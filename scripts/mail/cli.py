"""Command line interface helpers for the RFQ sender.

This module exposes the argument parsing and validation logic that was
previously embedded directly in ``rfq_sender.py``.  Keeping the functions in a
dedicated module makes them easier to test in isolation and keeps the main
script lightweight.
"""

from __future__ import annotations

import argparse
import os
from typing import Optional, Tuple


# Determine the project root so the default configuration directory can be
# resolved relative to this file.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        The parsed command line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Send RFQ emails to vendors for finishing, material, and hardware quotes.",
    )

    # Add interactive mode flag
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode with a user-friendly interface",
    )

    # Required arguments (not required if in interactive mode)
    parser.add_argument(
        "--part_no",
        help="Part number (e.g. 0250-20000)",
    )
    parser.add_argument(
        "--process",
        help="Process name (e.g. 'cleaning', 'anodizing')",
    )
    parser.add_argument(
        "--file_location",
        help="Path to directory containing files to attach",
    )
    parser.add_argument(
        "--quantities",
        help="Comma-separated list of quantities (e.g. '1,2,5,10')",
    )

    # Optional arguments
    parser.add_argument(
        "--spec",
        help="Optional specification details",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print email contents without sending",
    )
    parser.add_argument(
        "--config-dir",
        default=os.path.join(PROJECT_ROOT, "config"),
        help="Path to configuration directory",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command")

    # Show log subcommand
    show_log_parser = subparsers.add_parser(
        "show-log",
        help="Show recent RFQ log entries",
    )
    show_log_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of log entries to show",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> Tuple[bool, Optional[str]]:
    """Validate command-line arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments.

    Returns
    -------
    Tuple[bool, Optional[str]]
        ``(is_valid, error_message)`` tuple.
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

    # Validate quantities
    if not args.quantities or not str(args.quantities).strip():
        return False, "Quantities must be comma-separated integers"

    try:
        quantities = [int(q.strip()) for q in str(args.quantities).split(",")]
    except ValueError:
        return False, "Quantities must be comma-separated integers"

    if any(q <= 0 for q in quantities):
        return False, "Quantities must be positive integers"

    # Store parsed quantities for later use
    args.cleaned_quantities = quantities
    return True, None


__all__ = ["parse_args", "validate_args"]

