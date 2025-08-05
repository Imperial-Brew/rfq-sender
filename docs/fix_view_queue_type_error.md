# Fix for View Queue Type Error

## Issue Description

The view_queue page was experiencing an error when loading queue data:

```
Error loading queue data: '<' not supported between instances of 'float' and 'str'
```

This error occurred because of a type mismatch during comparison operations in the date handling code. Specifically, the error happened when trying to compare a float value (NaN) with a string value.

## Root Cause Analysis

After investigating the code in `streamlit_app/pages/02_view_queue.py`, we identified two main issues:

1. The `safe_date_compare` function wasn't properly handling non-datetime values, which could lead to type comparison errors.
2. The 'sent' column in the queue.csv file contained mixed data types (float NaN and string 'YES'), which could cause type comparison issues elsewhere in the code.

## Changes Made

### 1. Enhanced the `safe_date_compare` function

Updated the function to better handle various input types:

```python
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
```

The key improvements are:
- Added explicit check for `None` values
- Added type checking with `isinstance()` to ensure we only compare datetime objects
- Enhanced error logging to include the type of the value causing the error

### 2. Standardized the 'sent' column

Added code to standardize the 'sent' column to prevent type comparison issues:

```python
# Standardize the 'sent' column if it exists to prevent type comparison issues
if 'sent' in df.columns:
    # Convert to string
    df['sent'] = df['sent'].astype(str)
    # Replace 'nan' with empty string
    df['sent'] = df['sent'].replace('nan', '')
    logger.info("Standardized 'sent' column to string type")
```

This ensures that all values in the 'sent' column are of the same type (string), preventing any type comparison issues.

## Testing

A test script (`test_fix.py`) was created to verify the fix. The script:

1. Loads the queue data
2. Tests the `safe_date_compare` function with various input types
3. Examines the 'sent' column for mixed types
4. Standardizes the 'sent' column if mixed types are detected

The test confirmed that:
- The `safe_date_compare` function correctly handles various input types
- The 'sent' column in the queue.csv file contains mixed data types (float NaN and string 'YES')
- Standardizing the 'sent' column successfully converts all values to strings

## Conclusion

The error was resolved by:
1. Improving type checking in the `safe_date_compare` function
2. Standardizing the 'sent' column to ensure consistent data types

These changes make the code more robust against type mismatches and prevent the '<' not supported between instances of 'float' and 'str' error from occurring.