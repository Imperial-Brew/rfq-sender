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
    load_familiar_specs,
    load_process_list,
    load_issuers,
    SPECS_PATH
)
from utils.auth import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication

if not require_authentication():
    st.stop()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(parent_dir / "logs" / "view_familiar_specs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_page():
    """Configure the page settings."""
    st.title("View Familiar Specifications")
    st.markdown("""
    This page displays all familiar specifications in the database.
    You can filter and search for specific specifications by process, issuer, or keyword.
    """)

def display_specs_data(user, role):
    """Display the specifications data with filtering options."""
    try:
        # Load specs data
        df = load_familiar_specs()
        
        if df.empty:
            st.info("No specifications found in the database. Add specs using the 'Add Spec/Process' page.")
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
    
    # Display specs data
    display_specs_data(user, role)

if __name__ == "__main__":
    main()