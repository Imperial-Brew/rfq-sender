import os
import pandas as pd
import json
# import smtplib - No longer needed, using exchangelib instead
import jinja2
# from email.mime.multipart import MIMEMultipart - No longer needed, using exchangelib instead
# from email.mime.text import MIMEText - No longer needed, using exchangelib instead
# from email.mime.application import MIMEApplication - No longer needed, using exchangelib instead
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import yaml
from scripts.utils.spec_check import SpecProcessValidator  # Import the validator
import logging
from dotenv import load_dotenv
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


def load_vendor_options(vendor_options_file: str) -> Dict[str, Any]:
    """
    Load vendor options from YAML file.

    Args:
        vendor_options_file: Path to the vendor options YAML file

    Returns:
        Dictionary containing vendor options data
    """
    try:
        with open(vendor_options_file, 'r', encoding='utf-8') as f:
            vendor_options = yaml.safe_load(f)
        return vendor_options
    except Exception as e:
        logger.error(f"Error loading vendor options file {vendor_options_file}: {str(e)}")
        return {}


def find_vendors_for_process_and_spec(
        vendors: List[Dict[str, Any]],
        vendor_options: Dict[str, Any],
        process: str,
        spec: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Find vendors that support a specific process and spec.

    Args:
        vendors: List of vendor dictionaries from vendors.json
        vendor_options: Vendor options data from vendor_options.yaml
        process: Process name to match
        spec: Optional spec to match

    Returns:
        List of vendor dictionaries that support the process and spec
    """
    # If no spec provided, use the simple process-only filter
    if not spec:
        return find_vendors_for_process(vendors, process)

    # Create a validator for normalizing process and spec names
    validator = SpecProcessValidator()

    # Normalize the input spec for comparison
    normalized_spec = normalize_process_spec(spec, validator)

    # Find vendors that support this spec
    suitable_vendors = []
    vendor_names_by_spec = []

    # First try to find vendors by spec
    if "vendors" in vendor_options:
        for vendor_option in vendor_options["vendors"]:
            vendor_name = vendor_option.get("name", "")

            for vendor_process in vendor_option.get("processes", []):
                if isinstance(vendor_process, dict) and vendor_process.get("name", "").lower() == process.lower():
                    # This vendor supports the process, now check if it supports the spec
                    if "specs" in vendor_process and vendor_process["specs"]:
                        for vendor_spec in vendor_process["specs"]:
                            if isinstance(vendor_spec, dict) and "number" in vendor_spec:
                                # Normalize the vendor spec for comparison
                                normalized_vendor_spec = normalize_process_spec(vendor_spec["number"], validator)

                                if normalized_spec == normalized_vendor_spec:
                                    # Found a match by spec
                                    vendor_names_by_spec.append(vendor_name)
                                    break

    # Now find the matching vendors in the original vendors list
    for vendor in vendors:
        if vendor.get("name") in vendor_names_by_spec:
            suitable_vendors.append(vendor)

    # If no vendors found by spec, fall back to process-only filtering
    if not suitable_vendors:
        return find_vendors_for_process(vendors, process)

    return suitable_vendors


def normalize_process_spec(text: str, validator: Optional[Any] = None) -> str:
    """
    Normalize a process or spec name for comparison.

    Args:
        text: The text to normalize
        validator: Optional SpecProcessValidator instance

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Basic normalization
    normalized = text.lower().strip()
    normalized = normalized.replace("-", "").replace(" ", "")

    # Use validator if provided
    if validator:
        try:
            normalized = validator.normalize(normalized)
        except:
            pass

    return normalized
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
def initialize_exchange(exchange_settings: Dict[str, Any]) -> Account:
    """
    Initialize connection to Exchange server.
    
    Args:
        exchange_settings: Dictionary with Exchange settings (username, from_email, cc)
        
    Returns:
        Exchange account object
        
    Raises:
        RuntimeError: If Exchange connection cannot be initialized
    """
    logger.info("Initializing Exchange connection")
    try:
        # Get credentials from environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Get credentials from environment variables with fallback to settings
        username = os.environ.get('EXCHANGE_USERNAME', exchange_settings.get('username', ''))
        password = os.environ.get('EXCHANGE_PASSWORD', '')
        server = os.environ.get('EXCHANGE_SERVER', 'outlook.office365.com')
        
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
    exchange_settings: Dict[str, Any],
    attachments: List[str] = None
) -> bool:
    """
    Create a draft email using Exchange Web Services.
    
    Args:
        recipient: Email address of the recipient
        subject: Email subject
        body: Email body (HTML)
        exchange_settings: Dictionary with Exchange settings (username, from_email, cc)
        attachments: List of file paths to attach
        
    Returns:
        True if draft created successfully, False otherwise
    """
    try:
        # Initialize Exchange connection
        account = initialize_exchange(exchange_settings)
        
        # Get CC email if specified
        cc_email = exchange_settings.get('cc', None)
        
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
        exchange_settings: Dict[str, Any],
        company_info: Dict[str, str],
        vendor_options_file: str = None
) -> Tuple[int, int]:
    """
    Process the queue and send emails to vendors.

    Args:
        queue_file: Path to the queue CSV file
        vendor_file: Path to the vendor JSON file
        template_path: Path to the email template
        exchange_settings: Exchange settings (username, from_email, cc)
        company_info: Company information
        vendor_options_file: Path to the vendor options YAML file

    Returns:
        Tuple containing number of successful emails and total emails
    """
    # Load queue data
    queue = pd.read_csv(queue_file)

    # Load vendor data
    vendors = load_vendors(vendor_file)

    # Load vendor options if provided
    vendor_options = {}
    if vendor_options_file and os.path.exists(vendor_options_file):
        vendor_options = load_vendor_options(vendor_options_file)

    # Initialize Exchange connection
    account = initialize_exchange(exchange_settings)

    # Process each item in the queue
    successful = 0
    total = 0

    for _, row in queue.iterrows():
        process = row.get('process', '')
        spec = row.get('spec', '')

        # Find vendors for this process and spec
        if vendor_options and spec:
            matching_vendors = find_vendors_for_process_and_spec(vendors, vendor_options, process, spec)
        else:
            matching_vendors = find_vendors_for_process(vendors, process)

        if not matching_vendors:
            continue

        total += len(matching_vendors)

        # Create and send email to each vendor
        for vendor in matching_vendors:
            # Get primary contact
            contact = get_primary_contact(vendor)
            if not contact:
                continue

            # Create email
            email = create_rfq_email(
                row,
                vendor,
                contact,
                template_path,
                company_info
            )

            # Send email
            if send_email(account, email, exchange_settings):
                successful += 1

    return successful, total