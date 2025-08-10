import streamlit as st
import pandas as pd
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any
import yaml
import jinja2
from datetime import datetime

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import from project modules
from core.config import Paths, ExchangeConfig, CompanyInfo, LoggingConfig, init_config
from utils.auth import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication
from spec_check import SpecProcessValidator

if not require_authentication():
    st.stop()
    
# Initialize configuration
init_config()

# Set up logging
logger = LoggingConfig.setup_logging(__name__, "send_rfq_emails.log")

def setup_page():
    st.title("Send RFQ Emails")
    st.markdown("""
    This page allows you to create RFQ email drafts in Outlook for vendors based on parts in the queue.
    Vendors are automatically matched based on their process capabilities.
    
    > **Note:** This tool creates draft emails in your Outlook client. No emails are sent automatically.
    > You will need to review and manually send each draft from Outlook.
    """)

def display_queue_for_emails(user, role):
    # Load queue data
    queue_file = str(Paths.QUEUE_PATH)
    contacts_file = str(parent_dir / "docs" / "OS" / "contacts.csv")
    vendor_options_file = str(parent_dir / "config" / "vendor_options.yaml")
    
    try:
        # Use load_data function from email_from_list.py
        queue, vendor_info = load_data(queue_file, contacts_file, vendor_options_file, logger)
        
        # Display queue with selection options
        # [Rest of the queue display code]
        
        # Process selected parts button
        if st.button("Create Draft Emails for Selected Parts"):
            # Use process_queue function adapted from email_from_list.py
            # [Email creation code]
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        logger.error(f"Error: {str(e)}")

