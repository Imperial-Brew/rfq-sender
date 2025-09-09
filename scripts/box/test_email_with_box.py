"""
Test Email with Box Integration Script

This script tests the email functionality with Box integration by creating a draft email
that assumes large files are shared via Box links instead of being attached directly.

Usage:
    python scripts\test_email_with_box.py

Requirements:
    - boxsdk package must be installed (pip install boxsdk)
    - pywin32 package must be installed (pip install pywin32)
    - 0__config.json file with Box JWT credentials (client ID, client secret, private key, etc.)
    - No environment variables are needed for Box as JWT authentication is used
"""

import logging
import os
import sys
from datetime import datetime

import win32com.client as win32

# Add parent directory to path to import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import Paths, LoggingConfig, init_config

# Initialize configuration
init_config()

# Import the functions we want to test
from email_from_list import create_draft_email


def setup_logging() -> logging.Logger:
    """Set up logging configuration using the centralized LoggingConfig."""
    return LoggingConfig.setup_logging(__name__, "test_email_with_box.log")


def main() -> None:
    """Main entry point for the script."""
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(project_root, "logs")
        
        # Set up logging using the centralized LoggingConfig
        logger = setup_logging()
        
        # Environment variables already loaded by init_config()
        logger.info("Environment variables loaded by init_config()")
        
        # Create Outlook application object
        outlook = win32.Dispatch("Outlook.Application")
        
        # Define test parameters
        to_email = "test@example.com"
        subject = "Test Email with Box Integration"
        body = """
        <h2>Test Email with Box Integration</h2>
        <p>This email tests the Box integration functionality in email_from_list.py.</p>
        <p>Large attachments should be uploaded to Box and a share link should be included in this email.</p>
        """
        
        # Create draft email (no attachments; files should be shared via Box links)
        logger.info("Creating draft email without attachments")
        
        # Generate a unique quote_id and process for the test
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quote_id = f"TEST_{timestamp}"
        process = "TEST_PROCESS"
        
        success = create_draft_email(
            outlook=outlook,
            recipient=to_email,
            subject=subject,
            body=body,
            logger=logger,
            html_format=True,
            use_outlook_signature=False,
            quote_id=quote_id,
            process=process
        )
        
        if success:
            logger.info("Test email created successfully. Please review it in Outlook.")
            print("\nTest email created successfully. Please review it in Outlook.")
            print("Check if large attachments were uploaded to Box and a share link is included in the email.")
        else:
            logger.error("Failed to create test email.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Script failed with unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
