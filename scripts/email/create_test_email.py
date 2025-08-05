"""
Create Test Email Script

This script creates a draft email in Outlook with a test subject and body.
It does not send the email, but displays it for review.

Usage:
    python scripts\create_test_email.py

Requirements:
    - pywin32 package must be installed (pip install pywin32)
    - Outlook must be installed and configured on the system
    - .env file with email configuration (see .env.example)

Environment Variables:
    - SMTP_FROM_EMAIL: Email address to use as sender
    - SMTP_FROM_NAME: Name to use as sender
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


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
            logging.FileHandler(os.path.join(logs_dir, "create_test_email.log")),
        ],
    )
    return logging.getLogger("create_test_email")


def create_outlook_draft(to_email: str, subject: str, body: str, logger: logging.Logger) -> bool:
    """
    Create a draft email in Outlook.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body
        logger: Logger object for logging messages

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Import win32com here to avoid issues if it's not installed
        import win32com.client

        # Create Outlook application object
        outlook = win32com.client.Dispatch("Outlook.Application")

        # Create a new email
        mail = outlook.CreateItem(0)  # 0 = olMailItem

        # Set email properties
        mail.To = to_email
        mail.Subject = subject
        mail.Body = body

        # Display the email without sending it
        mail.Display(True)  # True = modal window

        logger.info(f"Created draft email to {to_email}")
        return True

    except ImportError:
        logger.error("win32com is not installed. Please install it with: pip install pywin32")
        return False
    except Exception as e:
        logger.error(f"Failed to create draft email: {str(e)}")
        return False


def get_env_variable(var_name: str, default: Optional[str] = None, logger: logging.Logger = None) -> str:
    """
    Get environment variable with validation.

    Args:
        var_name: Name of the environment variable
        default: Default value if environment variable is not set
        logger: Logger object for logging messages

    Returns:
        Value of the environment variable or default

    Raises:
        ValueError: If environment variable is not set and no default is provided
    """
    value = os.environ.get(var_name, default)

    if value is None:
        error_msg = f"Environment variable {var_name} is not set and no default provided"
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg)

    return value


def main() -> None:
    """Main entry point for the script."""
    try:
        # Get the project root directory (parent of scripts directory)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(project_root, "logs")

        # Set up logging
        logger = setup_logging(logs_dir)

        # Load environment variables from .env file
        load_dotenv()
        logger.info("Loaded environment variables from .env file")

        # Get email configuration from environment variables with validation
        try:
            from_email = get_env_variable("SMTP_FROM_EMAIL", "your_email@example.com", logger)
            from_name = get_env_variable("SMTP_FROM_NAME", "RFQ System", logger)
        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            sys.exit(1)

        # Log environment variable values
        logger.info(f"Using sender email: {from_email}")
        logger.info(f"Using sender name: {from_name}")

        # Create test email
        to_email = "example@example.com"
        subject = "TEST"
        body = f"""TEST EMAIL

From: {from_name} <{from_email}>

This is a test email created using the RFQ Sender system.
No action is required.
        """

        logger.info(f"Creating test email from {from_email} to {to_email}")

        success = create_outlook_draft(to_email, subject, body, logger)

        if success:
            logger.info("Test email created successfully. Please review it in Outlook.")
        else:
            logger.error("Failed to create test email.")
            sys.exit(1)

    except Exception as e:
        # Catch any unexpected exceptions
        print(f"Script failed with unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
