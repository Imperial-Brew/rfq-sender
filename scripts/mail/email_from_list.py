"""
Email From List Script

This script reads a queue of RFQ items from a CSV file, matches them with suitable vendors
based on process capabilities, creates draft emails using Exchange Web Services for each quote, 
attaches files, and logs the actions.

The script uses the following data sources:
- Queue.csv: Contains the RFQ items with part numbers, processes, and file paths
- contacts.csv: Contains vendor contact information
- vendor_options.yaml: Contains vendor capabilities and approvals

Usage:
    python scripts\email_from_list.py

Requirements:
    - pandas package must be installed
    - exchangelib package must be installed
    - pyyaml package must be installed
    - Exchange account credentials must be configured in .env file
    - Required files must exist at the specified paths
"""

import logging
import os
import sys
import csv
import argparse
from scripts.box.box_integration import BoxIntegration
from typing import Dict, List, Optional, Tuple, Any, Union

import pandas as pd
import yaml
import jinja2
import questionary
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from pandas import DataFrame
from exchangelib import Credentials, Account, Configuration, DELEGATE, Message, Mailbox, FileAttachment
from exchangelib.protocol import BaseProtocol, NoVerifyHTTPAdapter
import urllib3

# Add parent directory to path to import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import Paths, LoggingConfig, init_config
from core.secrets import get_section
from utils.rfq_queue import save_queue

# Initialize configuration
init_config()

# Disable insecure request warnings if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure SSL verification at the protocol level to avoid conflicts
# between verify_mode=CERT_NONE and check_hostname=True
BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter

# Import SpecProcessValidator from spec_check.py
from scripts.utils.spec_check import SpecProcessValidator

console = Console()


def normalize_process_spec(text: str, validator: SpecProcessValidator = None) -> str:
    """
    Normalize a process or spec name using the SpecProcessValidator.

    Args:
        text: The process or spec name to normalize
        validator: Optional SpecProcessValidator instance. If None, a new one will be created.

    Returns:
        The normalized process or spec name
    """
    if not text:
        return ""

    # Create a validator if one wasn't provided
    if validator is None:
        validator = SpecProcessValidator()

    # Use the validator's normalize method
    return validator.normalize(text)


def enhanced_normalize_for_comparison(text: str, is_spec: bool = False) -> str:
    """
    Enhanced normalization for comparison purposes.

    This function goes beyond the basic normalization to handle specific cases:
    1. For specs, it removes all spaces to handle cases like "ASTM B633" vs "ASTM B 633"
    2. For processes, it handles cases where one term is a subset of another

    Args:
        text: The text to normalize
        is_spec: Whether the text is a spec (True) or process (False)

    Returns:
        The enhanced normalized text for comparison
    """
    if not text:
        return ""

    # Convert to string and lowercase
    text = str(text).lower()

    # Remove all spaces for specs to handle cases like "ASTM B633" vs "ASTM B 633"
    if is_spec:
        text = text.replace(" ", "")

    # For processes, handle special cases
    else:
        # Handle "zinc" vs "zinc plating"
        if text == "zinc":
            text = "zincplating"
        elif text == "zincplating" or text == "zinc plating":
            text = "zincplating"

    return text




def setup_logging(logs_dir: str) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        logs_dir: Directory where log files will be stored

    Returns:
        Logger object configured for this script
    """
    # Use the centralized logging module
    try:
        # Add parent directory to path to import from utils
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from utils.rfq_logging import get_logger
        return get_logger("email_from_list", "email_from_list.log")
    except ImportError:
        # Fall back to original implementation if centralized logging is not available
        from core.config import LoggingConfig
        return LoggingConfig.setup_logging("email_from_list", "email_from_list.log")


def load_data(queue_file: str, contacts_file: str, vendor_options_file: str, logger: logging.Logger = None) -> Tuple[DataFrame, Dict[Any, Dict[str, Any]]]:
    """
    Load data from CSV and YAML files and prepare vendor information.

    This function loads data from:
    - Queue.csv for the queue data
    - contacts.csv for vendor contact information
    - vendor_options.yaml for vendor approvals and capabilities

    Args:
        queue_file: Path to the queue CSV file (Queue.csv)
        contacts_file: Path to the contacts CSV file (contacts.csv)
        vendor_options_file: Path to the vendor options YAML file (vendor_options.yaml)
        logger: Optional logger for logging messages

    Returns:
        Tuple containing:
            - DataFrame with queue data (with renamed columns)
            - Dictionary mapping vendor_id to vendor information (email and name)

    Raises:
        FileNotFoundError: If any of the required files don't exist
        ValueError: If the files don't have the expected structure
    """
    if logger:
        logger.info(f"Loading queue data from {queue_file}")
    else:
        print(f"Loading queue data from {queue_file}")

    if not os.path.exists(queue_file):
        if logger:
            logger.error(f"Queue file not found: {queue_file}")
        else:
            print(f"Queue file not found: {queue_file}")
        raise FileNotFoundError(f"Queue file not found: {queue_file}")

    if logger:
        logger.info(f"Loading contacts data from {contacts_file}")
    else:
        print(f"Loading contacts data from {contacts_file}")

    if not os.path.exists(contacts_file):
        if logger:
            logger.error(f"Contacts file not found: {contacts_file}")
        else:
            print(f"Contacts file not found: {contacts_file}")
        raise FileNotFoundError(f"Contacts file not found: {contacts_file}")

    if logger:
        logger.info(f"Loading vendor options from {vendor_options_file}")
    else:
        print(f"Loading vendor options from {vendor_options_file}")

    if not os.path.exists(vendor_options_file):
        if logger:
            logger.error(f"Vendor options file not found: {vendor_options_file}")
        else:
            print(f"Vendor options file not found: {vendor_options_file}")
        raise FileNotFoundError(f"Vendor options file not found: {vendor_options_file}")

    try:
        # Load queue data with UTF-8 encoding and error handling
        try:
            queue = pd.read_csv(queue_file, encoding='utf-8')
        except UnicodeDecodeError:
            # Fall back to cp1252 if UTF-8 fails
            queue = pd.read_csv(queue_file, encoding='cp1252')

        # Log the number of items where SENT=YES, but don't filter them out
        if 'SENT' in queue.columns:
            sent_items_count = len(queue[queue['SENT'] == 'YES'])
            if logger:
                logger.info(f"Found {sent_items_count} items where SENT=YES. Total items: {len(queue)}")
            else:
                print(f"Found {sent_items_count} items where SENT=YES. Total items: {len(queue)}")

        # Load contacts data with UTF-8 encoding and error handling
        try:
            contacts = pd.read_csv(contacts_file, encoding='utf-8')
        except UnicodeDecodeError:
            # Fall back to cp1252 if UTF-8 fails
            contacts = pd.read_csv(contacts_file, encoding='cp1252')

        # Load vendor options data
        with open(vendor_options_file, 'r', encoding='utf-8') as f:
            vendor_options = yaml.safe_load(f)

        # Rename queue columns to match expected names
        queue_column_mapping = {
            'RFQ #': 'RFQ #',
            'Part_Number': 'part_number',
            'Rev': 'Rev',
            'Print Callout': 'callout',
            'process': 'process',
            'spec': 'spec',
            'material': 'material',
            'quantities': 'quantities',
            'file_location': 'file_location',
            'submitted_by': 'submitted_by',
            'qt/so #': 'qt/so #'
        }
        
        # Rename columns
        queue = queue.rename(columns=queue_column_mapping)
        
        # Add part_number as quote_id since it doesn't exist in the queue.csv
        queue['quote_id'] = queue['part_number']

        # Process contacts data
        # Filter to primary contacts only
        # The 'Primary' value is in the 9th column which might be unnamed in the CSV
        # Find the column that contains 'Primary' values
        primary_column = None
        for col in contacts.columns:
            if 'Primary' in contacts[col].values:
                primary_column = col
                break

        # Filter to primary contacts in the finishing category
        if primary_column:
            primary_contacts = contacts[(contacts['type'] == 'finishing') & (contacts[primary_column] == 'Primary')]
        else:
            # Fallback to just filtering by type if we can't find the primary column
            primary_contacts = contacts[contacts['type'] == 'finishing']

        # Create vendor info dictionary
        vendor_info = {}
        for _, row in primary_contacts.iterrows():
            vendor_id = row['Vendor'].strip()
            email = row['Email'].strip() if pd.notna(row['Email']) else ""

            # Skip entries without email
            if not email:
                continue

            # Get the first name if available
            first_name = row['First'].strip() if pd.notna(row['First']) else ""

            vendor_info[vendor_id] = {
                'email': email,
                'vendor_name': vendor_id,  # Use vendor name as is
                'first_name': first_name  # Add first name for personalized greeting
            }

        # Enrich vendor info with capabilities from vendor_options
        if vendor_options and 'vendors' in vendor_options:
            for vendor in vendor_options['vendors']:
                vendor_name = vendor['name']
                if vendor_name in vendor_info:
                    # Add capabilities information
                    if 'processes' in vendor:
                        # Store the full process objects, ensuring it's not None
                        vendor_info[vendor_name]['processes'] = vendor['processes'] if vendor['processes'] is not None else []

    except Exception as e:
        if logger:
            logger.error(f"Error loading files: {str(e)}")
        else:
            print(f"Error loading files: {str(e)}")
        raise

    # Validate required columns in queue
    required_queue_columns = ['part_number', 'process', 'file_location']
    missing_queue_columns = [col for col in required_queue_columns if col not in queue.columns]

    if missing_queue_columns:
        if logger:
            logger.error(f"Queue file missing required columns: {', '.join(missing_queue_columns)}")
        else:
            print(f"Queue file missing required columns: {', '.join(missing_queue_columns)}")
        raise ValueError(f"Queue file missing required columns: {', '.join(missing_queue_columns)}")

    # Check if we have any vendor info
    if not vendor_info:
        if logger:
            logger.warning("No vendor information found in contacts file")
        else:
            print("No vendor information found in contacts file")

    return queue, vendor_info


def initialize_exchange(logger: logging.Logger = None) -> Account:
    """
    Initialize connection to Exchange server.
    
    Returns:
        Exchange account object
        
    Raises:
        RuntimeError: If Exchange connection cannot be initialized
    """
    if logger:
        logger.info("Initializing Exchange connection")
    else:
        print("Initializing Exchange connection")
    
    try:
        # Get credentials from config using getter methods
        ex_cfg = get_section("exchange")
        username = ex_cfg.get("username", "")
        password = ""
        server = ""
        
        if not username or not password:
            error_msg = "Exchange credentials not found in configuration"
            if logger:
                logger.error(error_msg)
            else:
                print(error_msg)
            raise ValueError(error_msg)
        
        # Create credentials object
        credentials = Credentials(username=username, password=password)
        
        # Create configuration
        config = Configuration(
            server=server,
            credentials=credentials
        )
        
        # Connect to the account
        account = Account(
            primary_smtp_address=username,
            config=config,
            autodiscover=False,
            access_type=DELEGATE
        )
        
        if logger:
            logger.info("Exchange connection initialized successfully")
        else:
            print("Exchange connection initialized successfully")
            
        return account
    except Exception as e:
        error_msg = f"Failed to initialize Exchange connection: {str(e)}"
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        raise RuntimeError(error_msg)


def render_template(template_path: str, context: Dict[str, Any]) -> str:
    """
    Render a Jinja2 template with the given context.

    Args:
        template_path: Path to the template file
        context: Dictionary containing variables to pass to the template

    Returns:
        Rendered template as a string
    """
    template_dir = os.path.dirname(template_path)
    template_file = os.path.basename(template_path)

    # Set up Jinja2 environment
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir),
        autoescape=jinja2.select_autoescape(['html', 'xml'])
    )

    # Add custom filter for getting basename of a path
    env.filters['basename'] = os.path.basename

    # Load and render the template
    template = env.get_template(template_file)
    return template.render(**context)


def create_sample_table(items: DataFrame, process: str, template_path: str, html_format: bool = True) -> str:
    """
    Create a table for the given items and process.

    Args:
        items: DataFrame containing items for the quote
        process: Process to filter items by
        template_path: Path to the sample table template
        html_format: Whether to format the table as HTML (True) or CSV (False)

    Returns:
        Table as a string, either in HTML or CSV format
    """
    # Filter items by process
    process_items = items[items['process'] == process]

    # Read the template with UTF-8 encoding and error handling
    try:
        with open(template_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Get header row
    except UnicodeDecodeError:
        # Fall back to cp1252 with error handling if UTF-8 fails
        with open(template_path, 'r', newline='', encoding='cp1252', errors='replace') as f:
            reader = csv.reader(f)
            header = next(reader)  # Get header row

    if html_format:
        # Create an HTML table with proper styling
        html_table = ['<table style="border-collapse: collapse; width: 100%;">']

        # Add header row
        html_table.append('<tr style="background-color: #f2f2f2; font-weight: bold;">')
        for col in header:
            html_table.append(f'<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">{col}</th>')
        html_table.append('</tr>')

        # Add data rows
        for _, row in process_items.iterrows():
            html_table.append('<tr>')
            # Part Number
            html_table.append(f'<td style="border: 1px solid #ddd; padding: 8px;">{row["part_number"]}</td>')

            # Print Callout - Use the callout field from the queue
            callout_val = row["callout"] if pd.notna(row.get("callout")) else ""
            html_table.append(f'<td style="border: 1px solid #ddd; padding: 8px;">{callout_val}</td>')

            # Process - Use the process field from the queue
            process_val = row["process"] if pd.notna(row.get("process")) else ""
            html_table.append(f'<td style="border: 1px solid #ddd; padding: 8px;">{process_val}</td>')

            # Spec - Use the spec field from the queue
            spec_val = row["spec"] if pd.notna(row.get("spec")) else ""
            html_table.append(f'<td style="border: 1px solid #ddd; padding: 8px;">{spec_val}</td>')

            # QTYs - Use the qty field from the queue
            qty_val = row["qty"] if pd.notna(row.get("qty")) else ""
            html_table.append(f'<td style="border: 1px solid #ddd; padding: 8px;">{qty_val}</td>')

            # Unit_Price (empty)
            html_table.append('<td style="border: 1px solid #ddd; padding: 8px;"></td>')

            # Line Minimum (empty)
            html_table.append('<td style="border: 1px solid #ddd; padding: 8px;"></td>')

            # Order Minimum (empty)
            html_table.append('<td style="border: 1px solid #ddd; padding: 8px;"></td>')

            # Lead_Time (empty)
            html_table.append('<td style="border: 1px solid #ddd; padding: 8px;"></td>')

            # vendor_ref_# (empty)
            html_table.append('<td style="border: 1px solid #ddd; padding: 8px;"></td>')

            html_table.append('</tr>')

        html_table.append('</table>')


        return ''.join(html_table)
    else:
        # Create a CSV table (original behavior)
        output = []
        output.append(','.join(header))  # Add a header row

        # Add rows for each item
        for _, row in process_items.iterrows():
            # Use callout field for Print Callout column
            callout_val = row["callout"] if pd.notna(row.get("callout")) else ""
            # Use process field for Process column
            process_val = row["process"] if pd.notna(row.get("process")) else ""
            # Use spec field for Spec column
            spec_val = row["spec"] if pd.notna(row.get("spec")) else ""
            # Use qty field for QTYs column
            qty_val = row["qty"] if pd.notna(row.get("qty")) else ""

            csv_row = [
                row['part_number'],
                callout_val,
                process_val,
                spec_val,
                qty_val,
                '',  # Unit_Price (empty)
                '',  # Line Minimum (empty)
                '',  # Order Minimum (empty)
                '',  # Lead_Time (empty)
                ''   # vendor_ref_# (empty)
            ]
            output.append(','.join(csv_row))


        return '\n'.join(output)


def create_email_body(
    vendor_info: Dict[str, Any], 
    items: DataFrame, 
    process: str = None, 
    use_template: bool = False,
    template_path: str = None,
    sample_table_path: str = None,
    signature: str = None,
    html_format: bool = True,
    actual_attachments: List[str] = None
) -> Tuple[str, str]:
    """
    Create email subject and body for an RFQ.

    This function generates an email subject and body for a Request for Quote (RFQ).
    It can use a Jinja2 template if specified, or create a simple email.
    It can also include a sample table for the vendor to fill out.
    The email can be formatted as HTML or plain text.

    Args:
        vendor_info: Dictionary containing vendor information (name, email, first_name)
        items: DataFrame containing items for the quote, with columns like
               'quote_id', 'part_number', 'qty', 'process', 'spec', and 'callout'
        process: Process to filter items by (if None, includes all items)
        use_template: Whether to use the Jinja2 template
        template_path: Path to the Jinja2 template
        sample_table_path: Path to the sample table template
        signature: Email signature to include
        html_format: Whether to format the email as HTML (True) or plain text (False)
        actual_attachments: List of actual file paths that will be attached to the email

    Returns:
        Tuple containing:
            - Email subject
            - Email body (HTML or plain text)
    """
    import datetime

    quote_id = items['quote_id'].iloc[0]
    vendor_name = vendor_info['vendor_name']
    first_name = vendor_info.get('first_name', '')

    # Use first name if available, otherwise use vendor name
    greeting_name = first_name if first_name else vendor_name

    # Filter items by process if specified
    if process:
        filtered_items = items[items['process'] == process]
        subject = f"RFQ for Quote {quote_id} - {process}"
    else:
        filtered_items = items
        subject = f"RFQ for Quote {quote_id}"

    # Calculate due date (7 days from now)
    due_date = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%B %d, %Y")

    if use_template and template_path and os.path.exists(template_path):
        # Create sample table if specified
        sample_table = None
        if sample_table_path and os.path.exists(sample_table_path):
            sample_table = create_sample_table(filtered_items, process, sample_table_path, html_format)

        # Use Jinja2 template
        # Prepare context for the template
        context = {
            'vendor': {
                'name': vendor_name,
                'first_name': first_name
            },
            'greeting_name': greeting_name,
            'part_no': ', '.join(filtered_items['part_number'].unique()),
            'process': process or ', '.join(filtered_items['process'].unique()),
            'spec': filtered_items['spec'].iloc[0] if 'spec' in filtered_items.columns and not filtered_items['spec'].isna().all() else None,
            'quantities': filtered_items['qty'].unique().tolist() if 'qty' in filtered_items.columns else [],
            'attachments': actual_attachments if actual_attachments is not None else (filtered_items['file_path'].dropna().unique().tolist() if 'file_path' in filtered_items.columns else []),
            'due_date': due_date,  # Use the calculated due date
            'sender_name': "Your Name",  # Default values, will be overridden by HTML signature
            'sender_email': "your.email@example.com",
            'company_name': "Your Company",
            'sample_table': sample_table  # Add sample table to context
        }

        # Render the template
        body = render_template(template_path, context)

        # Don't append signature here, it will be added after Box file information
    else:
        if html_format:
            # Create HTML content
            html_parts = []
            html_parts.append(f"<p>Hello {greeting_name},</p>")
            html_parts.append("<p>Please find attached our RFQ for the following parts:</p>")
            html_parts.append("<ul>")

            # Create detailed lines for each part
            for r in filtered_items.itertuples():
                part_html = f"<li><strong>Part:</strong> {r.part_number}, <strong>Qty:</strong> {r.qty}, <strong>Process:</strong> {r.process}"

                # Add spec if available
                if hasattr(r, 'spec') and pd.notna(r.spec):
                    part_html += f", <strong>Spec:</strong> {r.spec}"

                part_html += "</li>"

                # Add callout as a quoted block if available
                if hasattr(r, 'callout') and pd.notna(r.callout):
                    callout_text = r.callout.strip()
                    # HTML-escape the callout text
                    callout_text = callout_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                    # Add the callout as a blockquote
                    part_html += f'<blockquote style="margin-left: 20px; padding-left: 10px; border-left: 3px solid #ccc;">{callout_text}</blockquote>'

                html_parts.append(part_html)

            html_parts.append("</ul>")

            # Add sample table if specified
            if sample_table_path and os.path.exists(sample_table_path):
                sample_table = create_sample_table(filtered_items, process, sample_table_path, html_format=True)
                html_parts.append("<p>Please fill out the following table and return it to us:</p>")
                html_parts.append(sample_table)

            # Don't add signature here, it will be added after Box file information

            body = "".join(html_parts)
        else:
            # Create plain text content (original behavior)
            lines = []
            for r in filtered_items.itertuples():
                part_line = f"- Part: {r.part_number}, Qty: {r.qty}, Process: {r.process}"

                # Add spec if available
                if hasattr(r, 'spec') and pd.notna(r.spec):
                    part_line += f", Spec: {r.spec}"

                # Add callout as a quoted block if available
                if hasattr(r, 'callout') and pd.notna(r.callout):
                    # Format the callout with proper indentation and quotes
                    callout_text = r.callout.strip()
                    # Replace any existing quotes with escaped quotes
                    callout_text = callout_text.replace('"', '\\"')
                    # Add the callout as a quoted block
                    part_line += f"\n  Callout: \"{callout_text}\""

                lines.append(part_line)

            body = (
                f"Hello {greeting_name},\n\n"
                "Please find attached our RFQ for the following parts:\n"
                + "\n".join(lines)
            )

            # Add sample table if specified
            if sample_table_path and os.path.exists(sample_table_path):
                sample_table = create_sample_table(filtered_items, process, sample_table_path, html_format=False)
                body += f"\n\nPlease fill out the following table and return it to us:\n\n{sample_table}"

            # Don't add signature here, it will be added after Box file information

    return subject, body


def create_draft_email(
        outlook: Any,
        recipient: str,
        subject: str,
        body: str,
        attachments: List[str],
        logger: logging.Logger = None,
        html_format: bool = True,
        use_outlook_signature: bool = True,
        quote_id: str = None,
        process: str = None,
        signature: str = None
) -> bool:
    """
    Create a draft email in Outlook.

    Args:
        outlook: Outlook application object
        recipient: Email address of the recipient
        subject: Email subject
        body: Email body (HTML or plain text)
        attachments: List of file paths to attach
        logger: Optional logger for logging messages
        html_format: Whether the body is HTML (True) or plain text (False)
        use_outlook_signature: Whether to use Outlook's general signature
        quote_id: ID of the quote (used for Box folder name)
        process: Process name (used for Box folder name)
        signature: Email signature to add at the end of the email

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create draft
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        mail.To = recipient
        mail.Subject = subject

        # Set the body format to HTML or plain text
        if html_format:
            mail.BodyFormat = 2  # 2 = olFormatHTML

            # If using Outlook's signature, we need to get the inspector first
            if use_outlook_signature:
                # Get the inspector to access the editor
                inspector = mail.GetInspector
                # Force the editor to initialize
                editor = inspector.WordEditor

                # Set the HTML body (this will include the signature)
                mail.HTMLBody = body
            else:
                # Just set the HTML body without signature
                mail.HTMLBody = body
        else:
            # Use plain text format
            mail.BodyFormat = 1  # 1 = olFormatPlain
            mail.Body = body

        # Track missing attachments and files for Box
        missing_attachments = []
        files_for_box = []
        box_files_info = []  # To store information about files uploaded to Box

        # Collect valid files for Box upload
        for path in attachments:
            if not os.path.isfile(path):
                if logger:
                    logger.warning(f"Missing attachment: {path}")
                else:
                    print(f"Missing attachment: {path}")
                missing_attachments.append(path)
                continue

            # Add file to Box upload list
            files_for_box.append(path)
            file_size_mb = os.path.getsize(path) / (1024 * 1024)
            if logger:
                logger.info(f"File will be uploaded to Box: {path} ({file_size_mb:.2f} MB)")
            else:
                print(f"File will be uploaded to Box: {path} ({file_size_mb:.2f} MB)")

        # Upload files to Box
        box_share_link = None
        if files_for_box:
            try:
                # Initialize Box integration
                box = BoxIntegration(logger)
                
                # Check if Box client was initialized successfully
                if not box.client:
                    error_msg = "Failed to initialize Box client. Set [box].BOX_JWT_JSON in .streamlit\\secrets.toml or set BOX_JWT_JSON environment variable."
                    if logger:
                        logger.error(error_msg)
                    else:
                        print(error_msg)
                        
                    # Add error information to all files
                    for path in files_for_box:
                        file_size_mb = os.path.getsize(path) / (1024 * 1024)
                        folder_path = os.path.dirname(path)
                        
                        box_files_info.append({
                            'path': path,
                            'size': file_size_mb,
                            'folder': folder_path,
                            'box_uploaded': False,
                            'error': "Box authentication failed. Provide [box].BOX_JWT_JSON in secrets or BOX_JWT_JSON in env."
                        })
                    
                    # Skip the rest of the Box operations
                    raise Exception("Box authentication failed. Provide [box].BOX_JWT_JSON in secrets or BOX_JWT_JSON in env.")
                
                # Extract part numbers from file paths (assuming files are named with part numbers)
                # This is a simple implementation - you may need to adjust based on your actual file naming convention
                part_numbers = set()
                files_by_part = {}
                
                # Try to extract part numbers from file paths or names
                for file_path in files_for_box:
                    file_name = os.path.basename(file_path)
                    
                    # Try to find part number in the file name
                    # Assuming part numbers start with "PN-" or are in a format like "123456_drawing.pdf"
                    # Adjust this logic based on your actual file naming convention
                    if "_" in file_name:
                        possible_part = file_name.split("_")[0]
                        # If it looks like a part number (alphanumeric), use it
                        if possible_part.isalnum() or "-" in possible_part:
                            part_number = possible_part
                        else:
                            # Default part number if we can't extract one
                            part_number = "PN-001"
                    elif "-" in file_name:
                        possible_part = file_name.split("-")[0]
                        if possible_part.isalnum():
                            part_number = f"PN-{possible_part}"
                        else:
                            part_number = "PN-001"
                    else:
                        # Default part number if we can't extract one
                        part_number = "PN-001"
                    
                    part_numbers.add(part_number)
                    
                    # Group files by part number
                    if part_number not in files_by_part:
                        files_by_part[part_number] = []
                    files_by_part[part_number].append(file_path)
                
                # If we couldn't extract any part numbers, use a default
                if not part_numbers:
                    part_numbers = {"PN-001"}
                    files_by_part = {"PN-001": files_for_box}
                
                # For this email, we're only dealing with one vendor (the recipient)
                vendor_name = recipient.split('@')[0]  # Use email username as vendor name
                vendor_name = ''.join(c for c in vendor_name if c.isalnum())  # Clean up vendor name
                
                # Create the hybrid folder structure
                if logger:
                    logger.info(f"Creating hybrid folder structure for RFQ: {quote_id}")
                    logger.info(f"Part numbers: {part_numbers}")
                    logger.info(f"Vendor: {vendor_name}")
                else:
                    print(f"Creating hybrid folder structure for RFQ: {quote_id}")
                    print(f"Part numbers: {part_numbers}")
                    print(f"Vendor: {vendor_name}")
                
                # Generate a folder name for logging purposes
                timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                folder_name = f"RFQ_{quote_id}_{process}_{timestamp}" if quote_id and process else f"RFQ_Files_{timestamp}"
                
                # Create folder structure
                folder_structure = box.create_rfq_structure(
                    quote_id=quote_id if quote_id else f"RFQ_{timestamp}",
                    part_numbers=list(part_numbers),
                    vendors=[vendor_name]
                )
                
                if folder_structure:
                    # For backward compatibility with error handling
                    folder = folder_structure["master_folder"]
                    
                    # Upload files to appropriate part folders
                    uploaded_files = []
                    for part_number, files in files_by_part.items():
                        part_folder = folder_structure["part_folders"].get(part_number)
                        if part_folder:
                            part_uploaded = box.upload_part_files(part_number, files, part_folder)
                            if part_uploaded:
                                uploaded_files.extend(part_uploaded)
                                
                                # Link files to vendor folder
                                vendor_folder = folder_structure["vendor_folders"].get(vendor_name)
                                if vendor_folder:
                                    box.link_files_to_vendor(
                                        vendor=vendor_name,
                                        part_numbers=[part_number],
                                        part_folders=folder_structure["part_folders"],
                                        vendor_folder=vendor_folder
                                    )
                    
                    # Create share link for vendor folder
                    vendor_folder = folder_structure["vendor_folders"].get(vendor_name)
                    if vendor_folder:
                        box_share_link = box.create_share_link(vendor_folder)
                    else:
                        # Fallback to master folder if vendor folder creation failed
                        box_share_link = box.create_share_link(folder_structure["master_folder"])

                    if box_share_link:
                        # Add information about uploaded files
                        for path in files_for_box:
                            file_size_mb = os.path.getsize(path) / (1024 * 1024)
                            folder_path = os.path.dirname(path)

                            box_files_info.append({
                                'path': path,
                                'size': file_size_mb,
                                'folder': folder_path,
                                'box_uploaded': True
                            })

                            if logger:
                                logger.info(f"Uploaded to Box: {path} ({file_size_mb:.2f} MB)")
                            else:
                                print(f"Uploaded to Box: {path} ({file_size_mb:.2f} MB)")
                    else:
                        # If share link creation failed, add files to box_files_info without Box info
                        for path in files_for_box:
                            file_size_mb = os.path.getsize(path) / (1024 * 1024)
                            folder_path = os.path.dirname(path)

                            box_files_info.append({
                                'path': path,
                                'size': file_size_mb,
                                'folder': folder_path,
                                'box_uploaded': True,  # Files were uploaded, but share link creation failed
                                'error': "Failed to create Box share link"
                            })

                        if logger:
                            logger.warning(f"Files were uploaded to Box folder '{folder_name}' (ID: {folder.id}) but failed to create share link")
                            logger.warning("Check Box sharing permissions. The folder may still be accessible through the Box web interface.")
                        else:
                            print(f"Files were uploaded to Box folder '{folder_name}' (ID: {folder.id}) but failed to create share link")
                            print("Check Box sharing permissions. The folder may still be accessible through the Box web interface.")
                else:
                    # If folder creation failed, add files to box_files_info without Box info
                    for path in files_for_box:
                        file_size_mb = os.path.getsize(path) / (1024 * 1024)
                        folder_path = os.path.dirname(path)

                        box_files_info.append({
                            'path': path,
                            'size': file_size_mb,
                            'folder': folder_path,
                            'box_uploaded': False,
                            'error': "Failed to create Box folder"
                        })

                    if logger:
                        logger.warning(f"Failed to create Box folder: {folder_name}")
                        logger.warning("Check Box credentials and permissions. Ensure you have write access to the Box account.")
                    else:
                        print(f"Failed to create Box folder: {folder_name}")
                        print("Check Box credentials and permissions. Ensure you have write access to the Box account.")

            except Exception as e:
                # If Box integration failed, add files to box_files_info without Box info
                for path in files_for_box:
                    file_size_mb = os.path.getsize(path) / (1024 * 1024)
                    folder_path = os.path.dirname(path)

                    box_files_info.append({
                        'path': path,
                        'size': file_size_mb,
                        'folder': folder_path,
                        'box_uploaded': False,
                        'error': str(e)  # Store the error message
                    })

                # Provide more specific error information
                error_type = type(e).__name__
                error_message = str(e)
                
                if "authentication" in error_message.lower() or "credentials" in error_message.lower() or "token" in error_message.lower():
                    error_hint = "Check Box credentials in .streamlit\\secrets.toml ([box].BOX_JWT_JSON) or BOX_JWT_JSON env."
                elif "network" in error_message.lower() or "connection" in error_message.lower() or "timeout" in error_message.lower():
                    error_hint = "Check network connection."
                elif "permission" in error_message.lower() or "access" in error_message.lower():
                    error_hint = "Check Box permissions."
                else:
                    error_hint = "Check Box configuration and try again."

                if logger:
                    logger.error(f"Error using Box integration: {error_type}: {error_message}")
                    logger.error(f"Suggestion: {error_hint}")
                else:
                    print(f"Error using Box integration: {error_type}: {error_message}")
                    print(f"Suggestion: {error_hint}")

        # Add information about files and Box link to the email body
        if box_files_info:
            if html_format:
                # Start with a prominent Box share link if available
                if box_share_link:
                    files_note = f"""<hr>
<div style='background-color: #f0f0f0; padding: 15px; border-left: 5px solid #0061d5; margin-bottom: 15px;'>
    <p style='font-size: 16px; margin-bottom: 10px;'><strong>📁 Files for this RFQ are available via Box</strong></p>
    <p style='font-size: 14px; background-color: #ffffff; padding: 10px; border: 1px solid #dddddd; border-radius: 4px;'>
        <strong>📎 Box Share Link:</strong> <a href='{box_share_link}' style='color: #0061d5; text-decoration: underline; font-weight: bold;'>{box_share_link}</a>
    </p>
    <p style='font-size: 12px; color: #666666; margin-top: 5px;'>Click the link above to access all files for this RFQ</p>
</div>
<p><strong>The following files have been uploaded to Box:</strong></p><ul>"""
                else:
                    files_note = "<hr><p><strong>Files for this RFQ are available via Box:</strong></p><ul>"
                
                # Then list the files
                for file_info in box_files_info:
                    file_path = file_info['path']
                    file_size_mb = file_info['size']
                    box_uploaded = file_info.get('box_uploaded', False)

                    note_text = f"<li>{os.path.basename(file_path)} ({file_size_mb:.2f} MB)"
                    if box_uploaded:
                        note_text += " - <strong>Uploaded to Box</strong>"
                    else:
                        note_text += " - <strong>Failed to upload to Box</strong>"
                        # Add error information if available
                        if 'error' in file_info:
                            note_text += f"<br><em>Error: {file_info['error']}</em>"
                    note_text += "</li>"
                    files_note += note_text

                # Close the list and add a note if no share link is available
                if not box_share_link:
                    files_note += "</ul><p>Please upload these files to BOX SharePoint and share the link, or contact the sender for alternative arrangements.</p>"
                else:
                    files_note += "</ul>"

                # Add Box file information
                mail.HTMLBody += files_note
                
                # Add signature after Box file information
                if signature:
                    mail.HTMLBody += f"<hr>{signature}"
                else:
                    mail.HTMLBody += "<hr><p>Thanks,<br>Your Name</p>"
            else:
                # Start with a prominent Box share link if available
                if box_share_link:
                    plain_note = f"""

=======================================================================
|                                                                     |
|  FILES FOR THIS RFQ ARE AVAILABLE VIA BOX                           |
|                                                                     |
=======================================================================

>> BOX SHARE LINK: {box_share_link}

>> Click the link above to access all files for this RFQ <<

The following files have been uploaded to Box:
"""
                else:
                    plain_note = "\n\nFiles for this RFQ are available via Box:\n"
                
                # Then list the files
                for file_info in box_files_info:
                    file_path = file_info['path']
                    file_size_mb = file_info['size']
                    box_uploaded = file_info.get('box_uploaded', False)

                    note_text = f"- {os.path.basename(file_path)} ({file_size_mb:.2f} MB)"
                    if box_uploaded:
                        note_text += " - UPLOADED TO BOX"
                    else:
                        note_text += " - FAILED TO UPLOAD TO BOX"
                        # Add error information if available
                        if 'error' in file_info:
                            note_text += f"\n  Error: {file_info['error']}"
                    plain_note += note_text + "\n"

                # Add a note if no share link is available
                if not box_share_link:
                    plain_note += "\nPlease upload these files to BOX SharePoint and share the link, or contact the sender for alternative arrangements."

                # Add plain note to body
                mail.Body += plain_note
                
                # Add signature after Box file information
                if signature:
                    mail.Body += f"\n\n{signature}"
                else:
                    mail.Body += "\n\nThanks,\nYour Name"

        mail.Save()

        if missing_attachments:
            if logger:
                logger.warning(f"Email saved with {len(missing_attachments)} missing attachments")
            else:
                print(f"Email saved with {len(missing_attachments)} missing attachments")
            return False

        if box_files_info and not box_share_link:
            # Count how many files were successfully uploaded
            successful_uploads = sum(1 for info in box_files_info if info.get('box_uploaded', False))
            failed_uploads = len(box_files_info) - successful_uploads
            
            if failed_uploads == len(box_files_info):
                # All uploads failed
                if logger:
                    logger.warning(f"Email saved but all {len(box_files_info)} files could not be uploaded to Box. Check Box credentials and network connection.")
                else:
                    print(f"Email saved but all {len(box_files_info)} files could not be uploaded to Box. Check Box credentials and network connection.")
            else:
                # Some uploads succeeded, some failed
                if logger:
                    logger.warning(f"Email saved but {failed_uploads} of {len(box_files_info)} files could not be uploaded to Box. {successful_uploads} files were uploaded successfully.")
                else:
                    print(f"Email saved but {failed_uploads} of {len(box_files_info)} files could not be uploaded to Box. {successful_uploads} files were uploaded successfully.")
        elif box_files_info and box_share_link:
            if logger:
                logger.info(f"Email saved with {len(box_files_info)} files uploaded to Box. Share link: {box_share_link}")
            else:
                print(f"Email saved with {len(box_files_info)} files uploaded to Box. Share link: {box_share_link}")

        return True

    except Exception as e:
        if logger:
            logger.error(f"Error creating draft email: {str(e)}")
        else:
            print(f"Error creating draft email: {str(e)}")
        return False

def log_email(log_file: str, quote_id: Any, vendor_id: Any, status: str, logger: logging.Logger = None) -> None:
    """
    Log email creation to CSV file.

    Args:
        log_file: Path to the log CSV file
        quote_id: ID of the quote
        vendor_id: ID of the vendor
        status: Status of the email (e.g., 'draft_saved', 'error')
    """
    try:
        log_df = pd.DataFrame([{
            'quote_id': quote_id,
            'vendor_id': vendor_id,
            'sent_timestamp': pd.Timestamp.now(),
            'status': status
        }])

        log_df.to_csv(
            log_file, 
            mode='a', 
            header=not os.path.exists(log_file), 
            index=False,
            encoding='utf-8'
        )

        if logger:
            logger.debug(f"Logged {status} for quote {quote_id}")
        else:
            print(f"Logged {status} for quote {quote_id}")

    except Exception as e:
        if logger:
            logger.error(f"Failed to log email: {str(e)}")
        else:
            print(f"Failed to log email: {str(e)}")


def update_vendor_quotes(
    quote_items: DataFrame, 
    vendor_id: str, 
    vendor_email: str, 
    vendor_quotes_file: str, 
    logger: logging.Logger = None
) -> None:
    """
    Update Vendor_Quotes.csv with quote information when a draft is created.

    Args:
        quote_items: DataFrame containing the quote items
        vendor_id: ID of the vendor
        vendor_email: Email of the vendor contact
        vendor_quotes_file: Path to the Vendor_Quotes.csv file
        logger: Optional logger for logging messages
    """
    try:
        # Create a list to store the rows to add to Vendor_Quotes.csv
        rows_to_add = []

        # Process each item in the quote
        for item in quote_items.itertuples():
            # Create a dictionary with the data to add
            row_data = {
                'Quote#': item.quote_id if hasattr(item, 'quote_id') else '',
                'Line': item.line if hasattr(item, 'line') else '',
                'part_number': item.part_number if hasattr(item, 'part_number') else '',
                'Process': item.process if hasattr(item, 'process') else '',
                'Spec': item.spec if hasattr(item, 'spec') else '',
                'Vendor': vendor_id,
                'Contact Email': vendor_email,
                'SENT': 'YES'
            }

            # Add any file path if available
            if hasattr(item, 'file_location') and pd.notna(item.file_location):
                row_data['file location'] = item.file_location

            rows_to_add.append(row_data)

        # Create a DataFrame from the rows
        vendor_quotes_df = pd.DataFrame(rows_to_add)

        # Write to Vendor_Quotes.csv
        vendor_quotes_df.to_csv(
            vendor_quotes_file,
            mode='a',
            header=not os.path.exists(vendor_quotes_file),
            index=False,
            encoding='utf-8'
        )

        if logger:
            logger.info(f"Added {len(rows_to_add)} items to Vendor_Quotes.csv for quote {quote_items['quote_id'].iloc[0]}")
        else:
            print(f"Added {len(rows_to_add)} items to Vendor_Quotes.csv for quote {quote_items['quote_id'].iloc[0]}")

    except Exception as e:
        if logger:
            logger.error(f"Failed to update Vendor_Quotes.csv: {str(e)}")
        else:
            print(f"Failed to update Vendor_Quotes.csv: {str(e)}")


def process_queue(
    queue: DataFrame, 
    vendor_info: Dict[Any, Dict[str, Any]], 
    outlook: Any, 
    log_file: str,
    template_path: str = None,
    sample_table_path: str = None,
    signature: str = None,
    logger: logging.Logger = None,
    default_vendor: str = None,
    vendor_quotes_file: str = None,
    queue_file: str = None
) -> Tuple[int, int]:
    """
    Process the queue and create draft emails.

    This function processes the queue data from Queue.csv, creates draft emails
    for each quote and process, and attaches the relevant files. It creates separate
    emails for each process, rather than combining multiple processes in one email.

    It prioritizes matching vendors by spec over process when spec information is available.

    The function also validates file paths and only attaches files that exist.

    Args:
        queue: DataFrame containing the queue data with renamed columns
        vendor_info: Dictionary mapping vendor_id to vendor information (email, name, processes)
        outlook: Outlook application object
        log_file: Path to the log CSV file
        template_path: Path to the Jinja2 template for email body
        sample_table_path: Path to the sample table template
        signature: Email signature to include
        logger: Optional logger for logging messages
        default_vendor: Default vendor to use if no suitable vendor is found
        vendor_quotes_file: Path to the Vendor_Quotes.csv file for tracking sent quotes
        queue_file: Path to the original Queue.csv file for updating SENT status

    Returns:
        Tuple containing:
            - Number of successful drafts
            - Total number of quotes processed
    """
    successful_drafts = 0
    total_quotes = 0
    use_template = template_path is not None and os.path.exists(template_path)

    # Create a validator for normalizing process and spec names
    validator = SpecProcessValidator()

    # Filter out items where SENT=YES for processing, but keep them in the queue for saving later
    processing_queue = queue.copy()
    if 'SENT' in processing_queue.columns:
        processing_queue = processing_queue[processing_queue['SENT'] != 'YES']
        if logger:
            logger.info(f"Filtered out items where SENT=YES for processing. Items to process: {len(processing_queue)}")
        else:
            print(f"Filtered out items where SENT=YES for processing. Items to process: {len(processing_queue)}")

    # Get a list of unique quote IDs from the filtered queue
    unique_quotes = processing_queue['quote_id'].unique()

    for quote_id in unique_quotes:
        items = processing_queue[processing_queue['quote_id'] == quote_id]

        # Check if we have any vendor information
        if not vendor_info:
            if logger:
                logger.warning(f"No vendor information available, skipping quote {quote_id}")
            else:
                print(f"No vendor information available, skipping quote {quote_id}")
            continue

        # Get the processes needed for this quote
        processes_needed = items['process'].unique().tolist()

        # Create a separate email for each process
        for process in processes_needed:
            total_quotes += 1
            process_items = items[items['process'] == process]

            # Check if we have spec information for this process
            has_spec = 'spec' in process_items.columns and not process_items['spec'].isna().all()

            # Find vendors that can handle this spec or process
            suitable_vendors = []

            if has_spec:
                # Get the spec for this process
                spec = process_items['spec'].iloc[0]
                normalized_spec = normalize_process_spec(spec, validator)
                if logger:
                    logger.info(f"Searching for vendors that support spec: {spec}")
                    logger.info(f"Normalized spec: {normalized_spec}")
                else:
                    print(f"Searching for vendors that support spec: {spec}")
                    print(f"Normalized spec: {normalized_spec}")

                # Find vendors that support this spec
                for vendor_id, info in vendor_info.items():
                    if 'processes' not in info:
                        continue

                    for vendor_process in info['processes']:
                        if isinstance(vendor_process, dict) and 'specs' in vendor_process and vendor_process['specs'] is not None:
                            for vendor_spec in vendor_process['specs']:
                                if isinstance(vendor_spec, dict) and 'number' in vendor_spec:
                                    # Normalize both spec names for comparison
                                    normalized_spec = normalize_process_spec(spec, validator)
                                    normalized_vendor_spec = normalize_process_spec(vendor_spec['number'], validator)

                                    # Enhanced normalization for comparison
                                    enhanced_spec = enhanced_normalize_for_comparison(spec, is_spec=True)
                                    enhanced_vendor_spec = enhanced_normalize_for_comparison(vendor_spec['number'], is_spec=True)

                                    # Log the comparison for debugging
                                    if logger:
                                        logger.info(f"Comparing spec '{spec}' ({normalized_spec}) with vendor spec '{vendor_spec['number']}' ({normalized_vendor_spec})")
                                        logger.info(f"Enhanced comparison: '{enhanced_spec}' vs '{enhanced_vendor_spec}'")
                                    else:
                                        print(f"Comparing spec '{spec}' ({normalized_spec}) with vendor spec '{vendor_spec['number']}' ({normalized_vendor_spec})")
                                        print(f"Enhanced comparison: '{enhanced_spec}' vs '{enhanced_vendor_spec}'")

                                    if normalized_spec == normalized_vendor_spec or enhanced_spec == enhanced_vendor_spec:
                                        if logger:
                                            logger.info(f"Found matching spec for vendor {vendor_id}")
                                        else:
                                            print(f"Found matching spec for vendor {vendor_id}")
                                        suitable_vendors.append(vendor_id)
                                        break

            # If no vendors found by spec, try finding by process
            if not suitable_vendors:
                if has_spec:
                    if logger:
                        logger.warning(f"No vendors found supporting spec: {spec}")
                        logger.info(f"Falling back to searching by process: {process}")
                    else:
                        print(f"No vendors found supporting spec: {spec}")
                        print(f"Falling back to searching by process: {process}")

                # Normalize the process name for logging
                normalized_process = normalize_process_spec(process, validator)
                if logger:
                    logger.info(f"Normalized process: {normalized_process}")
                else:
                    print(f"Normalized process: {normalized_process}")

                for vendor_id, info in vendor_info.items():
                    # If the vendor has a processes list and the process is in it
                    if 'processes' in info:
                        for vendor_process in info['processes']:
                            # Normalize process names for comparison
                            normalized_process = normalize_process_spec(process, validator)

                            if isinstance(vendor_process, str):
                                normalized_vendor_process = normalize_process_spec(vendor_process, validator)

                                # Enhanced normalization for comparison
                                enhanced_process = enhanced_normalize_for_comparison(process, is_spec=False)
                                enhanced_vendor_process = enhanced_normalize_for_comparison(vendor_process, is_spec=False)

                                # Log the comparison for debugging
                                if logger:
                                    logger.info(f"Comparing process '{process}' ({normalized_process}) with vendor process '{vendor_process}' ({normalized_vendor_process})")
                                    logger.info(f"Enhanced comparison: '{enhanced_process}' vs '{enhanced_vendor_process}'")
                                else:
                                    print(f"Comparing process '{process}' ({normalized_process}) with vendor process '{vendor_process}' ({normalized_vendor_process})")
                                    print(f"Enhanced comparison: '{enhanced_process}' vs '{enhanced_vendor_process}'")

                                if normalized_process == normalized_vendor_process or enhanced_process == enhanced_vendor_process:
                                    if logger:
                                        logger.info(f"Found matching process for vendor {vendor_id}")
                                    else:
                                        print(f"Found matching process for vendor {vendor_id}")
                                    suitable_vendors.append(vendor_id)
                                    break
                            elif isinstance(vendor_process, dict) and 'name' in vendor_process:
                                normalized_vendor_process = normalize_process_spec(vendor_process['name'], validator)

                                # Enhanced normalization for comparison
                                enhanced_process = enhanced_normalize_for_comparison(process, is_spec=False)
                                enhanced_vendor_process = enhanced_normalize_for_comparison(vendor_process['name'], is_spec=False)

                                # Log the comparison for debugging
                                if logger:
                                    logger.info(f"Comparing process '{process}' ({normalized_process}) with vendor process '{vendor_process['name']}' ({normalized_vendor_process})")
                                    logger.info(f"Enhanced comparison: '{enhanced_process}' vs '{enhanced_vendor_process}'")
                                else:
                                    print(f"Comparing process '{process}' ({normalized_process}) with vendor process '{vendor_process['name']}' ({normalized_vendor_process})")
                                    print(f"Enhanced comparison: '{enhanced_process}' vs '{enhanced_vendor_process}'")

                                if normalized_process == normalized_vendor_process or enhanced_process == enhanced_vendor_process:
                                    if logger:
                                        logger.info(f"Found matching process for vendor {vendor_id}")
                                    else:
                                        print(f"Found matching process for vendor {vendor_id}")
                                    suitable_vendors.append(vendor_id)
                                    break

            # If no suitable vendors found, log a warning and skip this item
            if not suitable_vendors:
                if logger:
                    logger.error(f"No vendors found with capabilities for process: {process}. Skipping this item.")
                else:
                    print(f"No vendors found with capabilities for process: {process}. Skipping this item.")

                # Log that we're skipping this item due to no suitable vendor
                log_email(log_file, quote_id, "NONE", f'skipped_no_vendor_{process}', logger)

                # Skip to the next process
                continue

            # Create an email for each suitable vendor
            for vendor_id in suitable_vendors:
                if logger:
                    logger.info(f"Processing quote {quote_id}, process {process} for vendor {vendor_id}")
                else:
                    print(f"Processing quote {quote_id}, process {process} for vendor {vendor_id}")

                # Get vendor info
                info = vendor_info.get(vendor_id)
                if not info:
                    if logger:
                        logger.warning(f"No contact for vendor {vendor_id}, skipping quote {quote_id}, process {process}")
                    else:
                        print(f"No contact for vendor {vendor_id}, skipping quote {quote_id}, process {process}")
                    log_email(log_file, quote_id, vendor_id, f'skipped_no_contact_{process}', logger)
                    continue

                recipient = info['email']

                # Get attachment paths
                attachments = []
                for r in process_items.itertuples():
                    if hasattr(r, 'file_location') and pd.notna(r.file_location):
                        # Handle file paths from the CSV
                        file_path = r.file_location.strip()
                        # Convert to raw string to handle special characters
                        file_path = rf"{file_path}"
                        part_number = r.part_number.strip()

                        # Check if the path exists
                        if os.path.exists(file_path):
                            # If it's a directory, search for files containing the part number
                            if os.path.isdir(file_path):
                                found_files = False
                                # Define file extensions to ignore
                                ignore_extensions = ['.xlsx', '.xls', '.docx', '.doc']

                                # Use os.walk to search through all sub-folders
                                for root, dirs, files in os.walk(file_path):
                                    for file in files:
                                        # Check if the file contains the part number
                                        if part_number in file:
                                            full_path = os.path.join(root, file)

                                            # Check if it's a file and not an Excel or Word document
                                            if os.path.isfile(full_path):
                                                # Get the file extension
                                                _, ext = os.path.splitext(full_path)

                                                # Skip Excel and Word documents
                                                if ext.lower() in ignore_extensions:
                                                    if logger:
                                                        logger.info(f"Ignoring Excel/Word file: {full_path}")
                                                    else:
                                                        print(f"Ignoring Excel/Word file: {full_path}")
                                                    continue

                                                # Add the file to attachments
                                                attachments.append(full_path)
                                                found_files = True
                                                if logger:
                                                    logger.info(f"Found file for part {part_number}: {full_path}")
                                                else:
                                                    print(f"Found file for part {part_number}: {full_path}")

                                if not found_files:
                                    if logger:
                                        logger.warning(f"No files found for part {part_number} in directory: {file_path}")
                                    else:
                                        print(f"No files found for part {part_number} in directory: {file_path}")
                            # If it's a file, add it directly
                            elif os.path.isfile(file_path):
                                attachments.append(file_path)
                                if logger:
                                    logger.info(f"Using file: {file_path}")
                                else:
                                    print(f"Using file: {file_path}")
                        else:
                            if logger:
                                logger.warning(f"Path not found: {file_path}")
                            else:
                                print(f"Path not found: {file_path}")

                if not attachments:
                    if logger:
                        logger.warning(f"No valid attachments found for quote {quote_id}, process {process}")
                    else:
                        print(f"No valid attachments found for quote {quote_id}, process {process}")

                # Build email with actual attachment count
                subject, body = create_email_body(
                    info, 
                    process_items, 
                    process=process,
                    use_template=use_template,
                    template_path=template_path,
                    sample_table_path=sample_table_path,
                    signature=signature,
                    html_format=True,
                    actual_attachments=attachments
                )

                # Create draft
                success = create_draft_email(
                    outlook,
                    recipient,
                    subject,
                    body,
                    attachments,
                    logger,
                    html_format=True,
                    use_outlook_signature=False,
                    quote_id=quote_id,
                    process=process,
                    signature=signature
                )

                if success:
                    if logger:
                        logger.info(f"Draft saved for quote {quote_id}, process {process} -> {recipient}")
                    else:
                        print(f"Draft saved for quote {quote_id}, process {process} -> {recipient}")
                    log_email(log_file, quote_id, vendor_id, f'draft_saved_{process}', logger)

                    # Update Vendor_Quotes.csv with quote information
                    if vendor_quotes_file:
                        update_vendor_quotes(
                            process_items, 
                            vendor_id, 
                            recipient, 
                            vendor_quotes_file, 
                            logger
                        )

                        # Mark items as SENT=YES in the original queue
                        for idx in process_items.index:
                            queue.loc[idx, 'SENT'] = 'YES'

                    successful_drafts += 1
                else:
                    if logger:
                        logger.warning(f"Issues encountered when creating draft for quote {quote_id}, process {process}")
                    else:
                        print(f"Issues encountered when creating draft for quote {quote_id}, process {process}")
                    log_email(log_file, quote_id, vendor_id, f'draft_saved_with_issues_{process}', logger)

    # Save the updated queue data back to the CSV file if queue_file is provided
    if queue_file and 'SENT' in queue.columns:
        try:
            if logger:
                logger.info(f"Saving updated queue data to {queue_file}")
            else:
                print(f"Saving updated queue data to {queue_file}")

            # Save the queue data via centralized handler (Box or local)
            save_queue(queue)

            if logger:
                logger.info(f"Queue data saved successfully")
            else:
                print(f"Queue data saved successfully")
        except Exception as e:
            if logger:
                logger.error(f"Failed to save queue data: {str(e)}")
            else:
                print(f"Failed to save queue data: {str(e)}")

    return successful_drafts, total_quotes


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Create draft emails from a queue of RFQs."
    )
    parser.add_argument(
        "--queue-file",
        help="Path to the queue CSV file (default: data/Queue.csv)"
    )
    parser.add_argument(
        "--contacts-file",
        help="Path to the contacts CSV file (default: docs/OS/contacts.csv)"
    )
    parser.add_argument(
        "--vendor-options-file",
        help="Path to the vendor options YAML file (default: docs/OS/vendor_options.yaml)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (default if no other arguments provided)"
    )

    return parser.parse_args()


def interactive_mode(
    project_root: str,
    logger: logging.Logger
) -> None:
    """
    Run the script in interactive mode with a user-friendly interface.

    Args:
        project_root: Path to the project root directory
        logger: Logger for logging messages
    """
    console.print("[bold blue]Email From List - Interactive Mode[/bold blue]")
    console.print("This tool creates draft emails from a queue of RFQs.")

    # Default file paths
    default_queue_file = os.path.join(project_root, 'data', 'Queue.csv')
    default_contacts_file = os.path.join(project_root, 'docs', 'OS', 'contacts.csv')
    default_vendor_options_file = os.path.join(project_root, 'docs', 'OS', 'vendor_options.yaml')
    default_logs_file = os.path.join(project_root, 'logs.csv')
    default_vendor_quotes_file = os.path.join(project_root, 'data', 'Vendor_Quotes.csv')
    default_template_path = os.path.join(project_root, 'docs', 'templates', 'cover_letter.j2')
    default_sample_table_path = os.path.join(project_root, 'docs', 'templates', 'Sample_Table(Empty)-OS.csv')
    default_signature_path = os.path.join(project_root, 'docs', 'templates', 'email_signature.html')

    # Get file paths interactively
    queue_file = questionary.path(
        "Path to Queue.csv file:",
        default=default_queue_file
    ).ask()

    contacts_file = questionary.path(
        "Path to contacts.csv file:",
        default=default_contacts_file
    ).ask()

    vendor_options_file = questionary.path(
        "Path to vendor_options.yaml file:",
        default=default_vendor_options_file
    ).ask()

    logs_file = questionary.path(
        "Path to logs.csv file:",
        default=default_logs_file
    ).ask()

    vendor_quotes_file = questionary.path(
        "Path to Vendor_Quotes.csv file:",
        default=default_vendor_quotes_file
    ).ask()

    template_path = questionary.path(
        "Path to email template file:",
        default=default_template_path
    ).ask()

    sample_table_path = questionary.path(
        "Path to sample table template file:",
        default=default_sample_table_path
    ).ask()

    signature_path = questionary.path(
        "Path to email signature file:",
        default=default_signature_path
    ).ask()

    # Read HTML signature from file with error handling
    try:
        with open(signature_path, 'r', encoding='utf-8') as f:
            signature = f.read()
        logger.info(f"Using HTML signature from {signature_path}")
    except UnicodeDecodeError:
        # Fall back to cp1252 with error handling if UTF-8 fails
        try:
            with open(signature_path, 'r', encoding='cp1252', errors='replace') as f:
                signature = f.read()
            logger.info(f"Using HTML signature from {signature_path} (with cp1252 encoding)")
        except Exception as e:
            logger.warning(f"Could not read HTML signature file: {str(e)}. Using text signature instead.")
            signature = """
Best regards,

Your Name
your.email@example.com
Your Company
Phone: (123) 456-7890
"""
    except Exception as e:
        logger.warning(f"Could not read HTML signature file: {str(e)}. Using text signature instead.")
        signature = """
Best regards,

Your Name
your.email@example.com
Your Company
Phone: (123) 456-7890
"""

    # Load data with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Loading data...", total=2)

        # Load queue data
        progress.update(task, description="Loading queue data...")
        queue, vendor_info = load_data(queue_file, contacts_file, vendor_options_file, logger)
        progress.advance(task)

        # Initialize Exchange
        progress.update(task, description="Initializing Exchange connection...")
        account = initialize_exchange(logger)
        progress.advance(task)

    # Show queue summary
    console.print("\n[bold]Queue Summary:[/bold]")
    table = Table(title=f"Items in Queue: {len(queue)}")
    table.add_column("Quote ID")
    table.add_column("Process")
    table.add_column("Part Number")
    table.add_column("Status")

    for _, row in queue.iterrows():
        table.add_row(
            str(row.get('quote_id', 'N/A')),
            str(row.get('process', 'N/A')),
            str(row.get('part_number', 'N/A')),
            "✅" if row.get('SENT') == 'YES' else "⏳"
        )

    console.print(table)

    # Ask if user wants to process all or select specific quotes
    process_all = questionary.confirm(
        "Process all quotes in the queue?",
        default=True
    ).ask()

    if not process_all:
        # Let user select specific quotes to process
        quote_ids = queue['quote_id'].unique().tolist()
        selected_quotes = questionary.checkbox(
            "Select quotes to process:",
            choices=quote_ids
        ).ask()

        # Filter queue to selected quotes
        queue = queue[queue['quote_id'].isin(selected_quotes)]

    # Process queue with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Processing queue...", total=len(queue['quote_id'].unique()))

        # Process queue
        successful_drafts, total_quotes = process_queue(
            queue, 
            vendor_info, 
            outlook, 
            logs_file, 
            template_path=template_path,
            sample_table_path=sample_table_path,
            signature=signature,
            logger=logger,
            default_vendor=None,
            vendor_quotes_file=vendor_quotes_file,
            queue_file=queue_file
        )

        progress.update(task, completed=len(queue['quote_id'].unique()))

    # Show results
    console.print(f"\n[bold green]Processing complete! Success: {successful_drafts}/{total_quotes}[/bold green]")


def main() -> None:
    """Main entry point for the script."""
    try:
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        # File paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)

        # Set up logging
        logs_dir = os.path.join(project_root, "logs")
        logger = setup_logging(logs_dir)
        
        # Log that environment variables were loaded
        logger.info("Loaded environment variables from .env file")
        
        # Verify Box credentials are present (secrets-first, no file dependency)
        from core.secrets import get_section
        box_secret = (get_section("box").get("BOX_JWT_JSON", "") or os.environ.get("BOX_JWT_JSON", "")).strip()
        if not box_secret:
            logger.warning("Box JWT not set. Please set [box].BOX_JWT_JSON in .streamlit\\secrets.toml or export BOX_JWT_JSON.")

        # Parse command-line arguments
        args = parse_args()

        # Check if we should run in interactive mode
        # Run in interactive mode if --interactive flag is set or no arguments are provided
        if args.interactive or all(v is None for k, v in vars(args).items() if k != 'interactive'):
            try:
                interactive_mode(project_root, logger)
            except Exception as e:
                # Check if it's a NoConsoleScreenBufferError
                if "NoConsoleScreenBufferError" in str(e):
                    console.print("[red]Error: Cannot run interactive mode in this environment.[/red]")
                    console.print("[yellow]This error typically occurs when running from an IDE or other non-console environment.[/yellow]")
                    console.print("[yellow]Try running the script directly from a command prompt (cmd.exe) or PowerShell.[/yellow]")
                    console.print("\n[green]Falling back to non-interactive mode. Use --help to see available commands.[/green]")
                    logger.warning("NoConsoleScreenBufferError: Falling back to non-interactive mode")
                else:
                    # For other exceptions, log the error and re-raise
                    logger.error(f"Error in interactive mode: {str(e)}")
                    raise
                return
            return

        # Non-interactive mode with provided arguments or defaults
        queue_file = args.queue_file or os.path.join(project_root, 'data', 'Queue.csv')
        contacts_file = args.contacts_file or os.path.join(project_root, 'docs', 'OS', 'contacts.csv')
        vendor_options_file = args.vendor_options_file or os.path.join(project_root, 'docs', 'OS', 'vendor_options.yaml')
        logs_file = os.path.join(project_root, 'logs.csv')
        vendor_quotes_file = os.path.join(project_root, 'data', 'Vendor_Quotes.csv')

        # Template paths
        template_path = os.path.join(project_root, 'docs', 'templates', 'cover_letter.j2')
        sample_table_path = os.path.join(project_root, 'docs', 'templates', 'Sample_Table(Empty)-OS.csv')
        signature_path = os.path.join(project_root, 'docs', 'templates', 'email_signature.html')

        # Read HTML signature from file
        try:
            with open(signature_path, 'r', encoding='utf-8') as f:
                signature = f.read()
            logger.info(f"Using HTML signature from {signature_path}")
        except UnicodeDecodeError:
            # Fall back to cp1252 with error handling if UTF-8 fails
            try:
                with open(signature_path, 'r', encoding='cp1252', errors='replace') as f:
                    signature = f.read()
                logger.info(f"Using HTML signature from {signature_path} (with cp1252 encoding)")
            except Exception as e:
                # Fallback to text signature if HTML signature file can't be read
                logger.warning(f"Could not read HTML signature file: {str(e)}. Using text signature instead.")
                signature = """
Best regards,

Your Name
your.email@example.com
Your Company
Phone: (123) 456-7890
"""
        except Exception as e:
            # Fallback to text signature if HTML signature file can't be read
            logger.warning(f"Could not read HTML signature file: {str(e)}. Using text signature instead.")
            signature = """
Best regards,

Your Name
your.email@example.com
Your Company
Phone: (123) 456-7890
"""

        # Load data
        queue, vendor_info = load_data(queue_file, contacts_file, vendor_options_file, logger)

        # Initialize Outlook
        outlook = initialize_outlook(logger)

        # Process queue
        successful_drafts, total_quotes = process_queue(
            queue, 
            vendor_info, 
            outlook, 
            logs_file, 
            template_path=template_path,
            sample_table_path=sample_table_path,
            signature=signature,
            logger=logger,
            default_vendor=None,  # No default vendor - will use first available if needed
            vendor_quotes_file=vendor_quotes_file,
            queue_file=queue_file
        )

        # Report results
        logger.info(f"All drafts generated. Success: {successful_drafts}/{total_quotes}")
        console.print(f"[bold green]All drafts generated. Success: {successful_drafts}/{total_quotes}[/bold green]")

    except Exception as e:
        # If logger is not defined yet, print to console
        if 'logger' in locals():
            logger.error(f"Script failed: {str(e)}")
        else:
            print(f"Script failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
