import streamlit as st
import datetime
from pathlib import Path
import sys
import yaml

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
# Prepend project root to sys.path so local 'utils' package wins over any site-packages 'utils'
sys.path.insert(0, str(parent_dir))

from streamlit_app.utils.auth_shim import load_users, login_user, validate_session


def save_users(users, path):
    """Save updated users to YAML file."""
    with open(path, "w") as f:
        yaml.dump({"users": users}, f)


def main():
    st.title("Login")

    # Check if already logged in
    if "authenticated" in st.session_state and st.session_state.authenticated:
        if "session_expiry" in st.session_state and validate_session(
                st.session_state.user.get("session_token"),
                st.session_state.session_expiry
        ):
            st.success(f"Already logged in as {st.session_state.user['name']}")
            st.button("Logout", on_click=logout)
            return

    # Login form
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        remember_me = st.checkbox("Remember me for 24 hours")
        submit = st.form_submit_button("Login")

        if submit:
            users_path = parent_dir / "users.yaml"
            users = load_users(str(users_path))

            user = login_user(users, email, password)
            if user:
                # Set session state
                st.session_state.authenticated = True
                st.session_state.user = user

                # Set expiry time (24 hours if remember me, 1 hour otherwise)
                expiry_hours = 24 if remember_me else 1
                st.session_state.session_expiry = datetime.datetime.now() + datetime.timedelta(hours=expiry_hours)

                # Save updated user data
                save_users(users, str(users_path))

                st.success(f"Welcome, {user['name']}!")
                st.rerun()
            else:
                st.error("Invalid email or password")


def logout():
    """Clear session state and log out user."""
    if "user" in st.session_state:
        st.session_state.user["session_token"] = None

        # Save updated user data
        users_path = parent_dir / "users.yaml"
        users = load_users(str(users_path))
        user_index = next((i for i, u in enumerate(users) if u["email"] == st.session_state.user["email"]), None)
        if user_index is not None:
            users[user_index]["session_token"] = None
            save_users(users, str(users_path))

    # Clear session state
    for key in ["authenticated", "user", "session_expiry"]:
        if key in st.session_state:
            del st.session_state[key]

    st.rerun()


if __name__ == "__main__":
    main()