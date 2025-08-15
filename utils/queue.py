import pandas as pd
import os
import logging
from pathlib import Path
from core.config import Paths, LoggingConfig, init_config

# Initialize configuration
init_config()

# Set up logging using the centralized configuration
logger = LoggingConfig.setup_logging(__name__, "queue.log")

# Use the centralized path from config
QUEUE_PATH = Paths.QUEUE_PATH

def load_queue(path=QUEUE_PATH):
    """
    Load the queue from a CSV file and standardize data types.
    
    Args:
        path: Path to the queue CSV file (defaults to QUEUE_PATH)
        
    Returns:
        DataFrame containing the queue data
    """
    logger.info(f"Loading queue from {path}")
    
    if not os.path.exists(path):
        logger.warning(f"Queue file not found at {path}, returning empty DataFrame")
        return pd.DataFrame()
    
    try:
        # Load the CSV file
        df = pd.read_csv(path)
        logger.info(f"Successfully loaded queue with {len(df)} entries")
        df.columns = [col.lower() for col in df.columns]

        # Standardize data types for all columns to prevent comparison issues
        for col in df.columns:
            # First, clean any line breaks or extra whitespace in all columns
            if df[col].dtype == 'object':  # Only process string/object columns
                # Replace line breaks and normalize whitespace
                df[col] = df[col].astype(str).str.replace('\n', ' ').str.strip()
            
            # For columns that should be strings
            if col in ['sent', 'quantities', 'qt/so #', 'rev', 'process', 'spec',
                       'material', 'part_number', 'print callout', 'file_location',
                       'submitted_by', 'rfq #']:
                df[col] = df[col].astype(str)
                df[col] = df[col].replace('nan', '')
            
            # For columns that might contain dates
            elif col in ['due_date']:
                # Convert to datetime with error handling
                df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # For columns that should be numeric
            elif col in ['rfq #']:
                # Try to convert to numeric, but keep as string if it fails
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    # Fill NaN values with empty string
                    df[col] = df[col].fillna('')
                except Exception as e:
                    logger.warning(f"Error converting {col} to numeric: {str(e)}")
                    # If conversion fails, ensure it's a clean string
                    df[col] = df[col].astype(str).replace('nan', '')
        
        logger.debug("Data types standardized for all columns")
        return df
    except Exception as e:
        logger.error(f"Error loading queue from {path}: {str(e)}")
        return pd.DataFrame()

def add_to_queue(path, entry: dict):
    """
    Add a new entry to the queue.
    
    Args:
        path: Path to the queue CSV file
        entry: Dictionary containing the entry data
        
    Returns:
        None
    """
    logger.info(f"Adding new entry to queue at {path}")
    try:
        # Normalize new fields: 'qt/so #' and 'cui_itar'
        qt_so = (entry.get('qt/so #') or '').strip()
        entry['qt/so #'] = qt_so
        # Normalize ITAR/CUI to string TRUE/FALSE
        cui_val = entry.get('cui_itar', '')
        if isinstance(cui_val, bool):
            entry['cui_itar'] = 'TRUE' if cui_val else 'FALSE'
        else:
            s = str(cui_val).strip().upper()
            entry['cui_itar'] = 'TRUE' if s in ('TRUE', 'YES', 'Y', '1') else ('FALSE' if s else '')
        
        # Load existing queue
        df = load_queue(path)
        
        # Add new entry
        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        
        # Save updated queue
        df.to_csv(path, index=False)
        
        logger.info(f"Successfully added entry to queue: {entry.get('part_number', 'Unknown part')} - {entry.get('process', 'Unknown process')}")
    except Exception as e:
        logger.error(f"Error adding entry to queue: {str(e)}")
        raise
