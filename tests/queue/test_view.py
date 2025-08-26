import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import sys
from pathlib import Path

# Add the parent directory to the path (adjusted for new location in tests/queue/)
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import the logging module
from utils.rfq_logging import get_logger

# Get module-specific logger
logger = get_logger(__name__)

def test_safe_date_compare():
    """Test the safe date comparison function with various inputs."""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    # Define the safe date comparison function (copied from 02_view_queue.py)
    def safe_date_compare(x):
        try:
            # Handle NaN, NaT, None, or any non-datetime value
            if pd.isna(x) or x is pd.NaT or x is None:
                return "No Date"
            
            # Ensure x is a datetime object
            if not isinstance(x, (pd.Timestamp, datetime)):
                # If it's a string or other type, return "No Date"
                return "No Date"
            
            date_val = x.date() if hasattr(x, 'date') else None
            if date_val is None:
                return "No Date"
                
            return "Overdue" if date_val < today else "Active"
        except Exception as e:
            logger.debug(f"Error comparing date value {x} of type {type(x)}: {str(e)}")
            return "No Date"
    
    # Test cases
    test_cases = [
        # Valid dates
        (pd.Timestamp(yesterday), "Overdue"),
        (pd.Timestamp(tomorrow), "Active"),
        (pd.Timestamp(today), "Active"),
        
        # Invalid/missing dates
        (pd.NaT, "No Date"),
        (None, "No Date"),
        (np.nan, "No Date"),
        
        # String dates (should be converted before calling this function)
        ("2023-01-01", "No Date"),  # String dates should be handled separately
        
        # Mixed types that might cause comparison errors
        (123, "No Date"),
        (123.45, "No Date"),
        ("invalid", "No Date"),
    ]
    
    # Run tests
    passed = 0
    failed = 0
    
    for value, expected in test_cases:
        try:
            result = safe_date_compare(value)
            if result == expected:
                logger.info(f"PASS: {value} -> {result}")
                passed += 1
            else:
                logger.error(f"FAIL: {value} -> {result}, expected {expected}")
                failed += 1
        except Exception as e:
            logger.error(f"ERROR: {value} raised exception: {str(e)}")
            failed += 1
    
    logger.info(f"Test results: {passed} passed, {failed} failed")
    return passed, failed

def test_dataframe_processing():
    """Test the dataframe processing with various date formats."""
    # Create a test dataframe with various date formats
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    df = pd.DataFrame({
        "part_number": ["P001", "P002", "P003", "P004", "P005", "P006", "P007"],
        "due_date": [
            yesterday,                # Timestamp - past
            tomorrow,                 # Timestamp - future
            pd.NaT,                   # NaT
            None,                     # None
            "2023-01-01",             # String date
            "invalid",                # Invalid string
            123                       # Number
        ]
    })
    
    try:
        # Convert dates with error handling
        df["due_date_converted"] = pd.to_datetime(df["due_date"], errors="coerce")
        
        # Define safe date comparison function
        def safe_date_compare(x):
            try:
                # Handle NaN, NaT, None, or any non-datetime value
                if pd.isna(x) or x is pd.NaT or x is None:
                    return "No Date"
                
                # Ensure x is a datetime object
                if not isinstance(x, (pd.Timestamp, datetime)):
                    # If it's a string or other type, return "No Date"
                    return "No Date"
                
                date_val = x.date() if hasattr(x, 'date') else None
                if date_val is None:
                    return "No Date"
                    
                # Ensure both values are of the same type before comparison
                if not isinstance(date_val, type(today)):
                    # Convert date_val to the same type as today if possible
                    try:
                        date_val = type(today)(date_val)
                    except:
                        return "No Date"
                
                return "Overdue" if date_val < today else "Active"
            except Exception as e:
                logger.debug(f"Error comparing date value {x} of type {type(x)}: {str(e)}")
                return "No Date"
        
        # Apply the function
        df["status"] = df["due_date_converted"].apply(safe_date_compare)
        
        # Check results
        # Note: pd.to_datetime with errors='coerce' will convert valid date strings and timestamps
        # "2023-01-01" is a valid date string and will be converted to a date in the past (Overdue)
        # 123 is interpreted as milliseconds since epoch (1970-01-01) which is also in the past (Overdue)
        expected_statuses = ["Overdue", "Active", "No Date", "No Date", "Overdue", "No Date", "Overdue"]
        all_correct = True
        
        for i, (actual, expected) in enumerate(zip(df["status"], expected_statuses)):
            if actual != expected:
                logger.error(f"Row {i}: Expected '{expected}', got '{actual}'")
                all_correct = False
            else:
                logger.info(f"Row {i}: Correct status '{actual}'")
        
        if all_correct:
            logger.info("All statuses calculated correctly!")
        else:
            logger.error("Some statuses were incorrect")
        
        # Print the dataframe for inspection
        logger.info("\nTest DataFrame:")
        logger.info(df[["part_number", "due_date", "due_date_converted", "status"]].to_string())
        
        return all_correct
    
    except Exception as e:
        logger.error(f"Error in dataframe processing: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Testing safe date comparison function...")
    passed, failed = test_safe_date_compare()
    
    logger.info("\nTesting dataframe processing...")
    df_test_passed = test_dataframe_processing()
    
    if failed == 0 and df_test_passed:
        logger.info("\nAll tests PASSED!")
    else:
        logger.error("\nSome tests FAILED!")