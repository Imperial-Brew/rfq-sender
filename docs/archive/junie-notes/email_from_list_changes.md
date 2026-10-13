# Changes to email_from_list.py

## Overview
This document describes the changes made to the `email_from_list.py` script to accommodate the updated structure of the `queue.csv` file.

## Changes Made

### 1. Updated Queue Column Mapping
The column mapping dictionary was updated to match the actual columns in the `queue.csv` file:

```python
queue_column_mapping = {
    'RFQ #': 'RFQ #',
    'Part_Number': 'part_number',
    'Rev': 'Rev',
    'Print Callout': 'callout',
    'process': 'process',
    'spec': 'spec',
    'material': 'material',
    'quantities': 'quantities',
    'file_location': 'file_location',
    'submitted_by': 'submitted_by',
    'qt/so #': 'qt/so #'
}
```

### 2. Added Quote ID Generation
Since the `queue.csv` file doesn't have a `quote_id` column but the script relies on it, we added code to create this column from the `part_number`:

```python
# Add part_number as quote_id since it doesn't exist in the queue.csv
queue['quote_id'] = queue['part_number']
```

### 3. Updated Required Columns
The required columns list was updated to match the actual column names:

```python
required_queue_columns = ['part_number', 'process', 'file_location']
```

### 4. Fixed File Path References
Updated references from `file_path` to `file_location` in the code:

1. In the attachment handling code:
```python
if hasattr(r, 'file_location') and pd.notna(r.file_location):
    # Handle file paths from the CSV
    file_path = r.file_location.strip()
```

2. In the Vendor_Quotes.csv handling code:
```python
if hasattr(item, 'file_location') and pd.notna(item.file_location):
    row_data['file location'] = item.file_location
```

## Testing
The changes were tested using a simplified test script that verifies:
1. The queue.csv file can be loaded correctly
2. The column mapping works as expected
3. All required columns are present after renaming
4. The quote_id column is properly created from part_number

The test confirmed that all these aspects are working correctly.

## Next Steps
The script should now be able to process the updated `queue.csv` file format. If any issues are encountered, additional adjustments may be needed to handle specific edge cases or data formats.