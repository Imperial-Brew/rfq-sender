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

import jinja2
import yaml
import questionary
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path to import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import SecurityConfig, LoggingConfig, init_config, Paths

# Get the project root directory (parent of scripts directory)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Initialize configuration
init_config()

# Import SpecProcessValidator from scripts.utils.spec_check
from scripts.utils.spec_check import SpecProcessValidator

console = Console()

# Set up logging using the centralized configuration
logger = LoggingConfig.setup_logging(__name__, "rfq_sender.log")

# Import split-out helpers
from .cli import parse_args, validate_args  # noqa: E402
from .config import init_database  # noqa: E402


def load_config(config_dir: str) -> dict:  # pragma: no cover - legacy wrapper
    """Wrapper for :func:`scripts.email.config.load_config` for backwards compatibility."""
    from .config import load_config as _load_config
    return _load_config(config_dir)


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


def init_database() -> sqlite3.Connection:  # pragma: no cover - legacy wrapper
    """Wrapper for :func:`scripts.email.config.init_database` for backwards compatibility."""
    from .config import init_database as _init_database
    return _init_database()


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


def validate_email(email: str) -> bool:  # pragma: no cover - legacy wrapper
    """Wrapper for :func:`scripts.email.sender.validate_email`."""
    from .sender import validate_email as _validate_email
    return _validate_email(email)


def check_attachments(attachments: List[str]) -> Tuple[bool, List[str], List[str]]:  # pragma: no cover - legacy wrapper
    """Wrapper for :func:`scripts.email.sender.check_attachments`."""
    from .sender import check_attachments as _check_attachments
    return _check_attachments(attachments)


def handle_cui_compliance(vendor: Dict[str, any], body: str) -> str:  # pragma: no cover - legacy wrapper
    """Wrapper for :func:`scripts.email.sender.handle_cui_compliance`."""
    from .sender import handle_cui_compliance as _handle_cui_compliance
    return _handle_cui_compliance(vendor, body)


def send_email(
    to_email: str,
    subject: str,
    body: str,
    attachments: List[str],
    config: Dict[str, any],
    dry_run: bool = False,
    max_retries: int = 3,
) -> bool:  # pragma: no cover - legacy wrapper
    """Wrapper for :func:`scripts.email.sender.send_email`."""
    from .sender import send_email as _send_email
    return _send_email(to_email, subject, body, attachments, config, dry_run=dry_run, max_retries=max_retries)


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
