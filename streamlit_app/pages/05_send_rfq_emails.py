import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import logging
import os
from datetime import datetime

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import configuration and utility functions
from core.config import Paths, ExchangeConfig, CompanyInfo, LoggingConfig, init_config
from utils.queue import load_queue
from utils.email import (
    load_vendors,
    find_vendors_for_process,
    get_primary_contact,
    create_rfq_email,
    send_email,
    process_queue_and_send_emails
)
from utils.auth import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication

if not require_authentication():
    st.stop()

# Initialize configuration
init_config()

# Set up logging using the centralized configuration
logger = LoggingConfig.setup_logging(__name__, "send_rfq_emails.log")

def setup_page():
    """Configure the page settings."""
    st.title("Send RFQ Emails")
    st.markdown("""
    This page allows you to create RFQ email drafts in Outlook for vendors based on parts in the queue.
    You can create drafts for individual parts or process the entire queue.
    
    > **Note:** This tool creates draft emails in your Outlook client. No emails are sent automatically.
    > You will need to review and manually send each draft from Outlook.
    """)

def display_queue_for_emails(user, role):
    """Display the queue with options to send emails."""
    try:
        # Load queue data
        df = load_queue(Paths.QUEUE_PATH)
        
        if df.empty:
            st.info("The queue is currently empty. Add parts using the 'Add to Queue' page.")
            return
        
        # Display the queue
        st.subheader("RFQ Queue")
        
        # Format the dataframe for display
        display_df = df.copy()
        
        # Convert date columns to datetime if they exist
        if "due_date" in display_df.columns:
            display_df["due_date"] = pd.to_datetime(display_df["due_date"], errors="coerce")
            # Store datetime objects for comparison
            display_df["due_date_dt"] = display_df["due_date"]
        
        # Add a status column based on due date if it exists
        if "due_date_dt" in display_df.columns:
            today = datetime.now().date()
            
            # Define a safe date comparison function
            def safe_date_compare(x):
                try:
                    # Handle NaN, NaT, None, or any non-datetime value
                    if pd.isna(x) or x is pd.NaT or x is None:
                        return "No Date"
                    
                    # Convert to datetime if it's a string
                    if isinstance(x, str):
                        try:
                            date_val = pd.to_datetime(x).date()
                        except:
                            return "No Date"
                    # Ensure x is a datetime object
                    elif not isinstance(x, (pd.Timestamp, datetime)):
                        return "No Date"
                    else:
                        date_val = x.date() if hasattr(x, 'date') else None
                    
                    if date_val is None:
                        return "No Date"
                        
                    # Ensure both values are of the same type before comparison
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
            
            # Apply the safe comparison function
            display_df["status"] = display_df["due_date_dt"].apply(safe_date_compare)
            
            # Format dates for display after comparison is done
            if "due_date" in display_df.columns:
                display_df["due_date"] = display_df["due_date"].dt.strftime("%Y-%m-%d")
        
        # Highlight expedited items
        if "expedited" in display_df.columns:
            display_df["priority"] = display_df["expedited"].apply(
                lambda x: "⚠️ Expedited" if x else "Standard"
            )
        
        # Reorder and select columns for display
        columns_to_display = ["part_number", "process", "spec", "quantities"]
        if "priority" in display_df.columns:
            columns_to_display.append("priority")
        if "due_date" in display_df.columns:
            columns_to_display.append("due_date")
        if "status" in display_df.columns:
            columns_to_display.append("status")
        
        # Only include columns that actually exist in the dataframe
        columns_to_display = [col for col in columns_to_display if col in display_df.columns]
        
        # Add a selection column
        display_df_with_selection = display_df.copy()
        
        # Display the dataframe with selection
        selected_indices = st.multiselect(
            "Select parts to send RFQ emails for:",
            options=list(range(len(display_df_with_selection))),
            format_func=lambda i: f"{display_df_with_selection.iloc[i]['part_number']} - {display_df_with_selection.iloc[i]['process']}"
        )
        
        if selected_indices:
            selected_parts = display_df_with_selection.iloc[selected_indices]
            st.write("Selected parts:")
            st.dataframe(
                selected_parts[columns_to_display],
                use_container_width=True,
                hide_index=True
            )
        
        # Process selected parts
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Create Draft Emails for Selected Parts", disabled=len(selected_indices) == 0):
                if role not in ["admin", "editor"]:
                    st.warning("You need admin or editor privileges to send emails.")
                    return
                
                try:
                    with st.spinner("Sending emails..."):
                        # Set up required parameters
                        vendor_file = str(parent_dir / "config" / "vendors.json")
                        template_path = str(parent_dir / "config" / "templates" / "email_signature.html")
                        
                        # Get email settings from ExchangeConfig
                        smtp_settings = {
                            "server": ExchangeConfig.get_server(),
                            "port": 587,
                            "username": ExchangeConfig.get_username(),
                            "password": ExchangeConfig.get_password(),
                            "use_tls": True,
                            "from_email": ExchangeConfig.get_from_email(),
                            "cc": ExchangeConfig.get_cc_email()
                        }
                        
                        # Get company info from CompanyInfo and override with user info
                        company_info = CompanyInfo.get_info()
                        company_info.update({
                            "sender_name": user["name"],
                            "sender_title": user.get("title", "Estimator"),
                            "sender_email": user.get("email", smtp_settings["from_email"]),
                            "sender_phone": user.get("phone", CompanyInfo.get_sender_phone())
                        })
                        
                        # Load vendors
                        vendors_data = load_vendors(vendor_file)
                        
                        # Process only selected parts
                        selected_parts_df = df.iloc[selected_indices]
                        results = []
                        
                        for _, row in selected_parts_df.iterrows():
                            part_number = row["part_number"]
                            process = row["process"]
                            
                            # Find vendors for this process
                            process_vendors = find_vendors_for_process(vendors_data, process)
                            
                            if not process_vendors:
                                results.append({
                                    "part_number": part_number,
                                    "process": process,
                                    "status": "No vendors found",
                                    "emails_sent": 0
                                })
                                continue
                            
                            # Send emails to each vendor
                            emails_sent = 0
                            for vendor in process_vendors:
                                try:
                                    # Get primary contact
                                    contact = get_primary_contact(vendor)
                                    
                                    if not contact or not contact.get('email'):
                                        logger.warning(f"No valid contact found for vendor: {vendor.get('name', 'Unknown')}")
                                        continue
                                    
                                    # Create email content
                                    recipient, subject, body = create_rfq_email(
                                        queue_items=pd.DataFrame([row]), 
                                        vendor=vendor, 
                                        contact=contact, 
                                        template_path=template_path, 
                                        company_info=company_info
                                    )
                                    
                                    if not recipient or not subject or not body:
                                        logger.warning(f"Failed to create email for vendor: {vendor.get('name', 'Unknown')}")
                                        continue
                                    
                                    # Send the email
                                    if send_email(
                                        recipient=recipient,
                                        subject=subject,
                                        body=body,
                                        smtp_settings=smtp_settings
                                    ):
                                        emails_sent += 1
                                        logger.info(f"Draft email created successfully for {recipient} for {part_number}")
                                    else:
                                        logger.warning(f"Failed to create draft email for {recipient} for {part_number}")
                                except Exception as e:
                                    logger.error(f"Error creating draft email for {vendor.get('name', 'Unknown')} for {part_number}: {str(e)}")
                            
                            results.append({
                                "part_number": part_number,
                                "process": process,
                                "status": "Success" if emails_sent > 0 else "Failed",
                                "emails_sent": emails_sent
                            })
                        
                        # Display results
                        results_df = pd.DataFrame(results)
                        st.success(f"Processed {len(results)} parts. Created {results_df['emails_sent'].sum()} draft emails in Outlook.")
                        st.dataframe(results_df, use_container_width=True, hide_index=True)
                        
                        # Log the action
                        logger.info(f"RFQ draft emails created by {user['name']} for {len(results)} parts")
                        
                except Exception as e:
                    st.error(f"Error creating RFQ email drafts: {str(e)}")
                    logger.error(f"Error creating RFQ email drafts: {str(e)}")
        
        with col2:
            if st.button("Create Drafts for Entire Queue"):
                if role not in ["admin", "editor"]:
                    st.warning("You need admin or editor privileges to send emails.")
                    return
                
                try:
                    with st.spinner("Processing entire queue..."):
                        # Set up required parameters
                        vendor_file = Paths.VENDOR_FILE
                        template_path = Paths.EMAIL_TEMPLATE_PATH
                        
                        # Get email settings from config
                        exchange_settings = ExchangeConfig.get_settings()
                        
                        # Get company info from config and override with user info
                        company_info = CompanyInfo.get_info()
                        company_info.update({
                            "sender_name": user["name"],
                            "sender_title": user.get("title", "Estimator"),
                            "sender_email": user.get("email", ExchangeConfig.get_from_email()),
                            "sender_phone": user.get("phone", "(123) 456-7890")
                        })
                        
                        # Process the entire queue
                        results = process_queue_and_send_emails(
                            queue_file=str(Paths.QUEUE_PATH),
                            vendor_file=vendor_file,
                            template_path=template_path,
                            exchange_settings=ExchangeConfig.get_settings(),
                            company_info=company_info
                        )
                        
                        # Display results
                        if isinstance(results, tuple) and len(results) == 2:
                            successful, total = results
                            st.success(f"Processed entire queue. Created {successful} of {total} draft emails in Outlook.")
                        else:
                            results_df = pd.DataFrame(results)
                            st.success(f"Processed {len(results)} parts. Created {results_df['emails_sent'].sum()} draft emails in Outlook.")
                            st.dataframe(results_df, use_container_width=True, hide_index=True)
                        
                        # Log the action
                        logger.info(f"Entire queue processed by {user['name']}, draft emails created")
                        
                except Exception as e:
                    st.error(f"Error creating draft emails for queue: {str(e)}")
                    logger.error(f"Error creating draft emails for queue: {str(e)}")
        
    except Exception as e:
        st.error(f"Error loading queue data: {str(e)}")
        logger.error(f"Error loading queue data: {str(e)}")

def display_email_settings():
    """Display email settings from Streamlit secrets."""
    st.subheader("Email Settings")
    
    # Display current settings
    st.info("""
    Email settings are configured in the Streamlit secrets file. 
    Current configuration is displayed below for reference only.
    To change these settings, edit the .streamlit/secrets.toml file directly.
    """)
    
    # Display settings in expandable section
    with st.expander("View Current Email Settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Exchange Settings**")
            st.text(f"Exchange Server: {ExchangeConfig.get_server()}")
            st.text(f"Exchange Username: {ExchangeConfig.get_username()}")
            st.text(f"From Email: {ExchangeConfig.get_from_email()}")
            # Don't display password for security reasons
            st.text(f"Password: {'*' * 8 if ExchangeConfig.get_password() else 'Not set'}")
        
        with col2:
            st.markdown("**Company Settings**")
            st.text(f"Company Name: {CompanyInfo.get_name()}")
            st.text(f"Sender Name: {CompanyInfo.get_sender_name()}")
            st.text(f"Sender Title: {CompanyInfo.get_sender_title()}")
            st.text(f"Sender Phone: {CompanyInfo.get_sender_phone()}")
    
    # Test email button
    if st.button("Create Test Email Draft"):
        try:
            # Get email settings from ExchangeConfig
            smtp_settings = {
                "server": ExchangeConfig.get_server(),
                "port": 587,
                "username": ExchangeConfig.get_username(),
                "password": ExchangeConfig.get_password(),
                "use_tls": True,
                "from_email": ExchangeConfig.get_from_email(),
                "cc": ExchangeConfig.get_cc_email()
            }
            
            # Create a test email
            test_email = {
                "to": ExchangeConfig.get_from_email(),
                "subject": "Test RFQ Email",
                "body": "This is a test email from the RFQ Sender application.",
                "cc": [],
                "attachments": []
            }
            
            # Send the test email
            send_email(
                recipient=test_email["to"],
                subject=test_email["subject"],
                body=test_email["body"],
                smtp_settings=smtp_settings,
                attachments=test_email.get("attachments", [])
            )
            st.success("Test email draft created successfully in Outlook!")
            logger.info("Test email draft created successfully in Outlook")
            
        except Exception as e:
            st.error(f"Error creating test email draft: {str(e)}")
            logger.error(f"Error creating test email draft: {str(e)}")

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
    
    # Display email settings
    display_email_settings()
    
    # Display queue for sending emails
    display_queue_for_emails(user, role)

if __name__ == "__main__":
    main()