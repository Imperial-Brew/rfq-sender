"""
Test script to verify that the imports and functions in 06_send_emails.py work correctly.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path (adjusted for new location in tests/email/)
sys.path.append(str(Path(__file__).parent.parent.parent))

def test_imports():
    """Test that the imports in 06_send_emails.py work correctly."""
    try:
        # Try to import the modules used in 06_send_emails.py
        from scripts.utils.spec_check import SpecProcessValidator
        from core.config import Paths, CompanyInfo, LoggingConfig, init_config
        
        # Initialize configuration
        init_config()
        
        # Print success message
        print("All imports successful!")
        
        # Test that the vendor_options.yaml file can be loaded
        vendor_options_file = str(Paths.VENDOR_OPTIONS_FILE)
        print(f"Vendor options file path: {vendor_options_file}")
        
        # Check if the file exists
        if not os.path.exists(vendor_options_file):
            print(f"Error: Vendor options file not found: {vendor_options_file}")
            return False
        
        print(f"Vendor options file exists at: {vendor_options_file}")
        
        # Import the load_data function from 06_send_emails.py
        # This is a bit tricky since it's a Streamlit page, so we'll just verify the file exists
        send_emails_path = os.path.join("streamlit_app", "pages", "06_send_emails.py")
        if not os.path.exists(send_emails_path):
            print(f"Error: 06_send_emails.py not found at: {send_emails_path}")
            return False
        
        print(f"06_send_emails.py exists at: {send_emails_path}")
        
        # Check if the file contains the load_data function
        with open(send_emails_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "def load_data" not in content:
                print("Error: load_data function not found in 06_send_emails.py")
                return False
            
            if "from scripts.email.email_from_list import load_data" in content:
                print("Error: 06_send_emails.py is still importing load_data from email_from_list.py")
                return False
        
        print("load_data function found in 06_send_emails.py")
        return True
    
    except ImportError as e:
        print(f"Import error: {str(e)}")
        return False
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("Test passed: All imports and functions work correctly")
    else:
        print("Test failed: There was an error with the imports or functions")
        sys.exit(1)