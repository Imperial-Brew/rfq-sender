"""
Test script to verify data loading functionality.

This script tests loading the queue data to ensure column mapping works correctly.
"""

import pandas as pd
import os
import sys
from pathlib import Path

# Add the parent directory to the path (adjusted for new location in tests/data/)
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

def test_load_queue_data():
    """Test loading and mapping queue data columns."""
    try:
        # Load queue data
        queue_file = os.path.join(parent_dir, 'docs', 'queue.csv')
        print(f"Loading queue data from {queue_file}")
        
        if not os.path.exists(queue_file):
            print(f"Queue file not found: {queue_file}")
            return False
        
        # Load queue data with UTF-8 encoding and error handling
        try:
            queue = pd.read_csv(queue_file, encoding='utf-8')
        except UnicodeDecodeError:
            # Fall back to cp1252 if UTF-8 fails
            queue = pd.read_csv(queue_file, encoding='cp1252')
        
        print("Original queue columns:", queue.columns.tolist())
        
        # Rename queue columns to match expected names
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
        
        # Rename columns
        queue = queue.rename(columns=queue_column_mapping)
        
        # Add part_number as quote_id since it doesn't exist in the queue.csv
        queue['quote_id'] = queue['part_number']
        
        print("Renamed queue columns:", queue.columns.tolist())
        
        # Check if required columns exist
        required_queue_columns = ['part_number', 'process', 'file_location']
        missing_queue_columns = [col for col in required_queue_columns if col not in queue.columns]
        
        if missing_queue_columns:
            print(f"Queue file missing required columns: {', '.join(missing_queue_columns)}")
            return False
        else:
            print("All required columns are present!")
            
        # Print first few rows to verify data
        print("\nFirst few rows after renaming:")
        print(queue.head())
        
        return True
        
    except Exception as e:
        print('Error:', str(e))
        return False

if __name__ == "__main__":
    success = test_load_queue_data()
    if success:
        print("\nQueue data loading test passed!")
    else:
        print("\nQueue data loading test failed!")
        sys.exit(1)