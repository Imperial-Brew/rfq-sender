"""
Test Email with Box Integration Script

This script tests the email functionality with Box integration by creating a draft email
with attachments, which will be uploaded to Box instead of being attached directly.

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
from dotenv import load_dotenv

# Import the functions we want to test
from email_from_list import create_draft_email


def setup_logging(logs_dir: str) -> logging.Logger:
    """Set up logging configuration."""
    os.makedirs(logs_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(logs_dir, "test_email_with_box.log")),
        ],
    )
    return logging.getLogger("test_email_with_box")


def main() -> None:
    """Main entry point for the script."""
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(project_root, "logs")
        
        # Set up logging
        logger = setup_logging(logs_dir)
        
        # Load environment variables
        load_dotenv()
        logger.info("Loaded environment variables from .env file")
        
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
        
        # Find some test files to attach
        test_files = []
        docs_dir = os.path.join(project_root, "docs")
        
        # Look for files larger than 1MB
        for root, _, files in os.walk(docs_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    if file_size_mb > 1.0:
                        test_files.append(file_path)
                        logger.info(f"Found test file: {file_path} ({file_size_mb:.2f} MB)")
                        if len(test_files) >= 3:  # Limit to 3 files
                            break
            if len(test_files) >= 3:
                break
                
        if not test_files:
            logger.error("No test files found")
            sys.exit(1)
        
        # Create draft email with attachments
        logger.info(f"Creating draft email with {len(test_files)} attachments")
        
        # Generate a unique quote_id and process for the test
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quote_id = f"TEST_{timestamp}"
        process = "TEST_PROCESS"
        
        success = create_draft_email(
            outlook=outlook,
            recipient=to_email,
            subject=subject,
            body=body,
            attachments=test_files,
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
