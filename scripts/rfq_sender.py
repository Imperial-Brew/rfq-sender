#!/usr/bin/env python
"""
RFQ Sender - Command Line Tool for sending RFQs to vendors

This script provides a command-line interface for sending Request for Quote (RFQ)
emails to multiple vendors for finishing, material, and hardware quotes.
"""

import argparse
import datetime
import logging
import os
import smtplib
import sqlite3
import sys
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dotenv import load_dotenv

import jinja2
import yaml

# Load environment variables from .env file
load_dotenv()

# Create logs directory if it doesn't exist
# Get the project root directory (parent of scripts directory)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(logs_dir, "rfq_sender.log")),
    ],
)
logger = logging.getLogger("rfq_sender")


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Send RFQ emails to vendors for finishing, material, and hardware quotes."
    )

    # Required arguments
    parser.add_argument(
        "--part_no", 
        required=True, 
        help="Part number (e.g. 0250-20000)"
    )
    parser.add_argument(
        "--process", 
        required=True, 
        help="Process name (e.g. 'cleaning', 'anodizing')"
    )
    parser.add_argument(
        "--file_location", 
        required=True, 
        help="Path to directory containing files to attach"
    )
    parser.add_argument(
        "--quantities", 
        required=True, 
        help="Comma-separated list of quantities (e.g. '1,2,5,10')"
    )

    # Optional arguments
    parser.add_argument(
        "--spec", 
        help="Optional specification details"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Print email contents without sending"
    )
    parser.add_argument(
        "--config-dir", 
        default=os.path.join("..", "config"),
        help="Path to configuration directory"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command")

    # Show log subcommand
    show_log_parser = subparsers.add_parser(
        "show-log", 
        help="Show recent RFQ log entries"
    )
    show_log_parser.add_argument(
        "--limit", 
        type=int, 
        default=10,
        help="Number of log entries to show"
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> Tuple[bool, Optional[str]]:
    """
    Validate command-line arguments.

    Args:
        args (argparse.Namespace): Parsed command-line arguments

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Validate part_no format
    if not args.part_no or not args.part_no.strip():
        return False, "Part number cannot be empty"

    # Validate process
    if not args.process or not args.process.strip():
        return False, "Process cannot be empty"

    # Validate file_location
    if not os.path.exists(args.file_location):
        return False, f"File location '{args.file_location}' does not exist"

    # Validate quantities format
    try:
        quantities = [int(q.strip()) for q in args.quantities.split(",")]
        if not quantities:
            return False, "Quantities list cannot be empty"
        if any(q <= 0 for q in quantities):
            return False, "Quantities must be positive integers"
    except ValueError:
        return False, "Quantities must be comma-separated integers"

    return True, None


def load_config(config_dir: str) -> dict:
    """
    Load configuration files.

    Args:
        config_dir (str): Path to configuration directory

    Returns:
        dict: Configuration data
    """
    config = {}

    # Load vendor configuration
    vendors_file = os.path.join(config_dir, "vendors.yml")
    if os.path.exists(vendors_file):
        with open(vendors_file, "r") as f:
            config["vendors"] = yaml.safe_load(f)
    else:
        logger.error(f"Vendor configuration file not found: {vendors_file}")
        sys.exit(1)

    # Load email configuration
    email_file = os.path.join(config_dir, "email.yml")
    if os.path.exists(email_file):
        with open(email_file, "r") as f:
            config["email"] = yaml.safe_load(f)
    else:
        logger.error(f"Email configuration file not found: {email_file}")
        sys.exit(1)

    return config


def get_attachments(part_no: str, process: str, file_location: str) -> List[str]:
    """
    Find and retrieve files matching the part number and process.

    Args:
        part_no (str): Part number
        process (str): Process name
        file_location (str): Path to directory containing files

    Returns:
        List[str]: List of file paths to attach
    """
    logger.info(f"Searching for files matching part_no={part_no}, process={process} in {file_location}")

    # Normalize process name for matching
    process_norm = process.lower().replace(" ", "").replace("-", "")

    # Create patterns to search for
    patterns = [
        f"*{part_no}*{process}*",  # Exact match
        f"*{part_no}*{process_norm}*",  # Normalized process
        f"*{part_no}*",  # Just part number
    ]

    # Find matching files
    matching_files = []
    for pattern in patterns:
        path = Path(file_location)
        for file_path in path.glob(pattern):
            if file_path.is_file() and file_path not in matching_files:
                matching_files.append(str(file_path))

    # Log results
    if matching_files:
        logger.info(f"Found {len(matching_files)} matching files")
        for file_path in matching_files:
            logger.info(f"  - {file_path}")
    else:
        logger.warning(f"No files found matching part_no={part_no}, process={process}")

    return matching_files


def render_template(template_name: str, context: Dict[str, any]) -> str:
    """
    Render a Jinja2 template with the given context.

    Args:
        template_name (str): Name of the template file
        context (Dict[str, any]): Context data for template rendering

    Returns:
        str: Rendered template as a string
    """
    # Set up Jinja2 environment
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Add custom filters
    env.filters["basename"] = lambda path: os.path.basename(path)

    # Load and render template
    template = env.get_template(template_name)
    return template.render(**context)


def init_database() -> sqlite3.Connection:
    """
    Initialize the SQLite database for RFQ tracking.

    Returns:
        sqlite3.Connection: Database connection
    """
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    # Connect to database
    db_path = os.path.join(data_dir, "rfq_log.db")
    conn = sqlite3.connect(db_path)

    # Create table if it doesn't exist
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rfq_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        part_no TEXT NOT NULL,
        process TEXT NOT NULL,
        vendor_name TEXT NOT NULL,
        vendor_email TEXT NOT NULL,
        quantities TEXT NOT NULL,
        sent_at TIMESTAMP NOT NULL,
        quote_no TEXT
    )
    ''')
    conn.commit()

    return conn


def log_rfq(
    conn: sqlite3.Connection,
    part_no: str,
    process: str,
    vendor_name: str,
    vendor_email: str,
    quantities: List[int],
    quote_no: Optional[str] = None,
) -> int:
    """
    Log an RFQ to the database.

    Args:
        conn (sqlite3.Connection): Database connection
        part_no (str): Part number
        process (str): Process name
        vendor_name (str): Vendor name
        vendor_email (str): Vendor email
        quantities (List[int]): List of quantities
        quote_no (Optional[str], optional): Quote number. Defaults to None.

    Returns:
        int: ID of the inserted row
    """
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO rfq_log (part_no, process, vendor_name, vendor_email, quantities, sent_at, quote_no)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            part_no,
            process,
            vendor_name,
            vendor_email,
            ",".join(str(q) for q in quantities),
            datetime.datetime.now().isoformat(),
            quote_no,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def show_rfq_log(conn: sqlite3.Connection, limit: int = 10) -> List[Dict[str, any]]:
    """
    Show recent RFQ log entries.

    Args:
        conn (sqlite3.Connection): Database connection
        limit (int, optional): Maximum number of entries to show. Defaults to 10.

    Returns:
        List[Dict[str, any]]: List of log entries
    """
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, part_no, process, vendor_name, vendor_email, quantities, sent_at, quote_no
        FROM rfq_log
        ORDER BY sent_at DESC
        LIMIT ?
        ''',
        (limit,),
    )

    # Convert to list of dictionaries
    columns = [col[0] for col in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))

    return results


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email (str): Email address to validate

    Returns:
        bool: True if email is valid, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def check_attachments(attachments: List[str]) -> Tuple[bool, List[str], List[str]]:
    """
    Check if attachments exist and are readable.

    Args:
        attachments (List[str]): List of file paths to check

    Returns:
        Tuple[bool, List[str], List[str]]: (all_valid, valid_attachments, invalid_attachments)
    """
    valid_attachments = []
    invalid_attachments = []

    for file_path in attachments:
        if os.path.exists(file_path) and os.access(file_path, os.R_OK):
            valid_attachments.append(file_path)
        else:
            invalid_attachments.append(file_path)

    return len(invalid_attachments) == 0, valid_attachments, invalid_attachments


def handle_cui_compliance(vendor: Dict[str, any], body: str) -> str:
    """
    Handle CUI (Controlled Unclassified Information) compliance based on vendor approval level.

    Args:
        vendor (Dict[str, any]): Vendor information
        body (str): Email body

    Returns:
        str: Modified email body with CUI warnings if applicable
    """
    # Check if CUI protection is enabled
    enable_cui_protection = os.environ.get("ENABLE_CUI_PROTECTION", "true").lower() == "true"

    if not enable_cui_protection:
        return body

    # Check vendor approval level
    approval_level = vendor.get("approval_level", "").lower()

    # If vendor is approved for CUI, add CUI warning
    if approval_level == "cui":
        cui_warning = os.environ.get(
            "CUI_WARNING_TEXT", 
            "This email contains Controlled Unclassified Information (CUI) that is subject to safeguarding or dissemination controls."
        )

        # Add warning at the top of the email
        modified_body = f"{cui_warning}\n\n{body}"

        # Add warning at the bottom of the email
        modified_body = f"{modified_body}\n\n{cui_warning}"

        logger.info(f"Added CUI warning to email for CUI-approved vendor: {vendor['name']}")
        return modified_body
    else:
        # For non-CUI vendors, check if there are any CUI attachments or content
        # This is a placeholder for more sophisticated CUI detection
        logger.info(f"Vendor {vendor['name']} is not approved for CUI data")
        return body


def send_email(
    to_email: str,
    subject: str,
    body: str,
    attachments: List[str],
    config: Dict[str, any],
    dry_run: bool = False,
    max_retries: int = 3,
) -> bool:
    """
    Send an email with attachments.

    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        body (str): Email body (HTML or plain text)
        attachments (List[str]): List of file paths to attach
        config (Dict[str, any]): Email configuration
        dry_run (bool, optional): If True, don't actually send the email. Defaults to False.
        max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Validate email format
    if not validate_email(to_email):
        logger.error(f"Invalid email address: {to_email}")
        return False

    # Check attachments
    all_valid, valid_attachments, invalid_attachments = check_attachments(attachments)
    if not all_valid:
        logger.warning(f"Some attachments are missing or not readable: {invalid_attachments}")
        logger.warning(f"Proceeding with valid attachments: {valid_attachments}")

    if dry_run:
        logger.info(f"[DRY RUN] Would send email to: {to_email}")
        logger.info(f"[DRY RUN] Subject: {subject}")
        logger.info(f"[DRY RUN] Body: {body[:100]}...")
        logger.info(f"[DRY RUN] Attachments: {valid_attachments}")
        return True

    # Retry logic
    for attempt in range(1, max_retries + 1):
        try:
            # Create message
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = f"{config['email']['smtp']['from_name']} <{config['email']['smtp']['from_email']}>"
            msg["To"] = to_email

            # Add CC recipients if specified
            if config["email"]["settings"].get("cc_emails"):
                cc_emails = config["email"]["settings"]["cc_emails"].split(",")
                msg["Cc"] = ", ".join(cc_emails)

            # Add body
            msg.attach(MIMEText(body, "plain"))

            # Add attachments
            for file_path in valid_attachments:
                try:
                    with open(file_path, "rb") as f:
                        attachment = MIMEApplication(f.read())
                        attachment.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(file_path)}",
                        )
                        msg.attach(attachment)
                except Exception as e:
                    logger.error(f"Failed to attach file {file_path}: {str(e)}")

            # Send email
            with smtplib.SMTP(config["email"]["smtp"]["server"], int(config["email"]["smtp"]["port"])) as server:
                if config["email"]["smtp"]["use_tls"]:
                    server.starttls()
                server.login(
                    config["email"]["smtp"]["username"],
                    config["email"]["smtp"]["password"],
                )
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPServerDisconnected as e:
            logger.warning(f"SMTP server disconnected (attempt {attempt}/{max_retries}): {str(e)}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Failed to send email after {max_retries} attempts")
                return False

        except smtplib.SMTPException as e:
            logger.warning(f"SMTP error (attempt {attempt}/{max_retries}): {str(e)}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Failed to send email after {max_retries} attempts")
                return False

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False


def main():
    """Main entry point for the script."""

    # Initialize database
    conn = init_database()

    # Parse and validate arguments
    args = parse_args()

    # Handle subcommands
    if args.command == "show-log":
        # Show recent RFQ log entries
        logger.info(f"Showing last {args.limit} log entries")
        log_entries = show_rfq_log(conn, args.limit)

        if not log_entries:
            logger.info("No RFQ log entries found")
            return

        # Print log entries
        print("\nRFQ Log Entries:")
        print("=" * 80)
        for entry in log_entries:
            print(f"ID: {entry['id']}")
            print(f"Part Number: {entry['part_no']}")
            print(f"Process: {entry['process']}")
            print(f"Vendor: {entry['vendor_name']} ({entry['vendor_email']})")
            print(f"Quantities: {entry['quantities']}")
            print(f"Sent At: {entry['sent_at']}")
            if entry['quote_no']:
                print(f"Quote Number: {entry['quote_no']}")
            print("-" * 80)

        return

    # Validate arguments
    is_valid, error_message = validate_args(args)
    if not is_valid:
        logger.error(f"Invalid arguments: {error_message}")
        sys.exit(1)

    # Load configuration
    config = load_config(args.config_dir)

    # Get attachments
    attachments = get_attachments(args.part_no, args.process, args.file_location)

    # Parse quantities
    quantities = [int(q.strip()) for q in args.quantities.split(",")]

    # Get matching vendors for the process
    matching_vendors = []
    for vendor in config["vendors"]["vendors"]:
        if args.process.lower() in [p.lower() for p in vendor.get("processes", [])]:
            matching_vendors.append(vendor)

    if not matching_vendors:
        logger.warning(f"No vendors found for process: {args.process}")
        sys.exit(1)

    logger.info(f"Found {len(matching_vendors)} vendors for process: {args.process}")

    # Prepare email context
    email_context = {
        "part_no": args.part_no,
        "process": args.process,
        "spec": args.spec,
        "quantities": quantities,
        "attachments": attachments,
        "sender_name": config["email"]["smtp"]["from_name"],
        "sender_email": config["email"]["smtp"]["from_email"],
        "company_name": config["email"]["settings"].get("company_name", "Your Company"),
        "due_date": (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
    }

    # Send emails to each vendor
    success_count = 0
    for vendor in matching_vendors:
        # Add vendor to context
        context = {**email_context, "vendor": vendor}

        # Render templates
        cover_letter = render_template("cover_letter.j2", context)
        pricing_form = render_template("pricing_form.j2", context)

        # Apply CUI compliance handling to the cover letter
        cover_letter = handle_cui_compliance(vendor, cover_letter)

        # Create pricing form file
        pricing_form_path = os.path.join(
            "temp",
            f"pricing_form_{args.part_no}_{vendor['name'].replace(' ', '_')}.md"
        )
        os.makedirs("temp", exist_ok=True)
        with open(pricing_form_path, "w") as f:
            f.write(pricing_form)

        # Add pricing form to attachments
        all_attachments = attachments + [pricing_form_path]

        # Send email
        subject = f"{config['email']['settings'].get('subject_prefix', '[RFQ]')} {args.part_no} - {args.process}"

        # Add CUI indicator to subject if vendor has CUI approval
        if vendor.get("approval_level", "").lower() == "cui":
            subject = f"[CUI] {subject}"

        if send_email(
            vendor["email"],
            subject,
            cover_letter,
            all_attachments,
            config,
            args.dry_run,
        ):
            success_count += 1

            # Log to database
            if not args.dry_run:
                log_rfq(
                    conn,
                    args.part_no,
                    args.process,
                    vendor["name"],
                    vendor["email"],
                    quantities,
                )
                logger.info(f"Logged RFQ to database for vendor: {vendor['name']}")

        # Clean up temporary file
        if os.path.exists(pricing_form_path) and not args.dry_run:
            os.remove(pricing_form_path)

    # Log results
    logger.info(f"Sent {success_count} of {len(matching_vendors)} RFQ emails")

    # Close database connection
    conn.close()

    logger.info("RFQ processing completed")


if __name__ == "__main__":
    main()
