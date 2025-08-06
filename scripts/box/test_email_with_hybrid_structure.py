"""
Test Email with Hybrid Box Structure Script

This script tests the email functionality with the new hybrid Box folder structure by creating
a draft email with attachments, which will be organized in the hybrid folder structure.

Usage:
    python scripts\box\test_email_with_hybrid_structure.py

Requirements:
    - boxsdk package must be installed (pip install boxsdk)
    - pywin32 package must be installed (pip install pywin32)
    - 0__config.json file with Box JWT credentials
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

# Add the parent directory to the path so we can import from email
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from email_from_list import create_draft_email


def setup_logging() -> logging.Logger:
    """Set up logging configuration using the centralized LoggingConfig."""
    return LoggingConfig.setup_logging(__name__, "test_email_with_hybrid_structure.log")


def create_test_files(test_dir: str, part_numbers: list) -> dict:
    """
    Create test files for each part number.
    
    Args:
        test_dir: Directory to create test files in
        part_numbers: List of part numbers
        
    Returns:
        Dictionary mapping part numbers to lists of file paths
    """
    os.makedirs(test_dir, exist_ok=True)
    
    all_files = []
    
    for part_number in part_numbers:
        # Create a drawing file
        drawing_path = os.path.join(test_dir, f"{part_number}_drawing.txt")
        with open(drawing_path, "w") as f:
            f.write(f"This is a test drawing for part {part_number}")
        all_files.append(drawing_path)
        
        # Create a spec file
        spec_path = os.path.join(test_dir, f"{part_number}_spec.txt")
        with open(spec_path, "w") as f:
            f.write(f"This is a test spec for part {part_number}")
        all_files.append(spec_path)
    
    return all_files


def main() -> None:
    """Main entry point for the script."""
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logs_dir = os.path.join(project_root, "logs")
        
        # Set up logging using the centralized LoggingConfig
        logger = setup_logging()
        
        # Environment variables already loaded by init_config()
        logger.info("Environment variables loaded by init_config()")
        
        # Create Outlook application object
        outlook = win32.Dispatch("Outlook.Application")
        
        # Define test parameters
        to_email = "test@example.com"
        subject = "Test Email with Hybrid Box Structure"
        body = """
        <h2>Test Email with Hybrid Box Structure</h2>
        <p>This email tests the hybrid Box folder structure functionality in email_from_list.py.</p>
        <p>Files should be organized by part number in the Box folder structure.</p>
        """
        
        # Create test directory
        test_dir = os.path.join(project_root, "scripts", "temp", "test_email_hybrid")
        os.makedirs(test_dir, exist_ok=True)
        
        # Define test parameters
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quote_id = f"TEST_QT_{timestamp}"
        process = "TEST_PROCESS"
        part_numbers = ["PN-001", "PN-002", "PN-003"]
        
        logger.info(f"Test parameters:")
        logger.info(f"  Quote ID: {quote_id}")
        logger.info(f"  Process: {process}")
        logger.info(f"  Part numbers: {part_numbers}")
        
        # Create test files
        logger.info("Creating test files")
        test_files = create_test_files(test_dir, part_numbers)
        
        logger.info(f"Created {len(test_files)} test files")
        for file_path in test_files:
            logger.info(f"  {file_path}")
        
        # Create draft email with attachments
        logger.info(f"Creating draft email with {len(test_files)} attachments")
        
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
            print("Check if files were organized by part number in the Box folder structure.")
            print("Verify that a share link to the vendor folder is included in the email.")
        else:
            logger.error("Failed to create test email.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Script failed with unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()