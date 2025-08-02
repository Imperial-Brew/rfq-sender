import streamlit as st
from pathlib import Path
import sys
import logging
import yaml

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

# Import utility functions
from utils.auth import load_users, get_user_role

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(parent_dir / "logs" / "app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_page_config():
    """Configure the Streamlit page settings."""
    st.set_page_config(
        page_title="RFQ Sender",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="expanded",
    )

def load_user_data():
    """Load user data and set up session state for user authentication."""
    # Load users from YAML file
    users_path = parent_dir / "users.yaml"
    
    if not users_path.exists():
        st.sidebar.error("Users configuration file not found.")
        return None
    
    try:
        users = load_users(str(users_path))
        user_names = [user["name"] for user in users]
        
        # User selection in sidebar
        selected_user = st.sidebar.selectbox("Who are you?", user_names)
        user = next((u for u in users if u["name"] == selected_user), None)
        role = get_user_role(user)
        
        # Store user in session state for access in other pages
        st.session_state.user = user
        
        # Display user info
        st.sidebar.markdown(f"**Role:** `{role}`")
        
        return user
    except Exception as e:
        st.sidebar.error(f"Error loading user data: {str(e)}")
        logger.error(f"Error loading user data: {str(e)}")
        return None

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
        
        # Display queue count if file exists
        if queue_file.exists():
            import pandas as pd
            queue_df = pd.read_csv(queue_file)
            with col2:
                st.metric("Queue Items", len(queue_df))
        
        # Display document count
        with col3:
            doc_count = sum(1 for _ in docs_dir.glob("**/*") if _.is_file())
            st.metric("Documents", doc_count)
            
    except Exception as e:
        logger.error(f"Error displaying stats: {str(e)}")

def main():
    """Main function to run the Streamlit application."""
    # Set up page configuration
    setup_page_config()
    
    # Main app header
    st.title("📬 RFQ Sender System")
    
    # Load user data
    user = load_user_data()
    
    if user:
        # Display home page content
        display_home_page()
    else:
        st.warning("Please select a user to continue.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logger.exception("Unhandled exception in main application")