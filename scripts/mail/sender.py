"""Email sending helpers for the RFQ sender script."""

from __future__ import annotations

import logging
import os
import smtplib
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Tuple

import sys

# Allow importing from the ``core`` package which lives at the repository root.
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import SecurityConfig, LoggingConfig, init_config  # noqa: E402

init_config()
logger = LoggingConfig.setup_logging(__name__, "rfq_sender.log")


def validate_email(email: str) -> bool:
    """Validate email format."""

    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def check_attachments(attachments: List[str]) -> Tuple[bool, List[str], List[str]]:
    """Check that attachments exist and are readable."""

    valid_attachments: List[str] = []
    invalid_attachments: List[str] = []

    for file_path in attachments:
        if os.path.exists(file_path) and os.access(file_path, os.R_OK):
            valid_attachments.append(file_path)
        else:
            invalid_attachments.append(file_path)

    return len(invalid_attachments) == 0, valid_attachments, invalid_attachments


def handle_cui_compliance(vendor: Dict[str, any], body: str) -> str:
    """Handle CUI compliance based on vendor approval level."""

    enable_cui_protection = SecurityConfig.ENABLE_CUI_PROTECTION
    if not enable_cui_protection:
        return body

    approval_level = vendor.get("approval_level", "").lower()

    if approval_level == "cui":
        cui_warning = SecurityConfig.CUI_WARNING
        modified_body = f"{cui_warning}\n\n{body}\n\n{cui_warning}"
        logger.info("Added CUI warning to email for CUI-approved vendor: %s", vendor["name"])
        return modified_body
    else:
        logger.info("Vendor %s is not approved for CUI data", vendor.get("name", "unknown"))
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
    """Send an email with attachments.

    The function performs basic validation and supports a ``dry_run`` mode used
    in the tests to avoid network access.
    """

    if not validate_email(to_email):
        logger.error("Invalid email address: %s", to_email)
        return False

    all_valid, valid_attachments, invalid_attachments = check_attachments(attachments)
    if not all_valid:
        logger.warning("Some attachments are missing or not readable: %s", invalid_attachments)
        logger.warning("Proceeding with valid attachments: %s", valid_attachments)

    if dry_run:
        logger.info("[DRY RUN] Would send email to: %s", to_email)
        logger.info("[DRY RUN] Subject: %s", subject)
        logger.info("[DRY RUN] Body: %s...", body[:100])
        logger.info("[DRY RUN] Attachments: %s", valid_attachments)
        return True

    for attempt in range(1, max_retries + 1):
        try:
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = f"{config['email']['smtp']['from_name']} <{config['email']['smtp']['from_email']}>"
            msg["To"] = to_email

            if config["email"]["settings"].get("cc_emails"):
                cc_emails = config["email"]["settings"]["cc_emails"].split(",")
                msg["Cc"] = ", ".join(cc_emails)

            msg.attach(MIMEText(body, "plain"))

            for file_path in valid_attachments:
                try:
                    with open(file_path, "rb") as f:
                        attachment = MIMEApplication(f.read())
                        attachment.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(file_path)}",
                        )
                        msg.attach(attachment)
                except Exception as exc:
                    logger.error("Failed to attach file %s: %s", file_path, exc)

            with smtplib.SMTP(config["email"]["smtp"]["server"], int(config["email"]["smtp"]["port"])) as server:
                if config["email"]["smtp"]["use_tls"]:
                    server.starttls()
                server.login(
                    config["email"]["smtp"]["username"],
                    config["email"]["smtp"]["password"],
                )
                server.send_message(msg)

            logger.info("Email sent successfully to %s", to_email)
            return True

        except smtplib.SMTPServerDisconnected as exc:  # pragma: no cover - network dependent
            logger.warning(
                "SMTP server disconnected (attempt %d/%d): %s", attempt, max_retries, exc
            )
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                logger.error("Failed to send email after %d attempts", max_retries)
                return False
        except smtplib.SMTPException as exc:  # pragma: no cover - network dependent
            logger.warning("SMTP error (attempt %d/%d): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                logger.error("Failed to send email after %d attempts", max_retries)
                return False
        except Exception as exc:  # pragma: no cover - general error path
            logger.error("Failed to send email to %s: %s", to_email, exc)
            return False


__all__ = [
    "validate_email",
    "check_attachments",
    "handle_cui_compliance",
    "send_email",
]

