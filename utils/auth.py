import bcrypt
import secrets
import datetime
import yaml
from typing import Dict, List, Optional, Any


def load_users(path: str) -> List[Dict[str, Any]]:
    """Load users from YAML file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)["users"]


def get_user_role(user: Dict[str, Any]) -> str:
    """Get user role or default to viewer."""
    return user.get("role", "viewer")


def hash_password(password: str) -> str:
    """Generate bcrypt hash for password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_session_token() -> str:
    """Generate unique session token."""
    return secrets.token_hex(32)


def validate_session(token: str, expiry: datetime.datetime) -> bool:
    """Check if session is valid and not expired."""
    if not token or not expiry:
        return False
    return datetime.datetime.now() < expiry


def login_user(users: List[Dict[str, Any]], email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user and create session."""
    user = next((u for u in users if u["email"] == email), None)
    if not user or not verify_password(password, user.get("password_hash", "")):
        return None

    # Update user with session info
    user["session_token"] = create_session_token()
    user["last_login"] = datetime.datetime.now()

    return user


def logout_user(user: Dict[str, Any]) -> None:
    """Clear session data."""
    if user:
        user["session_token"] = None