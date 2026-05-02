"""
Authentication routes.

POST /auth/login  — validates credentials, returns a JWT
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from pydantic import BaseModel

from utils.auth import load_users, login_user
from api.deps import SECRET_KEY, ALGORITHM

router = APIRouter()

USERS_FILE = os.environ.get("USERS_FILE", "users.yaml")


# Pydantic models define the shape of request and response bodies.
# FastAPI uses them to:
#   1. Validate incoming JSON (wrong types → automatic 422 error)
#   2. Generate API documentation (visible at /docs when the server runs)
#   3. Serialize outgoing data to JSON

class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    email: str
    name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """
    Authenticates against the same users.yaml used by Streamlit.
    No migration needed — same passwords, same file.

    On success, returns a JWT (JSON Web Token).

    JWT vs. the old session_token approach:
    - Old way: server creates a random token, stores it somewhere, looks it up on each request
    - JWT way: server encodes the user's data INTO the token and signs it with a secret key.
      Any request can be verified by checking the signature — no storage needed.
      The user's email, name, role, and expiry are all baked into the token itself.
    """
    try:
        users = load_users(USERS_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="users.yaml not found.")

    user = login_user(users, body.email, body.password)
    if not user:
        # Always return the same error for wrong email OR wrong password.
        # Specific errors ("email not found" vs "wrong password") help attackers
        # enumerate valid accounts — a vague message is intentionally safer.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    payload = {
        "sub": user["email"],       # "sub" = subject, the standard JWT field for "who is this for"
        "name": user.get("name", ""),
        "role": user.get("role", "viewer"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return TokenResponse(
        access_token=token,
        user=UserOut(
            email=user["email"],
            name=user.get("name", ""),
            role=user.get("role", "viewer"),
        ),
    )
