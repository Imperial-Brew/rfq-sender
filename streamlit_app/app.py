import streamlit as st
from pathlib import Path
import sys
import logging
import yaml
import datetime

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent
# Prepend project root to ensure local modules shadow similarly-named third-party ones
sys.path.insert(0, str(parent_dir))

# Import utility functions
from streamlit_app.utils.auth_shim import load_users, get_user_role, validate_session
from streamlit_app.components.logout_button import logout_button
from utils.rfq_logging import get_logger, configure_root_logger
from utils.rfq_queue import load_queue as load_queue_df

# Configure root logger first (ensures logs directory exists)
configure_root_logger()

# Get module-specific logger
logger = get_logger(__name__)


def setup_page_config():
    """Configure the Streamlit page settings."""
    st.set_page_config(
        page_title="RFQ Sender",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def check_authentication():
    """Check if user is authenticated and session is valid."""
    if not st.session_state.get("authenticated", False):
        st.sidebar.warning("Please log in to access the application")
        st.switch_page("pages/00_login.py")
        return False

    # Check if session is valid
    user = st.session_state.get("user", {})
    session_token = user.get("session_token")
    session_expiry = st.session_state.get("session_expiry")

    if not validate_session(session_token, session_expiry):
        st.sidebar.warning("Your session has expired. Please log in again.")
        # Clear session state
        for key in ["authenticated", "user", "session_expiry"]:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("pages/00_login.py")
        return False

    return True


def display_user_info():
    """Display user information in the sidebar."""
    user = st.session_state.get("user", {})
    if user:
        st.sidebar.markdown(f"**User:** {user.get('name')}")
        st.sidebar.markdown(f"**Role:** `{user.get('role', 'viewer')}`")

        # Add logout button
        logout_button()


def display_home_page():
    """Display the home page content."""
    st.header("Welcome to RFQ Sender")
    st.markdown("""
    This application helps you manage and send Request for Quote (RFQ) emails 
    to vendors for various manufacturing processes.

    ### Features:
    - Add parts to the RFQ queue
    - View and filter the current queue
    - Add new specifications and processes
    - View familiar specifications
    - Send RFQ emails to vendors

    ### Getting Started:
    1. Use the pages in the sidebar to navigate
    2. Start by adding parts to the queue
    3. Send RFQ emails to vendors
    """)

    # Display system stats
    try:
        # Count files in various directories
        docs_dir = parent_dir / "docs"
        specs_file = parent_dir / "docs" / "OS" / "spec_lists" / "FamiliarSpecs.csv"
        queue_file = parent_dir / "docs" / "queue.csv"

        col1, col2, col3 = st.columns(3)

        # Display specs count if file exists
        if specs_file.exists():
            import pandas as pd
            specs_df = pd.read_csv(specs_file)
            with col1:
                st.metric("Specifications", len(specs_df))

        # Display queue count (Box-first via utils.queue.load_queue)
        try:
            queue_df = load_queue_df()
            with col2:
                st.metric("Queue Items", len(queue_df))
        except Exception as e:
            logger.warning(f"Unable to load queue for metric: {e}")

        # Display document count
        with col3:
            doc_count = sum(1 for _ in docs_dir.glob("**/*") if _.is_file())
            st.metric("Documents", doc_count)

    except Exception as e:
        logger.error(f"Error displaying stats: {str(e)}")


def main():
    """Main function to run the Streamlit application."""
    try:
        # Set up page configuration
        setup_page_config()
        
        # Main app header
        st.title("📬 RFQ Sender System")
        
        # Check authentication
        if check_authentication():
            # Display user info in sidebar
            display_user_info()
            
            # Display home page content
            display_home_page()
    except KeyError as e:
        if str(e) == "'streamlit_app'":
            st.error("Application structure error: 'streamlit_app' key not found. This may be due to how the application is deployed.")
            logger.error(f"KeyError in main application: {str(e)}")
        else:
            raise


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logger.exception("Unhandled exception in main application")