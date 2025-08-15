import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import logging

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import utility functions
from utils.specs import (
    load_process_list, 
    load_issuers, 
    add_spec_entry, 
    spec_exists,
    load_familiar_specs,
    SPECS_PATH
)
from streamlit_app.utils.auth_shim import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication
from utils.logging import get_logger

if not require_authentication():
    st.stop()

# Get module-specific logger
logger = get_logger(__name__)

def setup_page():
    """Configure the page settings."""
    st.title("Specifications Management")
    st.markdown("""
    This page allows you to manage specifications in the database.
    Use the tabs below to add new specifications or view existing ones.
    """)

def display_add_spec_form(user, role):
    """Display the form for adding a new spec/process."""
    # Check if user has admin privileges
    if role != "admin":
        st.warning("You need admin privileges to add new specs and processes.")
        return
    
    # Get existing processes and issuers for dropdowns
    processes = load_process_list()
    issuers = load_issuers()
    
    with st.form("add_spec_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Process field with option to add new
            process_options = [""] + sorted(processes) + ["+ Add New Process"]
            selected_process_option = st.selectbox(
                "Process", 
                options=process_options,
                help="Select an existing process or add a new one"
            )
            
            # Show text input if "Add New Process" is selected
            if selected_process_option == "+ Add New Process":
                new_process = st.text_input(
                    "New Process Name",
                    help="Enter the name of the new process"
                )
                process = new_process.strip() if new_process else ""
            else:
                process = selected_process_option
        
        with col2:
            # Spec field
            spec = st.text_input(
                "Specification", 
                help="Enter the specification identifier (e.g., AMS2759)"
            )
            
            # Issuer field with option to add new
            issuer_options = [""] + sorted(issuers) + ["+ Add New Issuer"]
            selected_issuer_option = st.selectbox(
                "Issuer", 
                options=issuer_options,
                help="Select an existing issuer or add a new one"
            )
            
            # Show text input if "Add New Issuer" is selected
            if selected_issuer_option == "+ Add New Issuer":
                new_issuer = st.text_input(
                    "New Issuer Name",
                    help="Enter the name of the new issuer (e.g., SAE, ASTM)"
                )
                issuer = new_issuer.strip() if new_issuer else ""
            else:
                issuer = selected_issuer_option
        
        # Notes field
        notes = st.text_area(
            "Notes", 
            help="Enter any additional information about this specification"
        )
        
        # Submit button
        submitted = st.form_submit_button("Add Specification", use_container_width=True)
        
        if submitted:
            # Validate inputs
            if not process or not spec:
                st.warning("Process and Specification are required fields.")
                logger.warning(f"Submission failed: missing required fields")
                return
            
            # Check if spec already exists for this process
            if spec_exists(process, spec):
                st.warning(f"Specification '{spec}' already exists for process '{process}'.")
                logger.warning(f"Duplicate spec submission: {process} - {spec}")
                return
            
            try:
                # Add the new spec entry
                add_spec_entry(process, spec, issuer, notes)
                
                # Show success message
                st.success(f"✅ Added {spec} for {process} successfully!")
                logger.info(f"New spec added: {process} - {spec} by {user['name']}")
                
                # Clear form (requires rerun)
                st.rerun()
            except Exception as e:
                st.error(f"Error adding specification: {str(e)}")
                logger.error(f"Error adding specification: {str(e)}")

def display_current_specs():
    """Display a preview of recently added specs."""
    try:
        # Load the specs dataframe
        df = pd.read_csv(SPECS_PATH)
        
        if not df.empty:
            st.subheader("Recently Added Specifications")
            
            # Sort by most recently added (assuming the CSV is appended to)
            df = df.tail(5).sort_index(ascending=False)
            
            # Display the dataframe
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
        
    except Exception as e:
        st.error(f"Error loading specifications: {str(e)}")
        logger.error(f"Error loading specifications: {str(e)}")

def display_specs_data(user, role):
    """Display the specifications data with filtering options."""
    try:
        # Load specs data
        df = load_familiar_specs()
        
        if df.empty:
            st.info("No specifications found in the database. Add specs using the 'Add Specification' tab.")
            return
        
        # Add filter options
        st.subheader("Filter Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filter by process
            processes = ["All"] + sorted(load_process_list())
            process_filter = st.selectbox("Filter by Process", processes)
        
        with col2:
            # Filter by issuer
            issuers = ["All"] + sorted(load_issuers())
            issuer_filter = st.selectbox("Filter by Issuer", issuers)
        
        with col3:
            # Search by keyword
            search_term = st.text_input("Search by Keyword", "")
        
        # Apply filters
        filtered_df = df.copy()
        
        if process_filter != "All":
            filtered_df = filtered_df[filtered_df["process"].str.lower() == process_filter.lower()]
        
        if issuer_filter != "All":
            filtered_df = filtered_df[filtered_df["issuer"].str.lower() == issuer_filter.lower()]
        
        if search_term:
            # Search across all columns
            search_mask = pd.Series(False, index=filtered_df.index)
            for col in filtered_df.columns:
                search_mask = search_mask | filtered_df[col].astype(str).str.contains(search_term, case=False, na=False)
            filtered_df = filtered_df[search_mask]
        
        # Display the filtered specs
        st.subheader("Specifications")
        
        if filtered_df.empty:
            st.warning("No specifications match the selected filters.")
            return
        
        # Format the dataframe for display
        display_df = filtered_df.copy()
        
        # Ensure all columns are properly formatted
        for col in display_df.columns:
            if display_df[col].dtype == 'object':
                display_df[col] = display_df[col].fillna("").astype(str)
        
        # Sort by process and spec
        display_df = display_df.sort_values(by=["process", "spec"])
        
        # Display the dataframe
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Add export option
        if st.button("Export Specifications to CSV"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="familiar_specs_export.csv",
                mime="text/csv"
            )
        
        # Display stats
        st.subheader("Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Specifications", len(df))
        
        with col2:
            st.metric("Total Processes", len(df["process"].unique()))
        
        with col3:
            st.metric("Total Issuers", len(df["issuer"].unique()))
        
        # Log the view
        logger.info(f"Specifications viewed by {user['name']} with {len(filtered_df)} entries after filtering")
        
    except Exception as e:
        st.error(f"Error loading specifications data: {str(e)}")
        logger.error(f"Error loading specifications data: {str(e)}")

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
    
    # Create tabs for Add Specification and View Specifications
    tab1, tab2 = st.tabs(["Add Specification", "View Specifications"])
    
    with tab1:
        display_add_spec_form(user, role)
        display_current_specs()
    
    with tab2:
        display_specs_data(user, role)

if __name__ == "__main__":
    main()