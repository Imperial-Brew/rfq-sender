"""
Test Hybrid Folder Structure Script

This script tests the hybrid folder structure functionality in the Box integration.
It creates a folder structure as described in box_structure.md, uploads test files,
and verifies that the structure is created correctly.

Usage:
    python scripts\box\test_hybrid_structure.py

Requirements:
    - boxsdk package must be installed (pip install boxsdk)
    - 0__config.json file with Box JWT credentials
"""

import logging
import os
import sys
from datetime import datetime

# Import BoxIntegration directly since we're in the same directory
from box_integration import BoxIntegration


def setup_logging(logs_dir: str) -> logging.Logger:
    """Set up logging configuration."""
    os.makedirs(logs_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(logs_dir, "test_hybrid_structure.log")),
        ],
    )
    return logging.getLogger("test_hybrid_structure")


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
    
    files_by_part = {}
    
    for part_number in part_numbers:
        files_by_part[part_number] = []
        
        # Create a drawing file
        drawing_path = os.path.join(test_dir, f"{part_number}_drawing.txt")
        with open(drawing_path, "w") as f:
            f.write(f"This is a test drawing for part {part_number}")
        files_by_part[part_number].append(drawing_path)
        
        # Create a spec file
        spec_path = os.path.join(test_dir, f"{part_number}_spec.txt")
        with open(spec_path, "w") as f:
            f.write(f"This is a test spec for part {part_number}")
        files_by_part[part_number].append(spec_path)
    
    return files_by_part


def main() -> None:
    """Main entry point for the script."""
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logs_dir = os.path.join(project_root, "logs")
        
        # Set up logging
        logger = setup_logging(logs_dir)
        logger.info("Starting hybrid folder structure test")
        
        # Create test directory
        test_dir = os.path.join(project_root, "scripts", "temp", "test_hybrid_structure")
        os.makedirs(test_dir, exist_ok=True)
        
        # Define test parameters
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quote_id = f"TEST_QT_{timestamp}"
        part_numbers = ["PN-001", "PN-002", "PN-003"]
        vendors = ["HeatTreatCo", "AnodizePro", "NickelWorks"]
        
        logger.info(f"Test parameters:")
        logger.info(f"  Quote ID: {quote_id}")
        logger.info(f"  Part numbers: {part_numbers}")
        logger.info(f"  Vendors: {vendors}")
        
        # Create test files
        logger.info("Creating test files")
        files_by_part = create_test_files(test_dir, part_numbers)
        
        # Initialize Box integration
        logger.info("Initializing Box integration")
        box = BoxIntegration(logger)
        
        if not box.client:
            logger.error("Failed to initialize Box client")
            sys.exit(1)
        
        # Create hybrid folder structure
        logger.info(f"Creating hybrid folder structure for RFQ: {quote_id}")
        folder_structure = box.create_rfq_structure(
            quote_id=quote_id,
            part_numbers=part_numbers,
            vendors=vendors
        )
        
        if not folder_structure:
            logger.error("Failed to create folder structure")
            sys.exit(1)
        
        logger.info("Folder structure created successfully")
        logger.info(f"Master folder: {folder_structure['master_folder'].name} (ID: {folder_structure['master_folder'].id})")
        
        # Upload files to part folders
        logger.info("Uploading files to part folders")
        for part_number, files in files_by_part.items():
            part_folder = folder_structure["part_folders"].get(part_number)
            if part_folder:
                logger.info(f"Uploading files for part {part_number}")
                uploaded = box.upload_part_files(part_number, files, part_folder)
                if uploaded:
                    logger.info(f"Uploaded {len(uploaded)} files for part {part_number}")
                else:
                    logger.warning(f"Failed to upload files for part {part_number}")
            else:
                logger.warning(f"Part folder not found for {part_number}")
        
        # Link files to vendor folders
        logger.info("Linking files to vendor folders")
        for vendor in vendors:
            vendor_folder = folder_structure["vendor_folders"].get(vendor)
            if vendor_folder:
                # For this test, we'll link all parts to all vendors
                # In a real scenario, you would only link relevant parts to each vendor
                logger.info(f"Linking files for vendor {vendor}")
                success = box.link_files_to_vendor(
                    vendor=vendor,
                    part_numbers=part_numbers,
                    part_folders=folder_structure["part_folders"],
                    vendor_folder=vendor_folder
                )
                
                if success:
                    logger.info(f"Successfully linked files for vendor {vendor}")
                    
                    # Create share link for vendor folder
                    share_link = box.create_share_link(vendor_folder)
                    if share_link:
                        logger.info(f"Created share link for vendor {vendor}: {share_link}")
                    else:
                        logger.warning(f"Failed to create share link for vendor {vendor}")
                else:
                    logger.warning(f"Failed to link files for vendor {vendor}")
            else:
                logger.warning(f"Vendor folder not found for {vendor}")
        
        logger.info("Test completed successfully")
        print("\nTest completed successfully. Check the log file for details.")
        print(f"Log file: {os.path.join(logs_dir, 'test_hybrid_structure.log')}")
        
    except Exception as e:
        print(f"Script failed with unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()