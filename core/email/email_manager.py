import base64
import os
import re
import pandas as pd
import jinja2
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, List
from dotenv import load_dotenv
from core.secrets import get_section  # to grab [company] and [app]
from core.email.utils import extract_rfq_fields
from core.vendors.vendor_manager import VendorManager
from core.email.graph_client import create_draft as graph_create

# Project root: two levels up from core/email/email_manager.py
_PROJECT_ROOT = Path(__file__).parent.parent.parent


_LOGO_CID = "company_logo"
_LOGO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".gif": "image/gif",
}


def _find_logo_path(explicit: Optional[str] = None) -> Optional[Path]:
    """Return the first logo file found in assets/, case-insensitively.

    Resolution order:
      1. ``explicit`` path if provided and exists
      2. Any file in ``assets/`` whose lowercased name matches logo.*
         (handles AthenaLOGO.png, logo.PNG, Logo.jpg, etc.)
      3. None — no logo available
    """
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p

    assets = _PROJECT_ROOT / "assets"
    if assets.is_dir():
        # Prefer files whose name starts with "logo" (case-insensitive)
        # then fall back to any image in assets/.
        image_exts = set(_LOGO_MIME)
        logo_files = sorted(
            (f for f in assets.iterdir()
             if f.is_file() and f.suffix.lower() in image_exts),
            key=lambda f: (not f.name.lower().startswith("logo"), f.name.lower()),
        )
        if logo_files:
            return logo_files[0]
    return None


def _logo_inline_attachment(path: Path) -> dict:
    """Build a Graph API fileAttachment payload for an inline image."""
    mime = _LOGO_MIME.get(path.suffix.lower(), "image/png")
    return {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": path.name,
        "contentType": mime,
        "contentBytes": base64.b64encode(path.read_bytes()).decode("ascii"),
        "isInline": True,
        "contentId": _LOGO_CID,
    }

# Disable insecure request warnings if needed
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) - commented out for debug

# Optional: Add this for self-signed certificates
#  BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter - commented out for debug

# Set up logging
logger = logging.getLogger(__name__)


class EmailManager:
    """
    Manages email operations for RFQ emails.
    
    This class provides functionality to:
    1. Creates draft emails via Microsoft Graph.
    2. Render email templates using Jinja2.
    """
    
    def __init__(
        self,
        template_path: str = None,
        exchange_settings: Dict[str, Any] = None,
        company_info: Dict[str, Any] = None,
    ):
        """
        Initialize the email manager.
        
        Args:
            template_path: Path to the email template file
            exchange_settings: Dictionary with Exchange settings (username, from_email, cc)
            company_info: Dictionary with company information
        """
        self.template_path = template_path
        self.exchange_settings = exchange_settings or {}
        self.company_info = company_info or {}
        # Graph only; no EWS account
        load_dotenv()

    def render_template(self, template_path: str, context: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template with the given context.
        
        Args:
            template_path: Path to the template file
            context: Dictionary of variables to pass to the template
            
        Returns:
            Rendered template as a string
        """
        try:
            template_dir = os.path.dirname(template_path)
            template_file = os.path.basename(template_path)
            
            # Create Jinja2 environment
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_dir),
                autoescape=jinja2.select_autoescape(['html', 'xml'])
            )
            
            # Load and render template
            template = env.get_template(template_file)
            return template.render(**context)
        except FileNotFoundError:
            logger.error(f"Template file not found: {template_path}")
            return ""
        except jinja2.exceptions.TemplateError as e:
            logger.error(f"Template error in {template_path}: {str(e)}")
            return ""
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {str(e)}")
            return ""

    # Legal-entity suffixes to strip when building a greeting from the vendor name.
    # Keeps "Harrison Electropolishing" instead of "Harrison Electropolishing L.P."
    _LEGAL_SUFFIXES = re.compile(
        r',?\s+('
        r'L\.?P\.?|LLP|LLC|L\.L\.C\.|Inc\.?|Corp\.?|Ltd\.?|Co\.|P\.C\.'
        r')$',
        re.IGNORECASE,
    )

    def create_rfq_email(
            self,
            queue_item,
            vendor,
            contact,
            template_path: Optional[str] = None,
            box_link: str = "",
            box_password: str = "",
            is_cui: bool = False,
    ) -> Tuple[str, str, str]:
        # Use provided template path or instance template path
        template_path = template_path or self.template_path
        if not template_path:
            raise ValueError("No template path provided")

        # Pull normalized fields from the shared helper
        fields = extract_rfq_fields(queue_item)

        # Subject line: "{prefix} {part_number} – {process}"
        # The prefix (e.g. "[RFQ]") is stored in [app] subject_prefix.
        # We no longer hard-code "RFQ:" to avoid doubling up with the prefix.
        app_cfg = get_section("app")
        prefix = app_cfg.get("subject_prefix", "RFQ:").strip()
        subject = f"{prefix} {fields['part_number']} – {fields['process']}"

        # Normalize company section: lowercase all keys and resolve aliases so
        # secrets can use either convention (COMPANY_NAME or name, etc.)
        raw_company = {**self.company_info, **get_section("company")}
        company = {k.lower(): v for k, v in raw_company.items()}

        def _co(key: str, *aliases: str) -> str:
            """Look up a company config value by key or any alias."""
            for k in (key, *aliases):
                val = company.get(k.lower(), "")
                if val:
                    return str(val)
            return ""

        # Build greeting name from contact or vendor fallback.
        # Strip generic inbox aliases and legal-entity suffixes.
        contact_name = contact.get('name', '').strip()
        _generic = {'quotes', 'sales', 'rfq', 'estimating', 'info', 'purchasing'}
        if contact_name.lower() in _generic:
            contact_name = ''

        vendor_name = vendor.get('name', '')
        vendor_name_short = self._LEGAL_SUFFIXES.sub('', vendor_name).strip()

        # Sanitize box_link: reject empty string, whitespace, or the literal
        # string "nan" that pandas produces when a NaN cell is str()-converted.
        _bad = {'', 'nan', 'none', 'null'}
        clean_box_link = box_link.strip() if box_link else ''
        if clean_box_link.lower() in _bad:
            clean_box_link = ''

        context = {
            'contact_name':     contact_name,
            'vendor_name':      vendor_name,
            'vendor_name_short': vendor_name_short,
            'part_number':      fields['part_number'],
            'process':          fields['process'],
            'spec':             fields['spec'],
            'quantities':       fields['quantities'],
            'material':         fields['material'],
            'due_date':         fields.get('due_date', ''),
            'notes':            fields.get('notes', ''),
            'box_link':         clean_box_link,
            'box_password':     box_password.strip() if box_password else '',
            'is_cui':           is_cui,
            'company_name':     _co('name', 'company_name') or 'Your Company',
            # Prefer CID inline attachment (works in Outlook; data: URIs are blocked).
            # Falls back to a hosted URL if no local logo file is found.
            'company_logo_src': (
                f"cid:{_LOGO_CID}"
                if _find_logo_path(_co('logo_path', 'company_logo_path'))
                else _co('logo_url', 'company_logo_url')
            ),
            'sender_name':      _co('sender_name'),
            'sender_title':     _co('sender_title'),
            'sender_email':     _co('sender_email'),
            'sender_phone':     _co('sender_phone'),
            'company_address':  _co('address', 'company_address'),
            'cui_warning':      _co('cui_warning'),
            'legal_footer':     _co('legal_footer', 'email_disclaimer'),
        }

        # Render and return
        body = self.render_template(template_path, context)
        return contact.get('email', ''), subject, body

    def create_draft_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        html_format: bool = True,
        cc_email: str = None,
        user_upn: Optional[str] = None,
    ) -> bool:
        """
        Create a draft email using Microsoft Graph only.

        Attachments are not supported. Files should be uploaded to Box and
        shared via link in the email body.
        If any attachments are provided, a ValueError is raised.

        Args:
            recipient: The primary recipient email address.
            subject: Email subject.
            body: HTML or plain text body content.
            attachments: Not supported (use Box links instead).
            html_format: If False, the body is wrapped in <pre> tags.
            cc_email: Optional CC email address.
            user_upn: Target mailbox UPN/email for the draft. If omitted,
                falls back to [exchange].username from secrets.
        """
        # This print is OUTSIDE the try block so it appears even if get_section raises.
        print(
            f"[EMAIL] create_draft_email entered: recipient={recipient!r}"
            f" user_upn={user_upn!r} body_len={len(body)}",
            flush=True,
        )
        try:
            if attachments:
                raise ValueError(
                    "File attachments are not supported; upload files to Box and include links instead."
                )
            # Resolve target mailbox
            ex_cfg = get_section("exchange")
            target_upn = (user_upn or ex_cfg.get("username", "")).strip()
            cc = cc_email or ex_cfg.get("cc")
            print(f"[EMAIL] target_upn={target_upn!r}", flush=True)
            if not target_upn:
                print(f"[EMAIL] ERROR: no target_upn", flush=True)
                logger.error("Missing target mailbox (user_upn) and [exchange].username — cannot create draft")
                return False
            if not recipient or "@" not in recipient:
                print(f"[EMAIL] ERROR: invalid recipient {recipient!r}", flush=True)
                logger.warning(f"Skipping draft: invalid recipient '%s'", recipient)
                return False

            html_body = body if html_format else f"<pre>{body}</pre>"

            # Build inline image attachments (logo only for now).
            # Outlook blocks data: URIs so we pass the image as a CID attachment.
            logo_path = _find_logo_path()
            inline_images = (
                [_logo_inline_attachment(logo_path)] if logo_path else []
            )

            logger.info(
                "Graph draft → upn=%s to=%s subject=%r body_len=%d logo=%s",
                target_upn, recipient, subject, len(html_body),
                logo_path.name if logo_path else "none",
            )
            print(f"[EMAIL] calling graph_create upn={target_upn!r} to={recipient!r}", flush=True)
            graph_create(
                user_upn=target_upn,
                subject=subject,
                html_body=html_body,
                to=[recipient],
                cc=[cc] if cc else None,
                inline_images=inline_images or None,
            )
            print(f"[EMAIL] graph_create OK for {recipient}", flush=True)
            logger.info("Graph draft created OK for %s", recipient)
            return True
        except Exception as e:
            print(f"[EMAIL] EXCEPTION in create_draft_email for {recipient}: {type(e).__name__}: {e}", flush=True)
            logger.error(f"Graph draft creation failed for {recipient}: {e}")
            return False
    
    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
    ) -> bool:
        """Convenience wrapper around :meth:`create_draft_email`.

        Attachments are not supported; include file links in the email body
        instead.
        """
        try:
            cc_email = self.exchange_settings.get('cc', None)
            success = self.create_draft_email(
                recipient=recipient,
                subject=subject,
                body=body,
                cc_email=cc_email,
                html_format=True,
            )
            if success:
                logger.info(f"Draft email created successfully for {recipient}")
            else:
                logger.warning(f"Failed to create draft email for {recipient}")
            return success
        except Exception as e:
            logger.error(f"Error creating draft email for {recipient}: {str(e)}")
            return False
    
    def process_queue_and_send_emails(
        self,
        queue_file: str,
        vendor_file: str,
        vendor_options_file: str = None
    ) -> Tuple[int, int]:
        """
        Process the queue and send emails to vendors.
        
        Args:
            queue_file: Path to the queue CSV file
            vendor_file: Path to the vendor JSON file
            vendor_options_file: Path to the vendor options YAML file
            
        Returns:
            Tuple containing number of successful emails and total emails
        """
        try:
            # Load queue data
            queue = pd.read_csv(queue_file)
            
            # Create vendor manager
            vendor_manager = VendorManager(
                vendor_file=vendor_file,
                vendor_options_file=vendor_options_file if vendor_options_file and os.path.exists(vendor_options_file) else None
            )
            
            # Process each item in the queue
            successful = 0
            total = 0
            
            for _, row in queue.iterrows():
                process = row.get('process', '')
                spec = row.get('spec', '')
                
                # Find vendors for this process and spec
                matching_vendors = vendor_manager.find_vendors_for_process_and_spec(process, spec)
                
                if not matching_vendors:
                    logger.warning(f"No vendors found for process '{process}' and spec '{spec}'")
                    continue
                
                total += len(matching_vendors)
                
                # Create and send email to each vendor
                for vendor in matching_vendors:
                    # Get primary contact
                    contact = vendor_manager.get_primary_contact(vendor)
                    if not contact:
                        logger.warning(f"No primary contact found for vendor '{vendor.get('name', '')}'")
                        continue
                    
                    # Create email
                    recipient_email, subject, body = self.create_rfq_email(
                        row,
                        vendor,
                        contact
                    )
                    
                    if not recipient_email or not subject or not body:
                        logger.warning(f"Failed to create email for vendor '{vendor.get('name', '')}'")
                        continue
                    
                    # Send email
                    if self.send_email(recipient_email, subject, body):
                        successful += 1
            
            return successful, total
        except FileNotFoundError as e:
            logger.error(f"File not found: {str(e)}")
            return 0, 0
        except Exception as e:
            logger.error(f"Error processing queue: {str(e)}")
            return 0, 0