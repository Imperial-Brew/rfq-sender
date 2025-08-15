import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import logging

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import utility functions
from core.vendors.vendor_manager import VendorManager
from utils.specs import load_process_list, load_specs_for_process
from streamlit_app.utils.auth_shim import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication
from utils.logging import get_logger

if not require_authentication():
    st.stop()

# Initialize logger
logger = get_logger(__name__)

# Initialize vendor manager
vendor_manager = VendorManager()

def setup_page():
    """Configure the page settings."""
    st.title("Vendor Management")
    st.markdown("""
    This page allows you to view vendor information, including their contact details, 
    process capabilities, and approved specifications.
    """)

def display_vendor_list():
    """Display the list of vendors with filtering options."""
    st.subheader("Vendor List")
    
    # Get all vendors
    vendors = vendor_manager.vendors
    
    # Create a search box for filtering vendors
    search_term = st.text_input("Search Vendors", "")
    
    # Filter vendors based on search term
    if search_term:
        filtered_vendors = [v for v in vendors if search_term.lower() in v.get('name', '').lower()]
    else:
        filtered_vendors = vendors
    
    # Create a selectbox for choosing a vendor
    vendor_names = [v.get('name', '') for v in filtered_vendors]
    
    if not vendor_names:
        st.warning("No vendors found matching your search criteria.")
        return None
    
    selected_vendor_name = st.selectbox("Select a Vendor", options=vendor_names)
    
    # Find the selected vendor
    selected_vendor = next((v for v in filtered_vendors if v.get('name', '') == selected_vendor_name), None)
    
    return selected_vendor

def display_vendor_details(vendor):
    """Display detailed information about a selected vendor."""
    if not vendor:
        return
    
    st.subheader(f"Vendor Details: {vendor.get('name', '')}")
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Contact Information", "Process Capabilities", "Approved Specifications"])
    
    with tab1:
        st.markdown("### Contact Information")
        
        # Display address
        address = vendor.get('address', {})
        address_str = ", ".join([v for k, v in address.items() if v])
        st.markdown(f"**Address:** {address_str}")
        
        # Display contacts
        contacts = vendor.get('contacts', [])
        if contacts:
            for i, contact in enumerate(contacts):
                st.markdown(f"#### Contact {i+1}")
                st.markdown(f"**Name:** {contact.get('name', '')}")
                st.markdown(f"**Email:** {contact.get('email', '')}")
                st.markdown(f"**Phone:** {contact.get('phone', '')}")
                if contact.get('primary', False):
                    st.markdown("**Primary Contact:** Yes")
                st.markdown("---")
        else:
            st.info("No contact information available for this vendor.")
    
    with tab2:
        st.markdown("### Process Capabilities")
        
        # Display processes
        processes = vendor.get('processes', [])
        if processes:
            for process in sorted(processes):
                st.markdown(f"- {process}")
        else:
            st.info("No process capabilities listed for this vendor.")
    
    with tab3:
        st.markdown("### Approved Specifications")
        
        # Get processes for this vendor
        processes = vendor.get('processes', [])
        
        if not processes:
            st.info("No processes listed for this vendor, so no specifications can be shown.")
            return
        
        # Create a selectbox for choosing a process
        selected_process = st.selectbox("Select a Process", options=sorted(processes))
        
        # Get specs for the selected process
        specs = load_specs_for_process(selected_process)
        
        if specs:
            st.markdown(f"#### Specifications for {selected_process}")
            for spec in specs:
                st.markdown(f"- {spec}")
        else:
            st.info(f"No specifications found for the process '{selected_process}'.")

def search_vendors_by_spec():
    """Search for vendors approved for a specific specification."""
    st.subheader("Search Vendors by Specification")
    
    # Get all processes
    processes = load_process_list()
    
    # Create a selectbox for choosing a process
    selected_process = st.selectbox(
        "Select Process", 
        options=sorted(processes),
        key="search_process"
    )
    
    # Get specs for the selected process
    specs = load_specs_for_process(selected_process)
    
    if not specs:
        st.warning(f"No specifications found for the process '{selected_process}'.")
        return
    
    # Create a selectbox for choosing a spec
    selected_spec = st.selectbox("Select Specification", options=sorted(specs))
    
    # Search button
    if st.button("Search Vendors"):
        # Find vendors for the selected process and spec
        matching_vendors = vendor_manager.find_vendors_for_process_and_spec(selected_process, selected_spec)
        
        if matching_vendors:
            st.success(f"Found {len(matching_vendors)} vendors approved for {selected_spec} ({selected_process})")
            
            # Display the matching vendors
            for vendor in matching_vendors:
                with st.expander(vendor.get('name', '')):
                    # Display contact info
                    primary_contact = vendor_manager.get_primary_contact(vendor)
                    if primary_contact:
                        st.markdown(f"**Primary Contact:** {primary_contact.get('name', '')}")
                        st.markdown(f"**Email:** {primary_contact.get('email', '')}")
                        st.markdown(f"**Phone:** {primary_contact.get('phone', '')}")
                    
                    # Display address
                    address = vendor.get('address', {})
                    address_str = ", ".join([v for k, v in address.items() if v])
                    if address_str:
                        st.markdown(f"**Address:** {address_str}")
        else:
            st.warning(f"No vendors found that are approved for {selected_spec} ({selected_process})")

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
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["Vendor Directory", "Search by Specification"])
    
    with tab1:
        selected_vendor = display_vendor_list()
        if selected_vendor:
            display_vendor_details(selected_vendor)
    
    with tab2:
        search_vendors_by_spec()

if __name__ == "__main__":
    main()