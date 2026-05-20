import os
import pandas as pd
import jinja2
import logging
from typing import Dict, Optional, Tuple, Any, List
from dotenv import load_dotenv
from core.secrets import get_section  # to grab [company] and [app]
from core.email.utils import extract_rfq_fields
from core.vendors.vendor_manager import VendorManager
from core.email.graph_client import create_draft as graph_create

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

    def create_rfq_email(
            self,
            queue_item,
            vendor,
            contact,
            template_path: Optional[str] = None
    ) -> Tuple[str, str, str]:
        # Use provided template path or instance template path
        template_path = template_path or self.template_path
        if not template_path:
            raise ValueError("No template path provided")

        # NEW: pull normalized fields from the shared helper
        fields = extract_rfq_fields(queue_item)

        # Subject line using those fields
        app_cfg = get_section("app")
        prefix = app_cfg.get("subject_prefix", "")
        subject = f"{prefix}RFQ: {fields['part_number']} - {fields['process']}"

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

        # Build the template context (what the Jinja file renders with)
        contact_name = contact.get('name', '').strip()
        # Treat generic aliases as unnamed so the template can fall back gracefully
        _generic = {'quotes', 'sales', 'rfq', 'estimating', 'info', 'purchasing'}
        if contact_name.lower() in _generic:
            contact_name = ''

        context = {
            'contact_name':    contact_name,
            'vendor_name':     vendor.get('name', ''),
            'part_number':     fields['part_number'],
            'process':         fields['process'],
            'spec':            fields['spec'],
            'quantities':      fields['quantities'],
            'material':        fields['material'],
            'company_name':    _co('name', 'company_name')   or 'Your Company',
            'company_logo_url':_co('logo_url', 'company_logo_url'),
            'sender_name':     _co('sender_name'),
            'sender_title':    _co('sender_title'),
            'sender_email':    _co('sender_email'),
            'sender_phone':    _co('sender_phone'),
            'company_address': _co('address', 'company_address'),
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
        try:
            if attachments:
                raise ValueError(
                    "Attachments are not supported; upload files to Box and include links instead."
                )
            # Resolve target mailbox (Option A: app-only targeting per user)
            ex_cfg = get_section("exchange")
            target_upn = (user_upn or ex_cfg.get("username", "")).strip()
            cc = cc_email or ex_cfg.get("cc")
            if not target_upn:
                logger.error("Missing target mailbox (user_upn) and [exchange].username — cannot create draft")
                return False
            if not recipient or "@" not in recipient:
                logger.warning(f"Skipping draft: invalid recipient '{recipient}'")
                return False

            html_body = body if html_format else f"<pre>{body}</pre>"

            graph_create(
                user_upn=target_upn,
                subject=subject,
                html_body=html_body,
                to=[recipient],
                cc=[cc] if cc else None,
            )

            return True
        except Exception as e:
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