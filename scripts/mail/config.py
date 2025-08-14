"""Configuration and database helpers for the RFQ sender."""

from __future__ import annotations

import logging
import os
import sqlite3
import yaml
import sys

from typing import Dict


# Allow importing from the ``core`` package which lives at the repository root.
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import LoggingConfig, init_config  # noqa: E402

# Ensure global configuration is initialised before creating loggers.
init_config()

logger = LoggingConfig.setup_logging(__name__, "rfq_sender.log")

# Location of the repository root used to resolve ancillary files.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_config(config_dir: str) -> Dict:
    """Load configuration files.

    Parameters
    ----------
    config_dir : str
        Path to the configuration directory.

    Returns
    -------
    dict
        Consolidated configuration data.
    """

    config: Dict[str, Dict] = {}

    # Load vendor options to obtain the reference list of vendors
    vendor_options_file = os.path.join(PROJECT_ROOT, "docs", "OS", "vendor_options.yaml")
    vendor_options = {}
    if os.path.exists(vendor_options_file):
        try:
            with open(vendor_options_file, "r", encoding="utf-8") as f:
                vendor_options = yaml.safe_load(f)
            logger.info("Loaded vendor options from %s", vendor_options_file)
        except Exception as exc:  # pragma: no cover - fatal error path
            logger.error("Failed to load vendor options: %s", exc)
            sys.exit(1)
    else:  # pragma: no cover - fatal error path
        logger.error("Vendor options file not found: %s", vendor_options_file)
        sys.exit(1)

    # Extract vendor names and their processes from vendor_options.yaml
    vendor_processes = {}
    if "vendors" in vendor_options:
        for vendor in vendor_options["vendors"]:
            vendor_name = vendor.get("name", "")
            processes = []
            for process in vendor.get("processes", []):
                if isinstance(process, dict) and "name" in process:
                    processes.append(process["name"])
            vendor_processes[vendor_name] = processes
        logger.info("Found %d vendors in vendor_options.yaml", len(vendor_processes))
    else:  # pragma: no cover - fatal error path
        logger.error("No vendors found in vendor_options.yaml")
        sys.exit(1)

    # Now load contacts.yml to get contact information for the vendors
    contacts_file = os.path.join(config_dir, "contacts.yml")
    if os.path.exists(contacts_file):
        with open(contacts_file, "r", encoding="utf-8") as f:
            contacts_data = yaml.safe_load(f)
    else:  # pragma: no cover - fatal error path
        logger.error("Contacts file not found: %s", contacts_file)
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
            logger.warning(
                "Vendor '%s' found in vendor_options.yaml but not in contacts.yml", vendor_name
            )
            continue

        # Extract the email address from the primary contact
        email = None
        for contact in vendor_contact.get("contacts", []):
            if contact.get("primary", False):
                email = contact.get("email")
                break

        # Skip vendors without a primary contact email
        if not email:
            logger.warning("No primary contact email found for vendor '%s'", vendor_name)
            continue

        transformed_vendor = {
            "name": vendor_name,
            "email": email,
            "processes": processes,
        }

        transformed_vendors.append(transformed_vendor)
        logger.info("Added vendor '%s' with %d processes", vendor_name, len(processes))

    # Wrap the transformed vendors in another "vendors" key to match expectations
    config["vendors"] = {"vendors": transformed_vendors}

    # Load email configuration
    email_file = os.path.join(config_dir, "email.yml")
    if os.path.exists(email_file):
        with open(email_file, "r", encoding="utf-8") as f:
            config["email"] = yaml.safe_load(f)
    else:  # pragma: no cover - fatal error path
        logger.error("Email configuration file not found: %s", email_file)
        sys.exit(1)

    return config


def init_database() -> sqlite3.Connection:
    """Initialise the SQLite database for RFQ tracking."""

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    db_path = os.path.join(data_dir, "rfq_log.db")
    conn = sqlite3.connect(db_path)

    cursor = conn.cursor()
    cursor.execute(
        """
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
        """
    )
    conn.commit()
    return conn


__all__ = ["load_config", "init_database"]

