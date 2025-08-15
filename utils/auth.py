import os
import yaml
import bcrypt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

__all__ = [
    "load_users",
    "login_user",
    "validate_session",
    "get_user_role",
    "hash_password",
    "verify_password",
    "create_session_token",
    "logout_user",
]


def _read_yaml(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _normalize_email(s: str) -> str:
    return (s or "").strip().lower()


def hash_password(password: str) -> str:
    if password is None:
        raise ValueError("password cannot be None")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_or_plain: str) -> bool:
    if hashed_or_plain is None:
        return False
    hp = str(hashed_or_plain)
    if hp.startswith("$2a$") or hp.startswith("$2b$") or hp.startswith("$2y$"):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hp.encode("utf-8"))
        except Exception:
            return False
    return str(plain_password) == hp


def load_users(path: str) -> List[Dict[str, Any]]:
    if not path:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "users.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"users.yaml not found at: {path}")

    data = _read_yaml(path)
    if isinstance(data, dict):
        for key in ("users", "Users", "accounts"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError("users.yaml must be a list of users or a dict containing a 'users' list")

    users: List[Dict[str, Any]] = []
    for u in data:
        if not isinstance(u, dict):
            continue
        user = dict(u)
        user["email"] = _normalize_email(user.get("email", ""))
        user.setdefault("role", "viewer")
        users.append(user)
    return users


def _find_user(users: List[Dict[str, Any]], email: str) -> Optional[Dict[str, Any]]:
    em = _normalize_email(email)
    for u in users:
        if _normalize_email(u.get("email", "")) == em:
            return u
    return None


def login_user(users: List[Dict[str, Any]], email: str, password: str) -> Optional[Dict[str, Any]]:
    if not users:
        return None
    u = _find_user(users, email)
    if not u:
        return None

    stored_pw = u.get("password") or u.get("password_hash") or u.get("pass")
    if stored_pw is None:
        return None

    if not verify_password(password, stored_pw):
        return None

    token = create_session_token()
    expiry = datetime.now(timezone.utc) + timedelta(hours=8)

    result = {k: v for k, v in u.items() if k not in ("password", "password_hash", "pass")}
    result["session_token"] = token
    result["session_expiry"] = expiry.isoformat()
    return result


def validate_session(token: Optional[str], expiry: Optional[str]) -> bool:
    if not token or not expiry:
        return False
    # Accept either datetime objects or ISO strings
    if isinstance(expiry, datetime):
        exp = expiry
    else:
        try:
            exp = datetime.fromisoformat(str(expiry))
        except Exception:
            try:
                exp = datetime.fromisoformat(str(expiry).replace("Z", "+00:00"))
            except Exception:
                return False
    # Compare with matching awareness
    if exp.tzinfo is None:
        now = datetime.now()
    else:
        now = datetime.now(exp.tzinfo)
    return now < exp


def get_user_role(user: Dict[str, Any]) -> str:
    return (user or {}).get("role", "viewer")


def create_session_token() -> str:
    return secrets.token_urlsafe(32)


def logout_user(user: Dict[str, Any]) -> None:
    return