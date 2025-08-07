import streamlit as st
from pathlib import Path
import sys
import yaml

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))


def logout_button():
    """Display logout button in the sidebar."""
    if st.sidebar.button("Logout"):
        logout()


def logout():
    """Clear session state and log out user."""
    if "user" in st.session_state:
        st.session_state.user["session_token"] = None

        # Save updated user data
        users_path = parent_dir / "users.yaml"
        with open(users_path, "r") as f:
            data = yaml.safe_load(f)

        users = data["users"]
        user_index = next((i for i, u in enumerate(users) if u["email"] == st.session_state.user["email"]), None)
        if user_index is not None:
            users[user_index]["session_token"] = None

            with open(users_path, "w") as f:
                yaml.dump(data, f)

    # Clear session state
    for key in ["authenticated", "user", "session_expiry"]:
        if key in st.session_state:
            del st.session_state[key]

    st.rerun()