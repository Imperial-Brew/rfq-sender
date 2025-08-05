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
    
    # Standardize data types for all columns that might cause comparison issues
    for col in df.columns:
        # For columns that should be strings but might have mixed types
        if col in ['sent', 'quantities', 'qt/so #', 'Rev']:
            df[col] = df[col].astype(str)
            df[col] = df[col].replace('nan', '')
        
        # For columns that should be numeric but might have strings
        # (Uncomment if needed)
        # elif col in ['numeric_column1', 'numeric_column2']:
        #     df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

def add_to_queue(path, entry: dict):
    df = load_queue(path)
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(path, index=False)
