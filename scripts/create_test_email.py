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

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

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
        logging.FileHandler(os.path.join(logs_dir, "create_test_email.log")),
    ],
)
logger = logging.getLogger("create_test_email")

def create_outlook_draft(to_email: str, subject: str, body: str) -> bool:
    """
    Create a draft email in Outlook.

    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        body (str): Email body

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

def main() -> None:
    """Main entry point for the script."""
    # Load environment variables from .env file
    load_dotenv()

    # Get email configuration from environment variables
    from_email = os.environ.get("SMTP_FROM_EMAIL", "your_email@example.com")
    from_name = os.environ.get("SMTP_FROM_NAME", "RFQ System")

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

    success = create_outlook_draft(to_email, subject, body)

    if success:
        logger.info("Test email created successfully. Please review it in Outlook.")
    else:
        logger.error("Failed to create test email.")
        sys.exit(1)

if __name__ == "__main__":
    main()
