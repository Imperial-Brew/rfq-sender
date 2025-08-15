import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import the shared utils.auth
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Re-export selected auth helpers from the shared utils.auth module
try:
    from utils.auth import (
        load_users,
        login_user,
        validate_session,
        get_user_role,
        hash_password,
        verify_password,
        create_session_token,
        logout_user,
    )
except Exception as e:
    # Provide minimal fallbacks to avoid hard crashes if import fails
    _IMPORT_ERR = f"{type(e).__name__}: {e}"

    def load_users(path):
        raise ImportError(f"Failed to import utils.auth.load_users: {_IMPORT_ERR}")

    def login_user(users, email, password):
        raise ImportError(f"Failed to import utils.auth.login_user: {_IMPORT_ERR}")

    def validate_session(token, expiry):
        return False

    def get_user_role(user):
        return user.get("role", "viewer")

    def hash_password(password: str) -> str:
        raise ImportError(f"Failed to import utils.auth.hash_password: {_IMPORT_ERR}")

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        raise ImportError(f"Failed to import utils.auth.verify_password: {_IMPORT_ERR}")

    def create_session_token() -> str:
        raise ImportError(f"Failed to import utils.auth.create_session_token: {_IMPORT_ERR}")

    def logout_user(user):
        pass
