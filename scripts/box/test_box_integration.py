"""
Test Box Integration Script

This script tests the Box integration by creating a folder, uploading files,
and creating a share link.

Usage:
    python scripts\test_box_integration.py

Requirements:
    - boxsdk package must be installed (pip install boxsdk)
    - 0__config.json file with Box JWT credentials (client ID, client secret, private key, etc.)
    - No environment variables are needed as JWT authentication is used
"""

import logging
import os
import sys
from datetime import datetime

import pandas as pd

# Add parent directory to path to import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import Paths, LoggingConfig, init_config

# Initialize configuration
init_config()

from box_integration import BoxIntegration


def setup_logging() -> logging.Logger:
    """Set up logging configuration using the centralized LoggingConfig."""
    return LoggingConfig.setup_logging(__name__, "test_box_integration.log")


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
        
        # Initialize Box integration
        logger.info("Initializing Box integration")
        box = BoxIntegration(logger)
        
        if not box.client:
            logger.error("Failed to initialize Box client. Check your credentials.")
            sys.exit(1)
        
        # Create a test folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"Test_Folder_{timestamp}"
        logger.info(f"Creating test folder: {folder_name}")
        
        folder = box.create_folder(folder_name)
        
        if not folder:
            logger.error("Failed to create Box folder")
            sys.exit(1)
            
        logger.info(f"Created folder: {folder_name} (ID: {folder.id})")
        
        # Find some test files to upload
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
            
        # Upload test files
        logger.info(f"Uploading {len(test_files)} files to Box")
        
        for file_path in test_files:
            file_name = os.path.basename(file_path)
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f"Uploading: {file_name} ({file_size_mb:.2f} MB)")
            
            uploaded_file = box.upload_file(file_path, folder)
            
            if uploaded_file:
                logger.info(f"Uploaded file: {file_name} (ID: {uploaded_file.id})")
            else:
                logger.error(f"Failed to upload file: {file_name}")
        
        # Create share link
        logger.info("Creating share link for folder")
        share_link = box.create_share_link(folder)
        
        if not share_link:
            logger.error("Failed to create Box share link")
            sys.exit(1)
            
        logger.info(f"Created share link: {share_link}")
        
        # Test complete
        logger.info("Box integration test completed successfully")
        print(f"\nBox integration test completed successfully!")
        print(f"Share link: {share_link}")
        
    except Exception as e:
        print(f"Script failed with unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
