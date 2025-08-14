# core/email/graph_client.py
from __future__ import annotations
import base64, os, time, requests, logging
from typing import List, Optional, Dict, Any
from core.secrets import get_section

log = logging.getLogger(__name__)
GRAPH = "https://graph.microsoft.com/v1.0"
_TOKEN: Optional[str] = None
_TOKEN_EXP: float = 0.0


def _azure_cfg() -> Dict[str, str]:
    az = dict(get_section("azure"))  # Streamlit secrets if present
    if not az:  # env fallback for pytest/CLI
        az = {
            "tenant_id": os.getenv("AZURE_TENANT_ID", ""),
            "client_id": os.getenv("AZURE_CLIENT_ID", ""),
            "client_secret": os.getenv("AZURE_CLIENT_SECRET", ""),
        }
    missing = [k for k in ("tenant_id","client_id","client_secret") if not az.get(k)]
    if missing:
        raise RuntimeError(f"Missing Azure settings: {', '.join(missing)}")
    return az

def _get_token() -> str:
    global _TOKEN, _TOKEN_EXP
    now = time.time()
    if _TOKEN and now < _TOKEN_EXP - 60:
        return _TOKEN

    az = _azure_cfg()
    data = {
        "client_id": az["client_id"],
        "client_secret": az["client_secret"],
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    url = f"https://login.microsoftonline.com/{az['tenant_id']}/oauth2/v2.0/token"
    # hard timeout; fail fast
    r = requests.post(url, data=data, timeout=20)
    r.raise_for_status()
    payload = r.json()
    _TOKEN = payload["access_token"]
    _TOKEN_EXP = now + int(payload.get("expires_in", 3600))
    return _TOKEN

def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {_get_token()}"}

def _addr(email: str) -> Dict[str, Any]:
    return {"emailAddress": {"address": email}}

def create_draft(user_upn: str, subject: str, html_body: str, to: List[str], cc: Optional[List[str]] = None) -> str:
    headers = {**_auth_headers(), "Content-Type": "application/json"}
    payload = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": html_body},
        "toRecipients": [_addr(x) for x in to],
    }
    if cc:
        payload["ccRecipients"] = [_addr(x) for x in cc]
    r = requests.post(f"{GRAPH}/users/{user_upn}/messages", headers=headers, json=payload, timeout=25)
    r.raise_for_status()
    return r.json()["id"]

def add_file_attachment(user_upn: str, message_id: str, path: str) -> None:
    # Graph small fileAttachment limit ~3MB; use upload session above that
    if os.path.getsize(path) <= 3 * 1024 * 1024:
        _add_small_attachment(user_upn, message_id, path)
    else:
        _add_large_attachment(user_upn, message_id, path)
