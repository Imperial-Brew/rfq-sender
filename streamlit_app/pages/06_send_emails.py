import streamlit as st
import pandas as pd
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import yaml
import jinja2
from datetime import datetime

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import from project modules
from core.config import Paths, CompanyInfo, LoggingConfig, init_config
from streamlit_app.utils.auth_shim import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication
from scripts.utils.spec_check import SpecProcessValidator

if not require_authentication():
    st.stop()
    
# Initialize configuration
init_config()

# Set up logging
logger = LoggingConfig.setup_logging(__name__, "send_rfq_emails.log")

def load_data(queue_file: str, contacts_file: str, vendor_options_file: str, 
              logger: logging.Logger = None) -> Tuple[pd.DataFrame, Dict[Any, Dict[str, Any]]]:
    """
    Load data from CSV and YAML files and prepare vendor information.

    Args:
        queue_file: Path to the queue CSV file (Queue.csv)
        contacts_file: Path to the contacts CSV file (contacts.csv)
        vendor_options_file: Path to the vendor options YAML file (vendor_options.yaml)
        logger: Optional logger for logging messages

    Returns:
        Tuple containing:
            - DataFrame with queue data (with renamed columns)
            - Dictionary mapping vendor_id to vendor information (email and name)
    """
    if logger:
        logger.info(f"Loading queue data from {queue_file}")
    else:
        print(f"Loading queue data from {queue_file}")

    if not os.path.exists(queue_file):
        if logger:
            logger.error(f"Queue file not found: {queue_file}")
        else:
            print(f"Queue file not found: {queue_file}")
        raise FileNotFoundError(f"Queue file not found: {queue_file}")

    if logger:
        logger.info(f"Loading contacts data from {contacts_file}")
    else:
        print(f"Loading contacts data from {contacts_file}")

    if not os.path.exists(contacts_file):
        if logger:
            logger.error(f"Contacts file not found: {contacts_file}")
        else:
            print(f"Contacts file not found: {contacts_file}")
        raise FileNotFoundError(f"Contacts file not found: {contacts_file}")

    if logger:
        logger.info(f"Loading vendor options from {vendor_options_file}")
    else:
        print(f"Loading vendor options from {vendor_options_file}")

    if not os.path.exists(vendor_options_file):
        if logger:
            logger.error(f"Vendor options file not found: {vendor_options_file}")
        else:
            print(f"Vendor options file not found: {vendor_options_file}")
        raise FileNotFoundError(f"Vendor options file not found: {vendor_options_file}")

    try:
        # Load queue data with UTF-8 encoding and error handling
        try:
            queue = pd.read_csv(queue_file, encoding='utf-8')
        except UnicodeDecodeError:
            # Fall back to cp1252 if UTF-8 fails
            queue = pd.read_csv(queue_file, encoding='cp1252')

        # Log the number of items where SENT=YES, but don't filter them out
        if 'SENT' in queue.columns:
            sent_items_count = len(queue[queue['SENT'] == 'YES'])
            if logger:
                logger.info(f"Found {sent_items_count} items where SENT=YES. Total items: {len(queue)}")
            else:
                print(f"Found {sent_items_count} items where SENT=YES. Total items: {len(queue)}")

        # Load contacts data with UTF-8 encoding and error handling
        try:
            contacts = pd.read_csv(contacts_file, encoding='utf-8')
        except UnicodeDecodeError:
            # Fall back to cp1252 if UTF-8 fails
            contacts = pd.read_csv(contacts_file, encoding='cp1252')

        # Load vendor options data
        with open(vendor_options_file, 'r', encoding='utf-8') as f:
            vendor_options = yaml.safe_load(f)

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

        # Process contacts data
        # Filter to primary contacts only
        # The 'Primary' value is in the 9th column which might be unnamed in the CSV
        # Find the column that contains 'Primary' values
        primary_column = None
        for col in contacts.columns:
            if 'Primary' in contacts[col].values:
                primary_column = col
                break

        # Filter to primary contacts in the finishing category
        if primary_column:
            primary_contacts = contacts[(contacts['type'] == 'finishing') & (contacts[primary_column] == 'Primary')]
        else:
            # Fallback to just filtering by type if we can't find the primary column
            primary_contacts = contacts[contacts['type'] == 'finishing']

        # Create vendor info dictionary
        vendor_info = {}
        for _, row in primary_contacts.iterrows():
            vendor_id = row['Vendor'].strip()
            email = row['Email'].strip() if pd.notna(row['Email']) else ""

            # Skip entries without email
            if not email:
                continue

            # Get the first name if available
            first_name = row['First'].strip() if pd.notna(row['First']) else ""

            vendor_info[vendor_id] = {
                'email': email,
                'vendor_name': vendor_id,  # Use vendor name as is
                'first_name': first_name  # Add first name for personalized greeting
            }

        # Enrich vendor info with capabilities from vendor_options
        if vendor_options and 'vendors' in vendor_options:
            for vendor in vendor_options['vendors']:
                vendor_name = vendor['name']
                if vendor_name in vendor_info:
                    # Add capabilities information
                    if 'processes' in vendor:
                        # Store the full process objects, ensuring it's not None
                        vendor_info[vendor_name]['processes'] = vendor['processes'] if vendor['processes'] is not None else []

    except Exception as e:
        if logger:
            logger.error(f"Error loading files: {str(e)}")
        else:
            print(f"Error loading files: {str(e)}")
        raise

    return queue, vendor_info

def setup_page():
    st.title("Send RFQ Emails")
    st.markdown("""
    This page allows you to create RFQ email drafts in Outlook for vendors based on parts in the queue.
    Vendors are automatically matched based on their process capabilities.
    
    > **Note:** This tool creates draft emails in your Outlook client. No emails are sent automatically.
    > You will need to review and manually send each draft from Outlook.
    """)

def display_queue_for_emails(user, role):
    # Load queue data using centralized path configuration
    queue_file = str(Paths.QUEUE_PATH)
    contacts_file = str(parent_dir / "docs" / "OS" / "contacts.csv")
    # Use the centralized path configuration for vendor_options.yaml
    # This ensures consistent path handling across the application
    vendor_options_file = str(Paths.VENDOR_OPTIONS_FILE)
    
    try:
        # Use local load_data function
        queue, vendor_info = load_data(queue_file, contacts_file, vendor_options_file, logger)
        
        # Display queue with selection options
        # [Rest of the queue display code]
        
        # Process selected parts button
        if st.button("Create Draft Emails for Selected Parts"):
            # Use process_queue function adapted from email_from_list.py
            # [Email creation code]
            pass
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        logger.error(f"Error: {str(e)}")

def main():
    """Main function to run the page."""
    setup_page()
    
    # Get user from session state (set in main app)
    if "user" not in st.session_state:
        st.warning("Please select a user in the sidebar of the main page.")
        return
    
    user = st.session_state.user
    role = get_user_role(user)
    
    # Display user info
    st.sidebar.markdown(f"**User:** {user['name']}")
    st.sidebar.markdown(f"**Role:** {role}")
    
    # Display queue for sending emails
    display_queue_for_emails(user, role)

if __name__ == "__main__":
    main()