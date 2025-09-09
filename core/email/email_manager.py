import os
import pandas as pd
import jinja2
import logging
from typing import Dict, Optional, Tuple, Any
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

        company = {**self.company_info, **get_section("company")}

        # Build the template context (what the Jinja file renders with)
        context = {
            'contact_name': contact.get('name', ''),
            'part_number': fields['part_number'],
            'process': fields['process'],
            'spec': fields['spec'],
            'quantities': fields['quantities'],
            'material': fields['material'],
            'company_name': company.get('name', 'Your Company'),
            'company_logo_url': company.get('logo_url', ''),
            'sender_name': company.get('sender_name', ''),
            'sender_title': company.get('sender_title', ''),
            'sender_email': company.get('sender_email', ''),
            'sender_phone': company.get('sender_phone', ''),
            'company_address': company.get('address', ''),
        }

        # Render and return
        body = self.render_template(template_path, context)
        return contact.get('email', ''), subject, body

    def create_draft_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        html_format: bool = True,
        cc_email: str = None,
    ) -> bool:
        """
        Create a draft email using Microsoft Graph only.

        Attachments are not supported. Files should be uploaded to Box and
        shared via link in the email body.
        """
        try:
            # Pull mailbox + default CC from secrets
            ex_cfg = get_section("exchange")
            user_upn = ex_cfg.get("username", "")
            cc = cc_email or ex_cfg.get("cc")
            if not user_upn:
                logger.error("Missing [exchange].username (UPN) — cannot create draft")
                return False
            if not recipient or "@" not in recipient:
                logger.warning(f"Skipping draft: invalid recipient '{recipient}'")
                return False

            html_body = body if html_format else f"<pre>{body}</pre>"

            msg_id = graph_create(
                user_upn=user_upn,
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