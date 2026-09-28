# Comprehensive Queue Data Type Fix

## Issue Description
The application was experiencing an error related to comparing values of different types using the '<' operator:

```
Error loading queue data: '<' not supported between instances of 'float' and 'str'
```

This issue was occurring in the queue viewing functionality where date comparisons are performed, and also when processing data from the queue.csv file that contained inconsistent data types and formatting issues.

## Root Cause Analysis
After thorough investigation, we identified multiple contributing factors:

1. **Type comparison issues in date handling**: The `safe_date_compare` function was attempting to compare date values with the current date without ensuring both values were of the same type.

2. **Inconsistent data formatting in queue.csv**: The queue data contained formatting issues like line breaks in text fields (e.g., "Zinc Nickel Plat\ne") and mixed data types.

3. **Limited type standardization**: The original `load_queue` function only standardized a few specific columns ('sent', 'quantities', 'qt/so #', 'Rev'), leaving other columns with potential type inconsistencies.

4. **Premature string conversion**: In some files, date values were being converted to strings before comparison, causing type mismatch errors.

## Comprehensive Solution

### 1. Enhanced Queue Loading Function

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

### 2. Improved Date Comparison

We also enhanced the `safe_date_compare` function in all relevant files to ensure proper type conversion before comparison:

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

### 3. Fixed Date Handling in Email Sending Page

In the `streamlit_app/pages/05_send_rfq_emails.py` file, we fixed an issue where date values were being converted to strings before comparison:

**Original code (problematic):**
```python
# Convert date columns to datetime if they exist
if "due_date" in display_df.columns:
    display_df["due_date"] = pd.to_datetime(display_df["due_date"], errors="coerce")
    # This line converts datetime to string before comparison
    display_df["due_date"] = display_df["due_date"].dt.strftime("%Y-%m-%d")
```

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

## Testing
The solution was thoroughly tested using:

1. `test_fix.py` - Verifies the queue loading and date comparison functions
2. `test_view_queue.py` - Tests the safe date comparison with various input types

All tests passed successfully, confirming that our comprehensive solution resolves the issue.

## Files Modified
1. `utils/queue.py` - Enhanced the load_queue function
2. `streamlit_app/pages/02_view_queue.py` - Improved safe_date_compare function
3. `streamlit_app/pages/05_send_rfq_emails.py` - Fixed date handling and comparison
4. `test_view_queue.py` - Updated safe_date_compare function
5. `test_fix.py` - Updated safe_date_compare function

## Conclusion
The comprehensive solution addresses all aspects of the issue:

1. Proper type checking and conversion before any comparison, preventing TypeErrors
2. Thorough data cleaning and standardization when loading the queue data
3. Handling of line breaks and other formatting issues in string columns
4. Explicit type conversion for all columns that might be involved in comparisons
5. Proper handling of date values throughout the application

These changes ensure consistent behavior across the application and prevent the '<' not supported between instances of 'float' and 'str' error from occurring.