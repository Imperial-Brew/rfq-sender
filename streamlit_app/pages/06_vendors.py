import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import logging

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import utility functions
from core.vendors.vendor_manager import VendorManager
from utils.specs import load_process_list, load_specs_for_process
from streamlit_app.utils.auth_shim import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication
from utils.rfq_logging import get_logger

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

def safe_get_vendor_approvals(vendor_name: str) -> dict:
    """Compatibility shim: get approvals defensively even if VendorManager lacks the method."""
    try:
        # Preferred path: use VendorManager method if available
        if hasattr(vendor_manager, "get_vendor_approvals") and callable(getattr(vendor_manager, "get_vendor_approvals")):
            return vendor_manager.get_vendor_approvals(vendor_name)
    except Exception as e:
        try:
            logger.exception("get_vendor_approvals via VendorManager failed; falling back to direct YAML parse")
        except Exception:
            pass
    # Fallback: read YAML directly and parse safely
    approvals = {}
    try:
        import yaml
        path = getattr(vendor_manager, "vendor_options_file", "docs/OS/vendor_options.yaml")
        with open(path, "r", encoding="utf-8") as f:
            vo = yaml.safe_load(f) or {}
        vendors = vo.get("vendors", []) or []
        # Find vendor entry: exact then case-insensitive
        entry = None
        for v in vendors:
            if isinstance(v, dict) and v.get("name") == vendor_name:
                entry = v
                break
        if entry is None:
            vn = (vendor_name or "").strip().lower()
            for v in vendors:
                if isinstance(v, dict) and str(v.get("name", "")).strip().lower() == vn:
                    entry = v
                    break
        if not entry:
            return {}
        for p in (entry.get("processes", []) or []):
            if not isinstance(p, dict):
                continue
            pname = p.get("name", "")
            specs = p.get("specs") or []
            vals = []
            for s in specs:
                if isinstance(s, dict) and "number" in s:
                    vals.append(s["number"])
            approvals[pname] = vals
    except Exception:
        # Silent fallback to empty approvals to avoid crashing the page
        try:
            logger.exception("Failed to parse vendor approvals from YAML fallback")
        except Exception:
            pass
        approvals = {}
    return approvals


def display_vendor_details(vendor):
    """Display detailed information about a selected vendor."""
    if not vendor:
        return

    st.subheader(f"Vendor Details: {vendor.get('name', '')}")

    tab1, tab2, tab3 = st.tabs(["Contact Information", "Process Capabilities", "Approved Specifications"])

    with tab1:
        # existing contact info block...
        address = vendor.get('address', {})
        address_str = ", ".join([v for k, v in address.items() if v])
        st.markdown(f"**Address:** {address_str}")
        contacts = vendor.get('contacts', [])
        if not contacts:
            try:
                contacts = vendor_manager.get_contacts_for_vendor(vendor.get('name', ''))
            except Exception:
                contacts = []
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
        processes = vendor.get('processes', [])
        if processes:
            for process in sorted(processes):
                st.markdown(f"- {process}")
        else:
            st.info("No process capabilities listed for this vendor.")

    with tab3:
        st.markdown("### Approved Specifications")

        vendor_name = vendor.get('name', '')
        approvals = safe_get_vendor_approvals(vendor_name)

        if not approvals:
            st.info("No approvals found for this vendor in vendor_options.yaml.")
            return

        # Role-gated edit controls (default read-only for non-admins)
        role = None
        try:
            if "user" in st.session_state:
                from streamlit_app.utils.auth_shim import get_user_role
                role = get_user_role(st.session_state.user)
        except Exception:
            role = None

        editable = (role and str(role).lower() in {"admin", "editor", "manager"})

        # Process selection
        process_names = sorted(approvals.keys())
        sel_process = st.selectbox(
            "Select a Process",
            options=process_names,
            key=f"vendor_proc_{vendor_name}"
        )

        specs = approvals.get(sel_process, [])
        if not specs:
            st.info(f"No specs listed for process '{sel_process}'.")
            return

        st.markdown(f"#### Specs approved for {sel_process}")
        st.write("\n")

        # Let user choose one or more specs for removal
        sel_specs = st.multiselect(
            "Select spec(s) to remove",
            options=sorted(specs),
            key=f"vendor_specs_{vendor_name}_{sel_process}"
        )

        if not editable:
            st.caption("You do not have permission to modify approvals. Contact an admin.")
            return

        col1, col2 = st.columns([1, 3])
        with col1:
            remove_clicked = st.button(
                "Remove selected",
                key=f"remove_specs_{vendor_name}_{sel_process}",
                type="primary",
                disabled=not sel_specs,
                help="Removes the selected spec approvals from this vendor/process"
            )

        if remove_clicked and sel_specs:
            removed_any = False
            failures = []
            for sp in sel_specs:
                ok = vendor_manager.remove_vendor_approval(vendor_name, sel_process, sp)
                if ok:
                    removed_any = True
                else:
                    failures.append(sp)

            if removed_any:
                st.success(f"Removed {len(sel_specs) - len(failures)} spec(s) from {vendor_name} → {sel_process}")
                if failures:
                    st.warning("Failed to remove: " + ", ".join(failures))
                # Refresh the UI view (reload approvals after write)
                approvals = safe_get_vendor_approvals(vendor_name)
            else:
                st.error("No changes were made. Check logs for details.")

        # Readback: show the current remaining specs in an expander
        with st.expander("View current approvals (all processes)", expanded=False):
            for p_name in sorted(approvals.keys()):
                vals = approvals[p_name]
                if vals:
                    st.markdown(f"- **{p_name}**: " + ", ".join(vals))
                else:
                    st.markdown(f"- **{p_name}**: (none)")

def search_vendors_by_spec():
    """Search for vendors approved for a specific specification."""
    st.subheader("Search Vendors by Specification")
    
    # Get all processes
    processes = load_process_list()

    # If processes list is empty, show error and exit early
    if not processes:
        st.error("FamiliarSpecs.csv not found in Box or local path.")
        return
    
    # Create a selectbox for choosing a process
    selected_process = st.selectbox(
        "Select Process", 
        options=sorted(processes),
        key="search_process"
    )
    
    # Get specs for the selected process (guard against None/empty)
    if selected_process:
        specs = load_specs_for_process(selected_process)
        if not specs:
            st.error("FamiliarSpecs.csv not found in Box or local path.")
            return
    else:
        specs = []

    
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