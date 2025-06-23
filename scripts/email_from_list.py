"""
Email From List Script

This script reads a queue of RFQ items from a CSV file, matches them with suitable vendors
based on process capabilities, creates draft emails in Outlook for each quote, attaches
files, and logs the actions.

The script uses the following data sources:
- Queue.csv: Contains the RFQ items with part numbers, processes, and file paths
- contacts.csv: Contains vendor contact information
- vendor_options.yaml: Contains vendor capabilities and approvals

Usage:
    python scripts\email_from_list.py

Requirements:
    - pandas package must be installed
    - pywin32 package must be installed
    - pyyaml package must be installed
    - Outlook must be installed and configured
    - Required files must exist at the specified paths
"""

import logging
import os
import sys
import csv
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import win32com.client as win32
import yaml
import jinja2
from pandas import DataFrame


def setup_logging(logs_dir: str) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        logs_dir: Directory where log files will be stored

    Returns:
        Logger object configured for this script
    """
    # Ensure logs directory exists
    os.makedirs(logs_dir, exist_ok=True)

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(logs_dir, "email_from_list.log"), encoding='utf-8'),
        ],
    )
    return logging.getLogger("email_from_list")


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
        # Load queue data with Windows encoding fallback
        queue = pd.read_csv(queue_file, encoding='cp1252')

        # Load contacts data
        contacts = pd.read_csv(contacts_file, encoding='cp1252')

        # Load vendor options data
        with open(vendor_options_file, 'r', encoding='utf-8') as f:
            vendor_options = yaml.safe_load(f)

        # Rename queue columns to match expected names
        queue_column_mapping = {
            'Quote#': 'quote_id',
            'Line': 'line',
            'Part Number': 'part_number',
            'Callout': 'callout',
            'Process': 'process',
            'Spec': 'spec',
            'PriceBreak': 'qty',
            'File_location': 'file_path'
        }
        queue = queue.rename(columns=queue_column_mapping)

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
    required_queue_columns = ['quote_id', 'part_number', 'process', 'file_path']
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


def initialize_outlook(logger: logging.Logger = None) -> Any:
    """
    Initialize the Outlook application.

    Returns:
        Outlook application object

    Raises:
        RuntimeError: If Outlook cannot be initialized
    """
    if logger:
        logger.info("Initializing Outlook")
    else:
        print("Initializing Outlook")
    try:
        outlook = win32.Dispatch('outlook.application')
        return outlook
    except Exception as e:
        if logger:
            logger.error(f"Failed to initialize Outlook: {str(e)}")
        else:
            print(f"Failed to initialize Outlook: {str(e)}")
        raise RuntimeError(f"Failed to initialize Outlook: {str(e)}")


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

    # Read the template
    with open(template_path, 'r', newline='') as f:
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

        # Append HTML signature if provided
        if signature and html_format and signature.strip().startswith('<'):
            # Append the HTML signature
            body = body + signature
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

            # Add signature
            if signature:
                newline = '\n'  # Define newline character outside the f-string
                html_parts.append(f"<p>{signature.replace(newline, '<br>')}</p>")
            else:
                html_parts.append("<p>Thanks,<br>Your Name</p>")

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

            # Add signature
            if signature:
                body += f"\n\n{signature}"
            else:
                body += "\n\nThanks,\nYour Name"

    return subject, body


def create_draft_email(
    outlook: Any, 
    recipient: str, 
    subject: str, 
    body: str, 
    attachments: List[str],
    logger: logging.Logger = None,
    html_format: bool = True,
    use_outlook_signature: bool = True
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

        # Attach files
        missing_attachments = []
        for path in attachments:
            if os.path.isfile(path):
                mail.Attachments.Add(path)
                if logger:
                    logger.debug(f"Attached file: {path}")
                else:
                    print(f"Attached file: {path}")
            else:
                if logger:
                    logger.warning(f"Missing attachment: {path}")
                else:
                    print(f"Missing attachment: {path}")
                missing_attachments.append(path)

        mail.Save()

        if missing_attachments:
            if logger:
                logger.warning(f"Email saved with {len(missing_attachments)} missing attachments")
            else:
                print(f"Email saved with {len(missing_attachments)} missing attachments")
            return False

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
            index=False
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


def process_queue(
    queue: DataFrame, 
    vendor_info: Dict[Any, Dict[str, Any]], 
    outlook: Any, 
    log_file: str,
    template_path: str = None,
    sample_table_path: str = None,
    signature: str = None,
    logger: logging.Logger = None,
    default_vendor: str = None
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

    Returns:
        Tuple containing:
            - Number of successful drafts
            - Total number of quotes processed
    """
    successful_drafts = 0
    total_quotes = 0
    use_template = template_path is not None and os.path.exists(template_path)

    # Get a list of unique quote IDs
    unique_quotes = queue['quote_id'].unique()

    for quote_id in unique_quotes:
        items = queue[queue['quote_id'] == quote_id]

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
                if logger:
                    logger.info(f"Searching for vendors that support spec: {spec}")
                else:
                    print(f"Searching for vendors that support spec: {spec}")

                # Find vendors that support this spec
                for vendor_id, info in vendor_info.items():
                    if 'processes' not in info:
                        continue

                    for vendor_process in info['processes']:
                        if isinstance(vendor_process, dict) and 'specs' in vendor_process and vendor_process['specs'] is not None:
                            for vendor_spec in vendor_process['specs']:
                                if isinstance(vendor_spec, dict) and 'number' in vendor_spec:
                                    if spec.lower() == vendor_spec['number'].lower():
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

                for vendor_id, info in vendor_info.items():
                    # If the vendor has a processes list and the process is in it
                    if 'processes' in info:
                        for vendor_process in info['processes']:
                            if isinstance(vendor_process, str) and process.lower() == vendor_process.lower():
                                suitable_vendors.append(vendor_id)
                                break
                            elif isinstance(vendor_process, dict) and 'name' in vendor_process:
                                if process.lower() == vendor_process['name'].lower():
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
                    if hasattr(r, 'file_path') and pd.notna(r.file_path):
                        # Handle file paths from the CSV
                        file_path = r.file_path.strip()
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
                    use_outlook_signature=False
                )

                if success:
                    if logger:
                        logger.info(f"Draft saved for quote {quote_id}, process {process} -> {recipient}")
                    else:
                        print(f"Draft saved for quote {quote_id}, process {process} -> {recipient}")
                    log_email(log_file, quote_id, vendor_id, f'draft_saved_{process}', logger)
                    successful_drafts += 1
                else:
                    if logger:
                        logger.warning(f"Issues encountered when creating draft for quote {quote_id}, process {process}")
                    else:
                        print(f"Issues encountered when creating draft for quote {quote_id}, process {process}")
                    log_email(log_file, quote_id, vendor_id, f'draft_saved_with_issues_{process}', logger)

    return successful_drafts, total_quotes


def main() -> None:
    """Main entry point for the script."""
    try:
        # File paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)

        queue_file = os.path.join(project_root, 'data', 'Queue.csv')
        contacts_file = os.path.join(project_root, 'docs', 'OS', 'contacts.csv')
        vendor_options_file = os.path.join(project_root, 'docs', 'OS', 'vendor_options.yaml')
        logs_file = os.path.join(project_root, 'logs.csv')

        # Template paths
        template_path = os.path.join(project_root, 'docs', 'templates', 'cover_letter.j2')
        sample_table_path = os.path.join(project_root, 'docs', 'templates', 'Sample_Table(Empty)-OS.csv')
        signature_path = os.path.join(project_root, 'docs', 'templates', 'email_signature.html')

        # Set up logging
        logs_dir = os.path.join(project_root, "logs")
        logger = setup_logging(logs_dir)

        # Read HTML signature from file
        try:
            with open(signature_path, 'r', encoding='utf-8') as f:
                signature = f.read()
            logger.info(f"Using HTML signature from {signature_path}")
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
            default_vendor=None  # No default vendor - will use first available if needed
        )

        # Report results
        if logger:
            logger.info(f"All drafts generated. Success: {successful_drafts}/{total_quotes}")
        else:
            print(f"All drafts generated. Success: {successful_drafts}/{total_quotes}")

    except Exception as e:
        # If logger is not defined yet, print to console
        if 'logger' in locals():
            logger.error(f"Script failed: {str(e)}")
        else:
            print(f"Script failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
