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
import questionary
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

# Import SpecProcessValidator from spec_check.py
from spec_check import SpecProcessValidator

console = Console()

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

    # Add interactive mode flag
    parser.add_argument(
        "--interactive", 
        "-i", 
        action="store_true",
        help="Run in interactive mode with a user-friendly interface"
    )

    # Required arguments (not required if in interactive mode)
    parser.add_argument(
        "--part_no", 
        help="Part number (e.g. 0250-20000)"
    )
    parser.add_argument(
        "--process", 
        help="Process name (e.g. 'cleaning', 'anodizing')"
    )
    parser.add_argument(
        "--file_location", 
        help="Path to directory containing files to attach"
    )
    parser.add_argument(
        "--quantities", 
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
        default=os.path.join(project_root, "config"),
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

    # First, load vendor_options.yaml to get the reference list of vendors
    vendor_options_file = os.path.join(project_root, "docs", "OS", "vendor_options.yaml")
    vendor_options = {}
    if os.path.exists(vendor_options_file):
        try:
            with open(vendor_options_file, "r", encoding="utf-8") as f:
                vendor_options = yaml.safe_load(f)
            logger.info(f"Loaded vendor options from {vendor_options_file}")
        except Exception as e:
            logger.error(f"Failed to load vendor options: {str(e)}")
            sys.exit(1)
    else:
        logger.error(f"Vendor options file not found: {vendor_options_file}")
        sys.exit(1)

    # Extract vendor names and their processes from vendor_options.yaml
    vendor_processes = {}
    if "vendors" in vendor_options:
        for vendor in vendor_options["vendors"]:
            vendor_name = vendor.get("name", "")
            processes = []
            for process in vendor.get("processes", []):
                if isinstance(process, dict) and "name" in process:
                    process_name = process["name"]
                    processes.append(process_name)
            vendor_processes[vendor_name] = processes
        logger.info(f"Found {len(vendor_processes)} vendors in vendor_options.yaml")
    else:
        logger.error("No vendors found in vendor_options.yaml")
        sys.exit(1)

    # Now load contacts.yml to get contact information for the vendors
    contacts_file = os.path.join(config_dir, "contacts.yml")
    if os.path.exists(contacts_file):
        with open(contacts_file, "r") as f:
            contacts_data = yaml.safe_load(f)
    else:
        logger.error(f"Contacts file not found: {contacts_file}")
        sys.exit(1)

    # Create transformed vendor objects only for vendors in vendor_options.yaml
    transformed_vendors = []
    for vendor_name, processes in vendor_processes.items():
        # Find this vendor in contacts.yml
        vendor_contact = None
        for contact_vendor in contacts_data.get("vendors", []):
            if contact_vendor.get("name", "") == vendor_name:
                vendor_contact = contact_vendor
                break

        if not vendor_contact:
            logger.warning(f"Vendor '{vendor_name}' found in vendor_options.yaml but not in contacts.yml")
            continue

        # Extract the email address from the primary contact
        email = None
        for contact in vendor_contact.get("contacts", []):
            if contact.get("primary", False):
                email = contact.get("email")
                break

        # Skip vendors without a primary contact email
        if not email:
            logger.warning(f"No primary contact email found for vendor '{vendor_name}'")
            continue

        # Create a transformed vendor object
        transformed_vendor = {
            "name": vendor_name,
            "email": email,
            "processes": processes
        }

        transformed_vendors.append(transformed_vendor)
        logger.info(f"Added vendor '{vendor_name}' with {len(processes)} processes")

    # Wrap the transformed vendors in another "vendors" key to match what the code expects
    config["vendors"] = {"vendors": transformed_vendors}

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
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "templates")
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


def validate_process_name(process: str) -> str:
    """
    Validate a process name using SpecProcessValidator.

    If the process name is not found, suggest similar processes and allow the user to select one.
    If no similar processes are found or the user doesn't select one, offer to add a new process.

    Args:
        process: The process name to validate

    Returns:
        The validated/selected/added process name
    """
    # Initialize the validator
    validator = SpecProcessValidator()

    # Check if the process exists
    exists, normalized, suggestions = validator.check_process(process)

    if exists:
        # Process exists, return the normalized name
        logger.info(f"Process '{process}' is valid. Normalized: '{normalized}'")
        return normalized

    # Process doesn't exist
    logger.warning(f"Process '{process}' not found. Normalized: '{normalized}'")

    if suggestions:
        # Suggest similar processes
        console.print(f"[yellow]Process '{process}' not recognized.[/yellow]")

        # Add "Add a new process" option
        choices = [
            questionary.Choice(title=f"Did you mean: {suggestion}", value=suggestion)
            for suggestion in suggestions
        ]
        choices.append(questionary.Choice(title="Add a new process", value="__add_new__"))
        choices.append(questionary.Choice(title="Use as entered", value="__use_as_is__"))

        selected = questionary.select(
            "Select an option:",
            choices=choices
        ).ask()

        if selected == "__add_new__":
            # Add a new process
            add_to_specific = questionary.confirm(
                "Add to a specific vendor?",
                default=False
            ).ask()

            vendor_name = None
            if add_to_specific:
                # Get list of vendor names
                vendor_names = [v['name'] for v in validator.ref['vendors']]
                vendor_name = questionary.select(
                    "Select the vendor:",
                    choices=vendor_names
                ).ask()

            success = validator.add_process(process, vendor_name)

            if success:
                console.print(f"[green]✅ Process '{process}' added successfully.[/green]")
                return process
            else:
                console.print(f"[red]❌ Process '{process}' could not be added.[/red]")
                return process
        elif selected == "__use_as_is__":
            # Use the process name as entered
            return process
        else:
            # Use the selected suggestion
            logger.info(f"Using suggested process: '{selected}'")
            return selected
    else:
        # No suggestions found
        console.print(f"[yellow]No similar processes found for '{process}'.[/yellow]")

        # Ask if the user wants to add a new process
        add_new = questionary.confirm(
            "Would you like to add a new process?",
            default=True
        ).ask()

        if add_new:
            # Add a new process
            add_to_specific = questionary.confirm(
                "Add to a specific vendor?",
                default=False
            ).ask()

            vendor_name = None
            if add_to_specific:
                # Get list of vendor names
                vendor_names = [v['name'] for v in validator.ref['vendors']]
                vendor_name = questionary.select(
                    "Select the vendor:",
                    choices=vendor_names
                ).ask()

            success = validator.add_process(process, vendor_name)

            if success:
                console.print(f"[green]✅ Process '{process}' added successfully.[/green]")
                return process
            else:
                console.print(f"[red]❌ Process '{process}' could not be added.[/red]")
                return process
        else:
            # Use the process name as entered
            return process


def validate_spec_name(spec: str, process: str) -> str:
    """
    Validate a spec name using SpecProcessValidator.

    If the spec name is not found, suggest similar specs and allow the user to select one.
    If no similar specs are found or the user doesn't select one, offer to add a new spec.

    Args:
        spec: The spec name to validate
        process: The process name to associate with the spec

    Returns:
        The validated/selected/added spec name
    """
    # If spec is empty, return it as is
    if not spec:
        return spec

    # Initialize the validator
    validator = SpecProcessValidator()

    # Check if the spec exists
    exists, normalized, suggestions = validator.check_spec(spec)

    if exists:
        # Spec exists, return the normalized name
        logger.info(f"Spec '{spec}' is valid. Normalized: '{normalized}'")
        return normalized

    # Spec doesn't exist
    logger.warning(f"Spec '{spec}' not found. Normalized: '{normalized}'")

    if suggestions:
        # Suggest similar specs
        console.print(f"[yellow]Spec '{spec}' not recognized.[/yellow]")

        # Add "Add a new spec" option
        choices = [
            questionary.Choice(title=f"Did you mean: {suggestion}", value=suggestion)
            for suggestion in suggestions
        ]
        choices.append(questionary.Choice(title="Add a new spec", value="__add_new__"))
        choices.append(questionary.Choice(title="Use as entered", value="__use_as_is__"))

        selected = questionary.select(
            "Select an option:",
            choices=choices
        ).ask()

        if selected == "__add_new__":
            # Add a new spec
            add_to_specific = questionary.confirm(
                "Add to a specific vendor?",
                default=False
            ).ask()

            vendor_name = None
            if add_to_specific:
                # Get list of vendor names
                vendor_names = [v['name'] for v in validator.ref['vendors']]
                vendor_name = questionary.select(
                    "Select the vendor:",
                    choices=vendor_names
                ).ask()

            success = validator.add_spec(spec, process, vendor_name)

            if success:
                console.print(f"[green]✅ Spec '{spec}' added successfully to process '{process}'.[/green]")
                return spec
            else:
                console.print(f"[red]❌ Spec '{spec}' could not be added.[/red]")
                return spec
        elif selected == "__use_as_is__":
            # Use the spec name as entered
            return spec
        else:
            # Use the selected suggestion
            logger.info(f"Using suggested spec: '{selected}'")
            return selected
    else:
        # No suggestions found
        console.print(f"[yellow]No similar specs found for '{spec}'.[/yellow]")

        # Ask if the user wants to add a new spec
        add_new = questionary.confirm(
            "Would you like to add a new spec?",
            default=True
        ).ask()

        if add_new:
            # Add a new spec
            add_to_specific = questionary.confirm(
                "Add to a specific vendor?",
                default=False
            ).ask()

            vendor_name = None
            if add_to_specific:
                # Get list of vendor names
                vendor_names = [v['name'] for v in validator.ref['vendors']]
                vendor_name = questionary.select(
                    "Select the vendor:",
                    choices=vendor_names
                ).ask()

            success = validator.add_spec(spec, process, vendor_name)

            if success:
                console.print(f"[green]✅ Spec '{spec}' added successfully to process '{process}'.[/green]")
                return spec
            else:
                console.print(f"[red]❌ Spec '{spec}' could not be added.[/red]")
                return spec
        else:
            # Use the spec name as entered
            return spec


def interactive_show_log(conn: sqlite3.Connection) -> None:
    """
    Show RFQ log entries in an interactive way.

    Args:
        conn: Database connection
    """
    # Ask for the number of log entries to show
    limit = questionary.text(
        "Number of log entries to show:",
        default="10"
    ).ask()

    try:
        limit = int(limit)
        log_entries = show_rfq_log(conn, limit)

        if not log_entries:
            console.print("[yellow]No RFQ log entries found[/yellow]")
            return

        # Display log entries in a table
        table = Table(title=f"RFQ Log Entries (Last {limit})")
        table.add_column("ID")
        table.add_column("Part Number")
        table.add_column("Process")
        table.add_column("Vendor")
        table.add_column("Sent At")
        table.add_column("Quote Number")

        for entry in log_entries:
            table.add_row(
                str(entry['id']),
                entry['part_no'],
                entry['process'],
                f"{entry['vendor_name']} ({entry['vendor_email']})",
                entry['sent_at'],
                entry['quote_no'] or "N/A"
            )

        console.print(table)

    except ValueError:
        console.print("[red]Invalid number of entries[/red]")


def interactive_mode(conn: sqlite3.Connection) -> None:
    """
    Run the script in interactive mode with a user-friendly interface.

    Args:
        conn: Database connection
    """
    console.print(Panel.fit(
        "[bold blue]RFQ Sender - Interactive Mode[/bold blue]\n\n"
        "This tool helps you send RFQ emails to vendors for finishing, material, and hardware quotes.",
        title="Welcome",
        border_style="green"
    ))

    # Main menu
    while True:
        action = questionary.select(
            "What would you like to do?",
            choices=[
                "Send a new RFQ",
                "View RFQ log",
                "Exit"
            ]
        ).ask()

        if action == "Exit":
            console.print("[green]Goodbye![/green]")
            break

        elif action == "View RFQ log":
            interactive_show_log(conn)

        elif action == "Send a new RFQ":
            # Get RFQ details interactively
            part_no = questionary.text(
                "Part number:",
                validate=lambda text: len(text.strip()) > 0
            ).ask()

            process_input = questionary.text(
                "Process name:",
                validate=lambda text: len(text.strip()) > 0
            ).ask()

            # Validate the process name
            process = validate_process_name(process_input)

            file_location = questionary.path(
                "Path to directory containing files to attach:"
            ).ask()

            quantities_str = questionary.text(
                "Comma-separated list of quantities (e.g. '1,2,5,10'):",
                validate=lambda text: all(q.strip().isdigit() for q in text.split(","))
            ).ask()

            spec_input = questionary.text(
                "Specification details (optional):"
            ).ask()

            # Validate the spec name if provided
            spec = validate_spec_name(spec_input, process) if spec_input else ""

            dry_run = questionary.confirm(
                "Perform a dry run (don't actually send emails)?",
                default=False
            ).ask()

            # Load configuration
            config_dir = os.path.join(project_root, "config")
            config = load_config(config_dir)

            # Get attachments with progress indicator
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
            ) as progress:
                task = progress.add_task("Finding attachments...", total=1)
                attachments = get_attachments(part_no, process, file_location)
                progress.update(task, completed=1)

            # Parse quantities
            quantities = [int(q.strip()) for q in quantities_str.split(",")]

            # Get matching vendors for the process
            matching_vendors = []
            for vendor in config["vendors"]["vendors"]:
                if process.lower() in [p.lower() for p in vendor.get("processes", [])]:
                    matching_vendors.append(vendor)

            if not matching_vendors:
                console.print(f"[red]No vendors found for process: {process}[/red]")
                continue

            # Let user select which vendors to send to
            vendor_choices = [
                questionary.Choice(
                    title=f"{vendor['name']} ({vendor['email']})",
                    value=vendor
                )
                for vendor in matching_vendors
            ]

            selected_vendors = questionary.checkbox(
                "Select vendors to send RFQ to:",
                choices=vendor_choices
            ).ask()

            if not selected_vendors:
                console.print("[yellow]No vendors selected, returning to main menu[/yellow]")
                continue

            # Prepare email context
            email_context = {
                "part_no": part_no,
                "process": process,
                "spec": spec,
                "quantities": quantities,
                "attachments": attachments,
                "sender_name": config["email"]["smtp"]["from_name"],
                "sender_email": config["email"]["smtp"]["from_email"],
                "company_name": config["email"]["settings"].get("company_name", "Your Company"),
                "due_date": (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
            }

            # Send emails with progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("Sending RFQs...", total=len(selected_vendors))

                success_count = 0
                for vendor in selected_vendors:
                    progress.update(task, description=f"Sending to {vendor['name']}...")

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
                        f"pricing_form_{part_no}_{vendor['name'].replace(' ', '_')}.md"
                    )
                    os.makedirs("temp", exist_ok=True)
                    with open(pricing_form_path, "w") as f:
                        f.write(pricing_form)

                    # Add pricing form to attachments
                    all_attachments = attachments + [pricing_form_path]

                    # Send email
                    subject = f"{config['email']['settings'].get('subject_prefix', '[RFQ]')} {part_no} - {process}"

                    # Add CUI indicator to subject if vendor has CUI approval
                    if vendor.get("approval_level", "").lower() == "cui":
                        subject = f"[CUI] {subject}"

                    if send_email(
                        vendor["email"],
                        subject,
                        cover_letter,
                        all_attachments,
                        config,
                        dry_run,
                    ):
                        success_count += 1

                        # Log to database
                        if not dry_run:
                            log_rfq(
                                conn,
                                part_no,
                                process,
                                vendor["name"],
                                vendor["email"],
                                quantities,
                            )

                    # Clean up temporary file
                    if os.path.exists(pricing_form_path) and not dry_run:
                        os.remove(pricing_form_path)

                    progress.advance(task)

            console.print(f"[green]Successfully sent {success_count}/{len(selected_vendors)} RFQs[/green]")


def main():
    """Main entry point for the script."""

    # Initialize database
    conn = init_database()

    # Parse arguments
    args = parse_args()

    # Check if we should run in interactive mode
    if args.interactive:
        try:
            interactive_mode(conn)
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
        conn.close()
        return

    # Handle subcommands
    if args.command == "show-log":
        # Show recent RFQ log entries
        logger.info(f"Showing last {args.limit} log entries")
        log_entries = show_rfq_log(conn, args.limit)

        if not log_entries:
            console.print("[yellow]No RFQ log entries found[/yellow]")
            return

        # Print log entries in a table
        table = Table(title=f"RFQ Log Entries (Last {args.limit})")
        table.add_column("ID")
        table.add_column("Part Number")
        table.add_column("Process")
        table.add_column("Vendor")
        table.add_column("Sent At")
        table.add_column("Quote Number")

        for entry in log_entries:
            table.add_row(
                str(entry['id']),
                entry['part_no'],
                entry['process'],
                f"{entry['vendor_name']} ({entry['vendor_email']})",
                entry['sent_at'],
                entry['quote_no'] or "N/A"
            )

        console.print(table)
        conn.close()
        return

    # Check if required arguments are provided
    if not all([args.part_no, args.process, args.file_location, args.quantities]):
        console.print("[red]Error: Missing required arguments. Use --interactive for guided input or provide all required arguments.[/red]")
        console.print("Required arguments: --part_no, --process, --file_location, --quantities")
        sys.exit(1)

    # Validate arguments
    is_valid, error_message = validate_args(args)
    if not is_valid:
        logger.error(f"Invalid arguments: {error_message}")
        console.print(f"[red]Invalid arguments: {error_message}[/red]")
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
        console.print(f"[red]No vendors found for process: {args.process}[/red]")
        sys.exit(1)

    logger.info(f"Found {len(matching_vendors)} vendors for process: {args.process}")
    console.print(f"[green]Found {len(matching_vendors)} vendors for process: {args.process}[/green]")

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
    console.print(f"[bold green]Sent {success_count} of {len(matching_vendors)} RFQ emails[/bold green]")

    # Close database connection
    conn.close()

    logger.info("RFQ processing completed")
    console.print("[bold green]RFQ processing completed[/bold green]")


if __name__ == "__main__":
    main()
