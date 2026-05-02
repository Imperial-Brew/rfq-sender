"""
FastAPI "dependencies" — reusable functions that routes declare they need.

The pattern looks like this in a route:

    @router.get("/queue")
    def get_queue(user = Depends(get_current_user)):
        ...

FastAPI sees `Depends(get_current_user)`, calls that function automatically
before running get_queue, and passes the return value in as `user`.
If get_current_user raises an HTTPException, FastAPI returns that error
instead of running the route at all. This is how auth works throughout the app.
"""

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

# HTTPBearer tells FastAPI to look for an Authorization: Bearer <token> header.
# Without this, routes wouldn't know where to find the token.
_bearer = HTTPBearer()

# The secret key is used to sign and verify JWTs.
# A JWT is signed with this key — if someone tampers with the token,
# the signature won't match and jwt.decode() will raise an error.
# NEVER hardcode this in production — always use an environment variable.
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-before-deploying")
ALGORITHM = "HS256"


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    Decodes the JWT from the Authorization header.
    Returns the payload dict: {"sub": email, "name": ..., "role": ..., "exp": ...}
    Raises 401 if the token is missing, invalid, or expired.
    """
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Role hierarchy: higher number = more permissions
_ROLE_RANK = {"viewer": 0, "estimator": 1, "admin": 2}


def require_role(minimum_role: str):
    """
    Returns a dependency that enforces a minimum role.

    Usage in a route:
        @router.delete("/{id}")
        def delete_item(user = Depends(require_role("admin"))):
            ...

    This is a "dependency factory" — a function that returns a dependency.
    The extra layer is needed because Depends() can't accept arguments directly.
    """
    def _check(user: dict = Depends(get_current_user)) -> dict:
        user_rank = _ROLE_RANK.get(user.get("role", "viewer"), 0)
        required_rank = _ROLE_RANK.get(minimum_role, 999)
        if user_rank < required_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires the '{minimum_role}' role.",
            )
        return user

    return _check
