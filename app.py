# app.py (process inside form with live spec filtering)
import streamlit as st
import pandas as pd
import yaml
import os
import json
from utils.auth import load_users, get_user_role
from utils.queue import load_queue, add_to_queue, QUEUE_PATH
import logging
from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig, LoggingConfig, init_config

# Initialize configuration
init_config()

# Set up logging using the centralized configuration
logger = LoggingConfig.setup_logging(__name__, "app.log")

from utils.specs import (
    load_process_list,
    load_specs_for_process,
    load_issuers,
    add_spec_entry,
    spec_exists,
    load_familiar_specs
)
from utils.email import (
    load_vendors,
    find_vendors_for_process,
    find_vendors_for_process_and_spec,
    load_vendor_options,
    get_primary_contact,
    create_rfq_email,
    send_email,
    process_queue_and_send_emails
)

st.set_page_config(page_title="RFQ Tool", layout="wide")

# --- Load users ---
users = load_users("users.yaml")
user_names = [user["name"] for user in users]
selected_user = st.sidebar.selectbox("Who are you?", user_names)
user = next((u for u in users if u["name"] == selected_user), None)
role = get_user_role(user)

st.sidebar.markdown(f"**Role:** `{role}`")
st.title("📬 RFQ Entry + Spec Tracker")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Add to Queue", "📋 View Queue", "🧾 Add Spec/Process", "🔍 View Familiar Specs", "📧 Send RFQ Emails"])

# --- Add to Queue ---
with tab1:
    # Initialize session state variables if they don't exist
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    if 'success_message' not in st.session_state:
        st.session_state.success_message = ""
    
    # Initialize form reset counter to force widget key changes
    if 'form_reset_counter' not in st.session_state:
        st.session_state.form_reset_counter = 0
        
    # Check if we need to reset the form
    if st.session_state.form_submitted:
        # Increment the reset counter to force new widget keys
        st.session_state.form_reset_counter += 1
        
        # Log for debugging
        st.sidebar.write(f"Debug - Form reset triggered. New counter value: {st.session_state.form_reset_counter}")
        
        # Reset the flag
        st.session_state.form_submitted = False
    
    # Display success message if it exists
    if st.session_state.success_message:
        # Create a more prominent success message
        st.markdown("""
        <div style="padding: 1rem; background-color: #d4edda; border-radius: 0.5rem; margin-bottom: 1rem; 
                    border-left: 0.5rem solid #28a745; font-weight: bold; font-size: 1.1rem;">
            {}
        </div>
        """.format(st.session_state.success_message), unsafe_allow_html=True)
        
        # Clear the message after displaying it once
        st.session_state.success_message = ""
    
    st.subheader("Submit New Part for Quote")
    processes = load_process_list()

    # Debug the processes list
    st.sidebar.write("Debug - Available Processes:", processes)
    
    # Get current reset counter for unique keys
    reset_counter = st.session_state.form_reset_counter
    
    # Process selection outside the form with dynamic key
    selected_process = st.selectbox(
        "Process", 
        options=[""] + sorted(processes), 
        key=f"proc_select_{reset_counter}"
    )
    
    # Load specs based on selected process
    available_specs = []
    if selected_process:
        available_specs = load_specs_for_process(selected_process)
        st.sidebar.write("Debug - Selected Process:", selected_process)
        st.sidebar.write("Debug - Available Specs:", available_specs)
    
    # Spec selection outside the form with dynamic key
    spec = st.selectbox(
        "Spec (optional)", 
        options=[""] + available_specs,
        key=f"spec_select_{reset_counter}"
    )
    
    with st.form(f"rfq_form_{reset_counter}"):
        part_number = st.text_input("Part Number", key=f"part_number_{reset_counter}")
        callout = st.text_input("Callout", key=f"callout_{reset_counter}")  # New callout field before process
        
        # Display the selected process and spec (read-only)
        st.text(f"Selected Process: {selected_process}")
        st.text(f"Selected Spec: {spec}")
        material = st.text_input("Material", key=f"material_{reset_counter}")  # Add material field
        quantity = st.text_input("Quantities (comma separated)", key=f"quantity_{reset_counter}")  # No default value
        file_location = st.text_input("File Location", key=f"file_location_{reset_counter}")
        # Removed expedited checkbox
        st.markdown(
            "**Note:** If you select a process, the spec will be filtered to only those familiar with that process.")
        submitted = st.form_submit_button("Add to Queue")

        if submitted:
            if not part_number:
                st.warning("Part number is required.")
            elif not selected_process:
                st.warning("Process is required. Please select a process before submitting.")
            else:
                try:
                    # Add to queue
                    add_to_queue(QUEUE_PATH, {
                        "part_number": part_number.strip(),
                        "callout": callout.strip(),
                        "process": selected_process.strip(),
                        "spec": spec.strip(),
                        "material": material.strip(),
                        "quantities": quantity.strip(),
                        "file_location": file_location.strip(),
                        "submitted_by": user["name"]
                    })
                    
                    # Log successful submission for debugging
                    st.sidebar.write(f"Debug - Successfully added part {part_number} to queue")
                    
                    # Store success message in session state so it persists after rerun
                    st.session_state.success_message = f"✅ Part {part_number} added to queue!"
                    
                    # Set form_submitted flag to true to reset the form on next run
                    st.session_state.form_submitted = True
                    
                    # Rerun the app to reset the form
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding to queue: {str(e)}")
                    st.sidebar.write(f"Debug - Error: {str(e)}")

# --- View Queue ---
with tab2:
    st.subheader("Queued Parts")
    df = load_queue(QUEUE_PATH)
    if df.empty:
        st.info("No parts in queue.")
    else:
        search = st.text_input("Search", "")
        if search:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
        st.dataframe(df, use_container_width=True)

# --- Add Spec/Process ---
with tab3:
    st.subheader("Add New Spec or Process")
    if role in ["admin", "estimator"]:
        issuers = load_issuers()

        with st.form("add_spec_form"):
            new_process = st.text_input("Process")
            new_spec = st.text_input("Spec")
            new_issuer = st.selectbox("Issuer", options=issuers + ["Other"])
            custom_issuer = ""
            if new_issuer == "Other":
                custom_issuer = st.text_input("Enter custom issuer")
            notes = st.text_area("Notes")

            spec_submit = st.form_submit_button("Add to Familiar Specs")
            if spec_submit:
                issuer_value = custom_issuer.strip() if new_issuer == "Other" else new_issuer

                if not new_process or not new_spec:
                    st.warning("Process and Spec are required.")
                elif spec_exists(new_process, new_spec):
                    st.warning("That process + spec combo already exists.")
                else:
                    add_spec_entry(new_process, new_spec, issuer_value, notes)
                    st.success("✅ New spec added.")
    else:
        st.info("You don’t have permission to add specs.")

# --- View Familiar Specs ---
with tab4:
    st.subheader("Familiar Specs List")
    spec_df = load_familiar_specs()
    if spec_df.empty:
        st.info("No familiar specs found.")
    else:
        search_term = st.text_input("Search spec or process", "")
        if search_term:
            spec_df = spec_df[spec_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
        st.dataframe(spec_df, use_container_width=True)

# --- Send RFQ Emails ---
with tab5:
    st.subheader("Send RFQ Emails to Vendors")

    # Initialize session state for email sending
    if 'email_sent' not in st.session_state:
        st.session_state.email_sent = False

    if 'email_results' not in st.session_state:
        st.session_state.email_results = None

    # Display success message if draft emails were created
    if st.session_state.email_sent and st.session_state.email_results:
        successful, total = st.session_state.email_results
        st.markdown(f"""
        <div style="padding: 1rem; background-color: #d4edda; border-radius: 0.5rem; margin-bottom: 1rem; 
                    border-left: 0.5rem solid #28a745; font-weight: bold; font-size: 1.1rem;">
            ✅ Draft emails created successfully! {successful} of {total} draft emails created in {user["name"]}'s Outlook.
        </div>
        """, unsafe_allow_html=True)

        # Reset the flag after displaying
        st.session_state.email_sent = False

    # Load queue data
    queue_df = load_queue(QUEUE_PATH)

    if queue_df.empty:
        st.warning("No items in queue. Add items to the queue before sending emails.")
    else:
        # Load vendor data from both sources
        vendor_file = "config/vendors.json"
        vendor_options_file = "docs/OS/vendor_options.yaml"

        if os.path.exists(vendor_file) and os.path.exists(vendor_options_file):
            vendors = load_vendors(vendor_file)
            vendor_options = load_vendor_options(vendor_options_file)

            # Hardcoded company info using user data
            company_info = {
                "name": "Athena Manufacturing",
                "sender_name": user["name"],
                "sender_title": "Estimator",
                "sender_email": user["email"],
                "sender_phone": "(123) 456-7890",  # You might want to add this to users.yaml
                "address": "123 Main St, Anytown, USA"  # Replace with actual address
            }

            # Email template selection
            template_path = "config/templates/email_signature.html"
            if not os.path.exists(template_path):
                st.warning(f"Email template not found at {template_path}")

            # Queue filtering
            st.subheader("Queue Items to Send")

            # Filter options
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                search_term = st.text_input("Search Queue", "")

            with filter_col2:
                process_filter = st.multiselect(
                    "Filter by Process",
                    options=sorted(queue_df['process'].unique()),
                    default=[]
                )

            # Apply filters
            filtered_df = queue_df.copy()
            if search_term:
                filtered_df = filtered_df[filtered_df.apply(
                    lambda row: row.astype(str).str.contains(search_term, case=False).any(),
                    axis=1
                )]

            if process_filter:
                filtered_df = filtered_df[filtered_df['process'].isin(process_filter)]

            # Display filtered queue
            st.dataframe(filtered_df, use_container_width=True)

            # Vendor preview
            st.subheader("Vendor Preview")

            # Get unique processes from filtered queue
            unique_processes = filtered_df['process'].unique()

            # Show vendors for each process
            for process in unique_processes:
                # Get items for this process
                process_items = filtered_df[filtered_df['process'] == process]

                # Check if we have spec information for this process
                has_spec = 'spec' in process_items.columns and not process_items['spec'].isna().all() and \
                           process_items['spec'].iloc[0]

                if has_spec:
                    # Get the spec for this process
                    spec = process_items['spec'].iloc[0]
                    st.write(f"**Process: {process}, Spec: {spec}**")

                    # Find vendors that support this process and spec
                    process_vendors = find_vendors_for_process_and_spec(vendors, vendor_options, process, spec)
                else:
                    st.write(f"**Process: {process}**")
                    # Find vendors that support this process only
                    process_vendors = find_vendors_for_process(vendors, process)

                if process_vendors:
                    vendor_names = [v.get('name', 'Unknown') for v in process_vendors]
                    st.write(f"Vendors: {', '.join(vendor_names)}")
                else:
                    st.warning(f"No vendors found for process: {process}" + (f" with spec: {spec}" if has_spec else ""))

            # Create draft emails button
            if st.button("Create Draft Emails", type="primary", disabled=filtered_df.empty):
                # Use the hardcoded company_info defined above
                
                # Exchange settings from environment variables
                exchange_settings = {
                    "username": os.getenv("EXCHANGE_USERNAME", user["email"]),
                    "from_email": os.getenv("EXCHANGE_FROM_EMAIL", user["email"]),
                    "cc": os.getenv("EXCHANGE_CC_EMAIL", "")
                }

                # Save filtered queue to temporary file
                temp_queue_file = "temp_queue.csv"
                filtered_df.to_csv(temp_queue_file, index=False)

                try:
                    # Process queue and create draft emails
                    with st.spinner("Creating draft emails in Outlook..."):
                        successful, total = process_queue_and_send_emails(
                            temp_queue_file,
                            vendor_file,
                            template_path,
                            exchange_settings,
                            company_info,
                            vendor_options_file  # Add vendor_options_file as a parameter
                        )

                    # Store results in session state
                    st.session_state.email_results = (successful, total)
                    st.session_state.email_sent = True

                    # Rerun to show success message
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating draft emails: {str(e)}")
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_queue_file):
                        os.remove(temp_queue_file)
        else:
            if not os.path.exists(vendor_file):
                st.error(f"Vendor file not found at {vendor_file}")
            if not os.path.exists(vendor_options_file):
                st.error(f"Vendor options file not found at {vendor_options_file}")
            st.info("Please ensure both vendor files exist.")