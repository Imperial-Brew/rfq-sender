import os
import pandas as pd
import json
import smtplib
import jinja2
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import logging
from exchangelib import Credentials, Account, Configuration, DELEGATE, Message, Mailbox, FileAttachment
from exchangelib.protocol import BaseProtocol, NoVerifyHTTPAdapter
import urllib3

# Disable insecure request warnings if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Optional: Add this for self-signed certificates
BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter

# Set up logging
logger = logging.getLogger(__name__)

# Load vendor information
def load_vendors(vendor_file: str) -> List[Dict[str, Any]]:
    """
    Load vendor information from JSON file.
    
    Args:
        vendor_file: Path to the vendor JSON file
        
    Returns:
        List of vendor dictionaries
    """
    try:
        with open(vendor_file, 'r') as f:
            data = json.load(f)
        return data.get('vendors', [])
    except Exception as e:
        logger.error(f"Error loading vendor file {vendor_file}: {str(e)}")
        return []

# Find vendors for a specific process
def find_vendors_for_process(vendors: List[Dict[str, Any]], process: str) -> List[Dict[str, Any]]:
    """
    Find vendors that support a specific process.
    
    Args:
        vendors: List of vendor dictionaries
        process: Process name to match
        
    Returns:
        List of vendor dictionaries that support the process
    """
    return [v for v in vendors if process.lower() in [p.lower() for p in v.get('processes', [])]]

# Get primary contact for a vendor
def get_primary_contact(vendor: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Get the primary contact for a vendor.
    
    Args:
        vendor: Vendor dictionary
        
    Returns:
        Primary contact dictionary or first contact if no primary is specified
    """
    contacts = vendor.get('contacts', [])
    for contact in contacts:
        if contact.get('primary', False):
            return contact
    return contacts[0] if contacts else None

# Initialize Exchange connection
def initialize_exchange(smtp_settings: Dict[str, Any]) -> Account:
    """
    Initialize connection to Exchange server.
    
    Args:
        smtp_settings: Dictionary with Exchange settings
        
    Returns:
        Exchange account object
        
    Raises:
        RuntimeError: If Exchange connection cannot be initialized
    """
    logger.info("Initializing Exchange connection")
    try:
        # Get credentials from settings
        username = smtp_settings.get('username', '')
        password = smtp_settings.get('password', '')
        server = smtp_settings.get('server', 'outlook.office365.com')
        
        # Create credentials object
        credentials = Credentials(username=username, password=password)
        
        # Create configuration
        config = Configuration(server=server, credentials=credentials)
        
        # Connect to the account
        account = Account(
            primary_smtp_address=username,
            config=config,
            autodiscover=False,
            access_type=DELEGATE
        )
        
        return account
    except Exception as e:
        logger.error(f"Failed to initialize Exchange connection: {str(e)}")
        raise RuntimeError(f"Failed to initialize Exchange connection: {str(e)}")

# Render email template
def render_template(template_path: str, context: Dict[str, Any]) -> str:
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
    except Exception as e:
        logger.error(f"Error rendering template {template_path}: {str(e)}")
        return ""

# Create email for RFQ
def create_rfq_email(
    queue_items: pd.DataFrame,
    vendor: Dict[str, Any],
    contact: Dict[str, Any],
    template_path: str,
    company_info: Dict[str, Any]
) -> Tuple[str, str, str]:
    """
    Create an email for an RFQ.
    
    Args:
        queue_items: DataFrame containing RFQ items
        vendor: Vendor dictionary
        contact: Contact dictionary
        template_path: Path to the email template
        company_info: Dictionary with company information
        
    Returns:
        Tuple of (recipient_email, subject, body)
    """
    try:
        # Get the first item for basic info
        first_item = queue_items.iloc[0]
        
        # Extract process and part number
        process = first_item.get('process', '')
        part_number = first_item.get('part_number', '')
        
        # Create email subject
        subject = f"RFQ: {part_number} - {process}"
        
        # Prepare quantities as comma-separated string
        quantities = first_item.get('quantities', '')
        
        # Prepare context for template
        context = {
            'contact_name': contact.get('name', ''),
            'part_number': part_number,
            'process': process,
            'spec': first_item.get('spec', ''),
            'quantities': quantities,
            'material': first_item.get('material', ''),
            'company_name': company_info.get('name', 'Your Company'),
            'company_logo_url': company_info.get('logo_url', ''),
            'sender_name': company_info.get('sender_name', ''),
            'sender_title': company_info.get('sender_title', ''),
            'sender_email': company_info.get('sender_email', ''),
            'sender_phone': company_info.get('sender_phone', ''),
            'company_address': company_info.get('address', '')
        }
        
        # Render email body using template
        body = render_template(template_path, context)
        
        return contact.get('email', ''), subject, body
    except Exception as e:
        logger.error(f"Error creating RFQ email: {str(e)}")
        return '', '', ''

# Create draft email using Exchange Web Services
def create_draft_email(
    account: Account,
    recipient: str,
    subject: str,
    body: str,
    attachments: List[str] = None,
    html_format: bool = True,
    use_outlook_signature: bool = False,  # This will be ignored
    cc_email: str = None
) -> bool:
    """
    Create a draft email using Exchange Web Services.
    
    Args:
        account: Exchange account object
        recipient: Email address of the recipient
        subject: Email subject
        body: Email body (HTML or plain text)
        attachments: List of file paths to attach
        html_format: Whether the body is HTML (True) or plain text (False)
        use_outlook_signature: Ignored in Exchange implementation
        cc_email: Optional CC email address
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create message
        m = Message(
            account=account,
            folder=account.drafts,
            subject=subject,
            body=body,
            body_type='HTML' if html_format else 'Text',
            to_recipients=[Mailbox(email_address=recipient)]
        )
        
        # Add CC if specified
        if cc_email:
            m.cc_recipients = [Mailbox(email_address=cc_email)]
        
        # Add attachments
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    file_attachment = FileAttachment(
                        name=os.path.basename(file_path),
                        content=content
                    )
                    m.attach(file_attachment)
                else:
                    logger.warning(f"Missing attachment: {file_path}")
        
        # Save the draft
        m.save()
        
        return True
    except Exception as e:
        logger.error(f"Error creating draft email to {recipient}: {str(e)}")
        return False

# Create draft email using Exchange Web Services
def send_email(
    recipient: str,
    subject: str,
    body: str,
    smtp_settings: Dict[str, Any],
    attachments: List[str] = None
) -> bool:
    """
    Create a draft email using Exchange Web Services.
    
    Args:
        recipient: Email address of the recipient
        subject: Email subject
        body: Email body (HTML)
        smtp_settings: Dictionary with Exchange settings
        attachments: List of file paths to attach
        
    Returns:
        True if draft created successfully, False otherwise
    """
    try:
        # Initialize Exchange connection
        account = initialize_exchange(smtp_settings)
        
        # Get CC email if specified
        cc_email = smtp_settings.get('cc', None)
        
        # Create draft email
        success = create_draft_email(
            account=account,
            recipient=recipient,
            subject=subject,
            body=body,
            attachments=attachments,
            cc_email=cc_email,
            html_format=True
        )
        
        if success:
            logger.info(f"Draft email created successfully for {recipient}")
        else:
            logger.warning(f"Failed to create draft email for {recipient}")
            
        return success
    except Exception as e:
        logger.error(f"Error creating draft email for {recipient}: {str(e)}")
        return False

# Process queue and create draft emails
def process_queue_and_send_emails(
    queue_file: str,
    vendor_file: str,
    template_path: str,
    smtp_settings: Dict[str, Any],
    company_info: Dict[str, Any]
) -> Tuple[int, int]:
    """
    Process the queue and create draft emails using Exchange Web Services.
    
    Args:
        queue_file: Path to the queue CSV file
        vendor_file: Path to the vendor JSON file
        template_path: Path to the email template
        smtp_settings: Dictionary with Exchange settings
        company_info: Dictionary with company information
        
    Returns:
        Tuple of (successful_emails, total_emails)
    """
    try:
        # Load queue data
        queue = pd.read_csv(queue_file)
        
        # Load vendor data
        vendors = load_vendors(vendor_file)
        
        # Initialize Exchange connection
        account = initialize_exchange(smtp_settings)
        
        # Track success/total
        successful_emails = 0
        total_emails = 0
        
        # Get unique processes from queue
        processes = queue['process'].unique()
        
        # Process each process separately
        for process in processes:
            # Get items for this process
            process_items = queue[queue['process'] == process]
            
            # Find vendors for this process
            process_vendors = find_vendors_for_process(vendors, process)
            
            if not process_vendors:
                logger.warning(f"No vendors found for process: {process}")
                continue
            
            # Create draft email for each vendor
            for vendor in process_vendors:
                # Get primary contact
                contact = get_primary_contact(vendor)
                
                if not contact or not contact.get('email'):
                    logger.warning(f"No valid contact found for vendor: {vendor.get('name', 'Unknown')}")
                    continue
                
                # Create email content
                recipient, subject, body = create_rfq_email(
                    process_items, 
                    vendor, 
                    contact, 
                    template_path, 
                    company_info
                )
                
                if not recipient or not subject or not body:
                    logger.warning(f"Failed to create email for vendor: {vendor.get('name', 'Unknown')}")
                    continue
                
                # Create draft email
                total_emails += 1
                cc_email = smtp_settings.get('cc', None)
                
                if create_draft_email(
                    account=account,
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    cc_email=cc_email,
                    html_format=True
                ):
                    successful_emails += 1
                    logger.info(f"Draft email created successfully for {recipient}")
                else:
                    logger.warning(f"Failed to create draft email for {recipient}")
        
        return successful_emails, total_emails
    except Exception as e:
        logger.error(f"Error processing queue and creating draft emails: {str(e)}")
        return 0, 0