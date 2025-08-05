import pandas as pd
import os
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the parent directory to the path
parent_dir = Path(__file__).parent
sys.path.append(str(parent_dir))

# Import the queue loading function
from utils.queue import load_queue, QUEUE_PATH

def test_view_queue():
    """Test loading the queue data and processing it similar to the view_queue page."""
    try:
        logger.info(f"Testing queue loading from {QUEUE_PATH}")
        
        # Check if the file exists
        if not os.path.exists(QUEUE_PATH):
            logger.error(f"Queue file not found at {QUEUE_PATH}")
            return False
        
        # Load the queue data
        df = load_queue(QUEUE_PATH)
        
        if df.empty:
            logger.warning("Queue dataframe is empty")
            return True  # Not an error, just empty
        
        logger.info(f"Queue data loaded: {len(df)} rows")
        logger.info(f"Columns: {df.columns.tolist()}")
        
        # Test the date processing logic
        if "due_date" in df.columns:
            try:
                # Convert to datetime with error handling
                df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")
                logger.info("Successfully converted due_date column to datetime")
            except Exception as e:
                logger.error(f"Error converting due_date column: {str(e)}")
                return False
        
        # Test the safe date comparison function
        from datetime import datetime
        
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
                    
                today = datetime.now().date()
                return "Overdue" if date_val < today else "Active"
            except Exception as e:
                logger.error(f"Error comparing date value {x} of type {type(x)}: {str(e)}")
                return "No Date"
        
        # Test the function on various data types
        test_values = [
            pd.NaT,
            None,
            "2023-01-01",
            datetime.now(),
            pd.Timestamp("2023-01-01"),
            123,
            "not a date"
        ]
        
        logger.info("Testing safe_date_compare function with various inputs:")
        for val in test_values:
            result = safe_date_compare(val)
            logger.info(f"  Input: {val} (type: {type(val)}) -> Result: {result}")
        
        # If we have a due_date column, test it with our function
        if "due_date" in df.columns:
            logger.info("Testing safe_date_compare on actual due_date column:")
            df["status"] = df["due_date"].apply(safe_date_compare)
            logger.info("Successfully applied safe_date_compare to due_date column")
        
        # Test other columns that might be involved in comparisons
        if "sent" in df.columns:
            logger.info("Examining 'sent' column values:")
            unique_values = df["sent"].unique()
            logger.info(f"Unique values in 'sent' column: {unique_values}")
            
            # Check for mixed types
            types = df["sent"].apply(type).unique()
            logger.info(f"Data types in 'sent' column: {types}")
            
            # If there are mixed types, try to standardize them
            if len(types) > 1:
                logger.info("Mixed types detected in 'sent' column, standardizing...")
                # Convert to string
                df["sent"] = df["sent"].astype(str)
                # Replace 'nan' with empty string
                df["sent"] = df["sent"].replace("nan", "")
                
                # Check again
                types = df["sent"].apply(type).unique()
                logger.info(f"Data types after standardization: {types}")
        
        logger.info("Test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in test_view_queue: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_view_queue()
    if success:
        print("Test completed successfully!")
    else:
        print("Test failed. Check the logs for details.")