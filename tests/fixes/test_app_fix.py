"""
Test script to verify the app.py fixes.

This script checks the structure of app.py to ensure there's no duplicate code
that could cause the KeyError: 'streamlit_app' issue.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path (adjusted for new location in tests/fixes/)
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import the logging module
from utils.logging import get_logger

# Get module-specific logger
logger = get_logger(__name__)

def test_app_structure():
    """Test the structure of app.py to ensure there's no duplicate code."""
    try:
        # Path to app.py
        app_path = os.path.join(parent_dir, "streamlit_app", "app.py")
        logger.info(f"Testing app structure at {app_path}")
        
        if not os.path.exists(app_path):
            logger.error(f"App file not found at {app_path}")
            return False
        
        # Read the app.py file
        with open(app_path, 'r') as f:
            content = f.read()
        
        # Check for duplicate setup_page_config calls outside of try block
        main_function = content.split("def main()")[1].split("if __name__ ==")[0]
        
        # Count occurrences of setup_page_config in the main function
        setup_calls = main_function.count("setup_page_config()")
        
        if setup_calls > 1:
            logger.error(f"Found {setup_calls} calls to setup_page_config() in main function. Should be only 1.")
            return False
        else:
            logger.info("Correct number of setup_page_config() calls found.")
        
        # Check for duplicate st.title calls
        title_calls = main_function.count('st.title("📬 RFQ Sender System")')
        
        if title_calls > 1:
            logger.error(f"Found {title_calls} calls to st.title() in main function. Should be only 1.")
            return False
        else:
            logger.info("Correct number of st.title() calls found.")
        
        # Check for duplicate check_authentication calls
        auth_calls = main_function.count("check_authentication()")
        
        if auth_calls > 1:
            logger.error(f"Found {auth_calls} calls to check_authentication() in main function. Should be only 1.")
            return False
        else:
            logger.info("Correct number of check_authentication() calls found.")
        
        # Check for proper try-except structure
        if "try:" in main_function and "except KeyError as e:" in main_function:
            logger.info("Found proper try-except structure for KeyError handling.")
        else:
            logger.error("Missing proper try-except structure for KeyError handling.")
            return False
        
        logger.info("App structure test passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error in test_app_structure: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_app_structure()
    if success:
        print("App structure tests completed successfully!")
    else:
        print("App structure tests failed. Check the logs for details.")