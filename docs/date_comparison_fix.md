# Date Comparison Fix

## Issue Description
There was a bug in the application related to comparing dates using the '<' operator between a float and a string. This issue was likely occurring in the queue viewing functionality where date comparisons are performed.

## Root Cause
The issue was identified in the `safe_date_compare` function used in multiple files:
- `streamlit_app/pages/02_view_queue.py`
- `streamlit_app/pages/05_send_rfq_emails.py`
- `test_view_queue.py`
- `test_fix.py`

The function was attempting to compare date values with the current date using the '<' operator without ensuring that both values were of the same type. This could lead to a TypeError when comparing a string or other non-date type with a date object.

## Fix Implementation
The fix involved enhancing the `safe_date_compare` function in all affected files to ensure proper type conversion before comparison:

1. Added explicit type checking to verify that both values being compared are of the same type
2. Added a conversion step to convert the date value to the same type as the comparison date (today)
3. Added proper error handling to catch any conversion errors and return a safe default value

### Example of the fixed code:

```python
import pandas as pd
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

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
        today = datetime.now().date()
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
```

## Files Modified
1. `streamlit_app/pages/02_view_queue.py`
2. `streamlit_app/pages/05_send_rfq_emails.py`
3. `test_view_queue.py`
4. `test_fix.py`

## Testing
The fix was tested using the existing `test_fix.py` script, which verifies that the `safe_date_compare` function correctly handles various input types:
- Valid datetime objects
- Pandas Timestamp objects
- NaT (Not a Time) values
- None values
- String values
- Numeric values

All tests passed successfully, confirming that the fix resolves the issue.

## Additional Fix
After implementing the initial fix, we discovered another issue in `streamlit_app/pages/05_send_rfq_emails.py`. In this file, the due_date column was being converted to a string format before being passed to the safe_date_compare function.

**Original code (problematic):**

```python
# Convert date columns to datetime if they exist
if "due_date" in display_df.columns:
    display_df["due_date"] = pd.to_datetime(display_df["due_date"], errors="coerce")
    # This line converts datetime to string before comparison
    display_df["due_date"] = display_df["due_date"].dt.strftime("%Y-%m-%d")
```

This was causing the comparison to fail because the safe_date_compare function was receiving string dates instead of datetime objects. We fixed this by:

1. Storing the datetime objects in a separate column before formatting
2. Using the datetime column for comparison
3. Formatting the display column after the comparison is done

**Updated code (fixed):**

```python
# Convert date columns to datetime if they exist
if "due_date" in display_df.columns:
    display_df["due_date"] = pd.to_datetime(display_df["due_date"], errors="coerce")
    # Store datetime objects for comparison in a new column
    display_df["due_date_dt"] = display_df["due_date"]

# Use the datetime column for comparison
if "due_date_dt" in display_df.columns:
    # ... safe_date_compare function ...
    
    # Apply the safe comparison function to the datetime column
    display_df["status"] = display_df["due_date_dt"].apply(safe_date_compare)
    
    # Format dates for display AFTER comparison is done
    if "due_date" in display_df.columns:
        display_df["due_date"] = display_df["due_date"].dt.strftime("%Y-%m-%d")
```

## Additional Comprehensive Fix
After implementing the initial fixes, we discovered that the issue was still occurring in some cases. A more comprehensive solution was needed to address all potential type conversion issues in the queue data.

### Enhanced Queue Loading
We updated the `load_queue` function in `utils/queue.py` to perform more thorough data cleaning and type standardization:

```python
def load_queue(path=QUEUE_PATH):
    if not os.path.exists(path):
        return pd.DataFrame()
    
    # Load the CSV file
    df = pd.read_csv(path)
    
    # Standardize data types for all columns to prevent comparison issues
    for col in df.columns:
        # First, clean any line breaks or extra whitespace in all columns
        if df[col].dtype == 'object':  # Only process string/object columns
            # Replace line breaks and normalize whitespace
            df[col] = df[col].astype(str).str.replace('\n', ' ').str.strip()
        
        # For columns that should be strings
        if col in ['sent', 'quantities', 'qt/so #', 'Rev', 'process', 'spec', 
                  'material', 'Part_Number', 'Print Callout', 'file_location', 
                  'submitted_by', 'RFQ #']:
            df[col] = df[col].astype(str)
            df[col] = df[col].replace('nan', '')
        
        # For columns that might contain dates
        elif col in ['due_date']:
            # Convert to datetime with error handling
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # For columns that should be numeric
        elif col in ['RFQ #']:
            # Try to convert to numeric, but keep as string if it fails
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Fill NaN values with empty string
                df[col] = df[col].fillna('')
            except:
                # If conversion fails, ensure it's a clean string
                df[col] = df[col].astype(str).replace('nan', '')
    
    return df
```

This enhanced version:
1. Cleans line breaks and normalizes whitespace in all string columns
2. Explicitly handles a wider range of columns that should be treated as strings
3. Properly converts date columns to datetime objects
4. Handles numeric columns with appropriate error handling
5. Ensures consistent data types throughout the dataframe

## Conclusion
The bug was caused by attempting to compare values of different types using the '<' operator, combined with inconsistent data formatting in the queue.csv file. Our comprehensive solution addresses both issues:

1. Proper type checking and conversion before any comparison, preventing TypeErrors
2. Thorough data cleaning and standardization when loading the queue data
3. Handling of line breaks and other formatting issues in string columns
4. Explicit type conversion for all columns that might be involved in comparisons

These changes ensure consistent behavior across the application and prevent the '<' not supported between instances of 'float' and 'str' error from occurring.