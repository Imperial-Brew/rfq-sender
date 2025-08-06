import streamlit as st
import datetime
from pathlib import Path
import sys

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

from utils.auth import validate_session


def require_authentication(role=None):
    """
    Middleware to require authentication before accessing a page.

    Args:
        role: Optional role requirement (e.g., 'admin')

    Returns:
        bool: True if authenticated and role matches, False otherwise
    """
    # Check if authenticated
    if not st.session_state.get("authenticated", False):
        st.warning("Please log in to access this page")
        st.stop()
        return False

    # Check if session is valid
    user = st.session_state.get("user", {})
    session_token = user.get("session_token")
    session_expiry = st.session_state.get("session_expiry")

    if not validate_session(session_token, session_expiry):
        st.warning("Your session has expired. Please log in again.")
        # Clear session state
        for key in ["authenticated", "user", "session_expiry"]:
            if key in st.session_state:
                del st.session_state[key]
        st.stop()
        return False

    # Check role if specified
    if role and user.get("role") != role:
        st.error(f"You need {role} privileges to access this page")
        st.stop()
        return False

    return True