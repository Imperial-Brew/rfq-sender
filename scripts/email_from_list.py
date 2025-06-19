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
            logging.FileHandler(os.path.join(logs_dir, "email_from_list.log")),
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
        # Filter to primary contacts only (if needed)
        primary_contacts = contacts[contacts['type'] == 'finishing']

        # Create vendor info dictionary
        vendor_info = {}
        for _, row in primary_contacts.iterrows():
            vendor_id = row['Vendor'].strip()
            email = row['Email'].strip() if pd.notna(row['Email']) else ""

            # Skip entries without email
            if not email:
                continue

            vendor_info[vendor_id] = {
                'email': email,
                'vendor_name': vendor_id  # Use vendor name as is
            }

        # Enrich vendor info with capabilities from vendor_options
        if vendor_options and 'vendors' in vendor_options:
            for vendor in vendor_options['vendors']:
                vendor_name = vendor['name']
                if vendor_name in vendor_info:
                    # Add capabilities information
                    processes = []
                    if 'processes' in vendor:
                        for process in vendor['processes']:
                            processes.append(process['name'])
                    vendor_info[vendor_name]['processes'] = processes

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


def create_sample_table(items: DataFrame, process: str, template_path: str) -> str:
    """
    Create a CSV table for the given items and process.

    Args:
        items: DataFrame containing items for the quote
        process: Process to filter items by
        template_path: Path to the sample table template

    Returns:
        CSV table as a string
    """
    # Filter items by process
    process_items = items[items['process'] == process]

    # Read the template
    with open(template_path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)  # Get header row

    # Create a new CSV in memory
    output = []
    output.append(','.join(header))  # Add header row

    # Add rows for each item
    for _, row in process_items.iterrows():
        csv_row = [
            row['part_number'],
            row['process'],
            '',  # Unit_Price (empty)
            '',  # Line Minimum (empty)
            '',  # Order Minimum (empty)
            '',  # Lead_Time (empty)
            ''   # vendor_ref_# (empty)
        ]
        output.append(','.join(csv_row))

    return '\n'.join(output)


def create_email_body(
    vendor_name: str, 
    items: DataFrame, 
    process: str = None, 
    use_template: bool = False,
    template_path: str = None,
    sample_table_path: str = None,
    signature: str = None
) -> Tuple[str, str]:
    """
    Create email subject and body for an RFQ.

    This function generates an email subject and body for a Request for Quote (RFQ).
    It can use a Jinja2 template if specified, or create a simple text email.
    It can also include a sample table for the vendor to fill out.

    Args:
        vendor_name: Name of the vendor
        items: DataFrame containing items for the quote, with columns like
               'quote_id', 'part_number', 'qty', 'process', 'spec', and 'callout'
        process: Process to filter items by (if None, includes all items)
        use_template: Whether to use the Jinja2 template
        template_path: Path to the Jinja2 template
        sample_table_path: Path to the sample table template
        signature: Email signature to include

    Returns:
        Tuple containing:
            - Email subject
            - Email body with properly quoted callout text
    """
    quote_id = items['quote_id'].iloc[0]

    # Filter items by process if specified
    if process:
        filtered_items = items[items['process'] == process]
        subject = f"RFQ for Quote {quote_id} - {process}"
    else:
        filtered_items = items
        subject = f"RFQ for Quote {quote_id}"

    if use_template and template_path and os.path.exists(template_path):
        # Use Jinja2 template
        # Prepare context for the template
        context = {
            'vendor': {'name': vendor_name},
            'part_no': ', '.join(filtered_items['part_number'].unique()),
            'process': process or ', '.join(filtered_items['process'].unique()),
            'spec': filtered_items['spec'].iloc[0] if 'spec' in filtered_items.columns and not filtered_items['spec'].isna().all() else None,
            'quantities': filtered_items['qty'].unique().tolist() if 'qty' in filtered_items.columns else [],
            'attachments': filtered_items['file_path'].dropna().unique().tolist() if 'file_path' in filtered_items.columns else [],
            'due_date': None,  # Could be added as a parameter
            'sender_name': signature.split('\n')[0] if signature else "Your Name",
            'sender_email': signature.split('\n')[1] if signature and len(signature.split('\n')) > 1 else "",
            'company_name': signature.split('\n')[2] if signature and len(signature.split('\n')) > 2 else ""
        }

        # Render the template
        body = render_template(template_path, context)

        # Add sample table if specified
        if sample_table_path and os.path.exists(sample_table_path):
            sample_table = create_sample_table(filtered_items, process, sample_table_path)
            body += f"\n\nPlease fill out the following table and return it to us:\n\n{sample_table}"
    else:
        # Create detailed lines for each part, including callout information if available
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
            f"Hello {vendor_name},\n\n"
            "Please find attached our RFQ for the following parts:\n"
            + "\n".join(lines)
        )

        # Add sample table if specified
        if sample_table_path and os.path.exists(sample_table_path):
            sample_table = create_sample_table(filtered_items, process, sample_table_path)
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
    logger: logging.Logger = None
) -> bool:
    """
    Create a draft email in Outlook.

    Args:
        outlook: Outlook application object
        recipient: Email address of the recipient
        subject: Email subject
        body: Email body
        attachments: List of file paths to attach

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create draft
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        mail.To = recipient
        mail.Subject = subject
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
    default_vendor: str = "Consolidated Metal Technologies, Inc."
) -> Tuple[int, int]:
    """
    Process the queue and create draft emails.

    This function processes the queue data from Queue.csv, creates draft emails
    for each quote and process, and attaches the relevant files. It creates separate
    emails for each process, rather than combining multiple processes in one email.

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

            # Find vendors that can handle this process
            suitable_vendors = []
            for vendor_id, info in vendor_info.items():
                # If the vendor has a processes list and the process is in it
                if 'processes' in info and process in info['processes']:
                    suitable_vendors.append(vendor_id)

            # If no suitable vendors found, prompt for vendor selection or use default
            if not suitable_vendors:
                if logger:
                    logger.warning(f"No vendors found with capabilities for process: {process}")
                    logger.warning(f"Using default vendor: {default_vendor}")
                else:
                    print(f"No vendors found with capabilities for process: {process}")
                    print(f"Using default vendor: {default_vendor}")

                # Check if default vendor exists in vendor_info
                if default_vendor in vendor_info:
                    vendor_id = default_vendor

                    # Add this process to the vendor's capabilities for future use
                    if 'processes' not in vendor_info[vendor_id]:
                        vendor_info[vendor_id]['processes'] = []

                    if process not in vendor_info[vendor_id]['processes']:
                        vendor_info[vendor_id]['processes'].append(process)
                        if logger:
                            logger.info(f"Added process '{process}' to vendor '{vendor_id}' capabilities")
                        else:
                            print(f"Added process '{process}' to vendor '{vendor_id}' capabilities")
                else:
                    # Use the first vendor as a fallback
                    vendor_id = list(vendor_info.keys())[0]
            else:
                # Use the first suitable vendor
                vendor_id = suitable_vendors[0]

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

            # Build email
            subject, body = create_email_body(
                info['vendor_name'], 
                process_items, 
                process=process,
                use_template=use_template,
                template_path=template_path,
                sample_table_path=sample_table_path,
                signature=signature
            )

            # Get attachment paths
            attachments = []
            for r in process_items.itertuples():
                if hasattr(r, 'file_path') and pd.notna(r.file_path):
                    # Handle file paths from the CSV
                    file_path = r.file_path.strip()
                    # Check if the file exists
                    if os.path.exists(file_path):
                        attachments.append(file_path)
                    else:
                        if logger:
                            logger.warning(f"File not found: {file_path}")
                        else:
                            print(f"File not found: {file_path}")

            if not attachments:
                if logger:
                    logger.warning(f"No valid attachments found for quote {quote_id}, process {process}")
                else:
                    print(f"No valid attachments found for quote {quote_id}, process {process}")

            # Create draft
            success = create_draft_email(outlook, recipient, subject, body, attachments, logger)

            if success:
                if logger:
                    logger.info(f"Draft saved for quote {quote_id}, process {process} → {recipient}")
                else:
                    print(f"Draft saved for quote {quote_id}, process {process} → {recipient}")
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

        # User signature
        signature = "Your Name\nyour.email@example.com\nYour Company"

        # Set up logging
        logs_dir = os.path.join(project_root, "logs")
        logger = setup_logging(logs_dir)

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
            default_vendor="Consolidated Metal Technologies, Inc."
        )

        # Report results
        if logger:
            logger.info(f"All drafts generated. Success: {successful_drafts}/{total_quotes}")
            logger.info("Note: Files were not retrieved. This will be addressed in a future update.")
        else:
            print(f"All drafts generated. Success: {successful_drafts}/{total_quotes}")
            print("Note: Files were not retrieved. This will be addressed in a future update.")

    except Exception as e:
        # If logger is not defined yet, print to console
        if 'logger' in locals():
            logger.error(f"Script failed: {str(e)}")
        else:
            print(f"Script failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
