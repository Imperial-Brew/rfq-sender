"""
Test script to verify that the vendor_options.yaml file can be loaded correctly.
"""

import os
import yaml
import sys
from pathlib import Path

# Add parent directory to path (adjusted for new location in tests/vendor/)
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import from project modules
from core.config import Paths, init_config

def test_load_vendor_options():
    """Test loading the vendor_options.yaml file."""
    # Initialize configuration
    init_config()
    
    # Get the path to the vendor_options.yaml file
    vendor_options_file = Paths.VENDOR_OPTIONS_FILE
    
    print(f"Vendor options file path: {vendor_options_file}")
    
    # Check if the file exists
    if not os.path.exists(vendor_options_file):
        print(f"Error: Vendor options file not found: {vendor_options_file}")
        return False
    
    # Try to load the file
    try:
        with open(vendor_options_file, 'r', encoding='utf-8') as f:
            vendor_options = yaml.safe_load(f)
        
        # Check if the file has the expected structure
        if not vendor_options or 'vendors' not in vendor_options:
            print("Error: Vendor options file does not have the expected structure")
            return False
        
        # Print some information about the loaded data
        vendor_count = len(vendor_options['vendors'])
        print(f"Successfully loaded vendor options file with {vendor_count} vendors")
        
        # Print the first few vendors
        for i, vendor in enumerate(vendor_options['vendors'][:3], 1):
            print(f"Vendor {i}: {vendor['name']}")
        
        return True
    
    except Exception as e:
        print(f"Error loading vendor options file: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_load_vendor_options()
    if success:
        print("Test passed: Vendor options file loaded successfully")
    else:
        print("Test failed: Could not load vendor options file")
        sys.exit(1)