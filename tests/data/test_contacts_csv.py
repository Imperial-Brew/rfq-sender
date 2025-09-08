"""
Test script to verify that contacts are loaded correctly from CSV.
"""
import os
import sys
from pathlib import Path
import logging

# Add the parent directory to the path so we can import from other modules
# Updated for new location in tests/data/
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the VendorManager class
from core.vendors.vendor_manager import VendorManager
from core.vendors.models import Vendor

def test_load_contacts():
    """Test loading contacts from CSV file."""
    # Define file paths
    vendor_file = os.path.join(parent_dir, "config", "vendors.json")
    contacts_file = os.path.join(parent_dir, "docs", "OS", "contacts.csv")
    
    # Create VendorManager instance
    vendor_manager = VendorManager(
        vendor_file=vendor_file,
        contacts_file=contacts_file
    )
    
    # Log the number of vendors and contacts
    logger.info(f"Loaded {len(vendor_manager.vendors)} vendors from JSON")
    logger.info(f"Loaded {len(vendor_manager.contacts)} vendors with contacts from CSV")
    
    # Print all vendor names from CSV for debugging
    logger.info("Vendor names in CSV:")
    for vendor_name in sorted(vendor_manager.contacts.keys()):
        logger.info(f"  - {vendor_name}")
    
    # Test getting contacts for a few vendors
    test_vendors = [
        "Tech Metals",
        "Gleco Plating",
        "Embee Processing",
        "Nxedge Inc.",
        "Turn-key Coatings, Inc."
    ]
    
    for vendor_name in test_vendors:
        # Find the vendor in the vendors list
        vendor = next((v for v in vendor_manager.vendors if v.name == vendor_name), None)
        
        if not vendor:
            logger.warning(f"Vendor not found in JSON: {vendor_name}")
            continue
        
        # Get the primary contact
        contact = vendor_manager.get_primary_contact(vendor)
        
        if contact:
            logger.info(f"Found contact for {vendor_name}: {contact.name} ({contact.email})")
            # Check if contact came from CSV or JSON
            contact_source = "JSON"
            
            # Check exact match
            if vendor_name in vendor_manager.contacts:
                csv_contacts = vendor_manager.contacts[vendor_name]
                csv_emails = [c.email for c in csv_contacts]
                if contact.email in csv_emails:
                    contact_source = "CSV (exact match)"
            
            # Check case-insensitive match
            else:
                vendor_name_lower = vendor_name.lower()
                for csv_vendor_name, csv_contacts in vendor_manager.contacts.items():
                    if csv_vendor_name.lower() == vendor_name_lower:
                        csv_emails = [c.email for c in csv_contacts]
                        if contact.email in csv_emails:
                            contact_source = f"CSV (case-insensitive: {csv_vendor_name})"
            
            # Check special case for Turn-key/TURNKEY
            if "Turn-key" in vendor_name or "TURNKEY" in vendor_name:
                for csv_vendor_name, csv_contacts in vendor_manager.contacts.items():
                    if ("Turn" in csv_vendor_name or "TURN" in csv_vendor_name) and "key" in csv_vendor_name.lower():
                        csv_emails = [c.email for c in csv_contacts]
                        if contact.email in csv_emails:
                            contact_source = f"CSV (special match: {csv_vendor_name})"
            
            logger.info(f"  Contact source: {contact_source}")
        else:
            logger.warning(f"No contact found for {vendor_name}")

def test_turnkey_matching():
    """Test specifically the matching between 'Turn-key Coatings, Inc.' and 'TURNKEY Coatings'."""
    logger.info("Testing Turn-key Coatings matching...")
    
    # Define file paths
    vendor_file = os.path.join(parent_dir, "config", "vendors.json")
    contacts_file = os.path.join(parent_dir, "docs", "OS", "contacts.csv")
    
    # Create VendorManager instance
    vendor_manager = VendorManager(
        vendor_file=vendor_file,
        contacts_file=contacts_file
    )
    
    # Create a test vendor with the name "Turn-key Coatings, Inc."
    test_vendor = Vendor(name="Turn-key Coatings, Inc.")
    
    # Get the primary contact
    contact = vendor_manager.get_primary_contact(test_vendor)
    
    if contact:
        logger.info(f"Found contact for Turn-key Coatings, Inc.: {contact.name} ({contact.email})")
        # Check if contact came from CSV
        if "TURNKEY Coatings" in vendor_manager.contacts:
            csv_contacts = vendor_manager.contacts["TURNKEY Coatings"]
            csv_emails = [c.email for c in csv_contacts]
            if contact.email in csv_emails:
                logger.info(f"  Contact source: CSV (TURNKEY Coatings)")
            else:
                logger.info(f"  Contact source: JSON")
        else:
            logger.info(f"  Contact source: JSON")
    else:
        logger.warning("No contact found for Turn-key Coatings, Inc.")
    
    # Now try with the CSV name directly
    logger.info("Testing with CSV name directly...")
    if "TURNKEY Coatings" in vendor_manager.contacts:
        csv_contacts = vendor_manager.contacts["TURNKEY Coatings"]
        if csv_contacts:
            contact = csv_contacts[0]
            logger.info(f"Found contact for TURNKEY Coatings: {contact.name} ({contact.email})")
        else:
            logger.warning("No contacts found for TURNKEY Coatings in CSV")
    else:
        logger.warning("TURNKEY Coatings not found in CSV contacts")

if __name__ == "__main__":
    logger.info("Starting contacts CSV test")
    test_load_contacts()
    test_turnkey_matching()
    logger.info("Test completed")