import pandas as pd
import os
from pathlib import Path

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent
QUEUE_PATH = os.path.join(ROOT_DIR, "docs", "queue.csv")

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

def add_to_queue(path, entry: dict):
    df = load_queue(path)
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(path, index=False)
