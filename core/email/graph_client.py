# core/email/graph_client.py
from __future__ import annotations
from core.secrets import get_section
import base64, os, time, requests, logging
from typing import List, Optional, Dict, Any

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
        log.debug("Graph token cache hit (expires in %.0fs)", _TOKEN_EXP - now)
        return _TOKEN

    az = _azure_cfg()
    log.info("Acquiring new Graph token for tenant=%s client=%s",
             az.get("tenant_id", "?")[:8] + "…", az.get("client_id", "?")[:8] + "…")
    data = {
        "client_id": az["client_id"],
        "client_secret": az["client_secret"],
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    url = f"https://login.microsoftonline.com/{az['tenant_id']}/oauth2/v2.0/token"
    # hard timeout; fail fast
    r = requests.post(url, data=data, timeout=20)
    if not r.ok:
        log.error("Graph token request failed: %s %s", r.status_code, r.text[:300])
    r.raise_for_status()
    payload = r.json()
    _TOKEN = payload["access_token"]
    _TOKEN_EXP = now + int(payload.get("expires_in", 3600))
    log.info("Graph token acquired OK (expires_in=%s)", payload.get("expires_in"))
    return _TOKEN

def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {_get_token()}"}

def _addr(email: str) -> Dict[str, Any]:
    return {"emailAddress": {"address": email}}

def create_draft(
    user_upn: str,
    subject: str,
    html_body: str,
    to: List[str],
    cc: Optional[List[str]] = None,
    inline_images: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Create an Outlook draft via Graph API.

    ``inline_images`` is a list of Graph fileAttachment dicts with
    ``isInline=True`` and a ``contentId`` that matches a ``cid:`` reference
    in ``html_body``.  Pass ``None`` (default) to skip attachments.
    """
    headers = {**_auth_headers(), "Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": html_body},
        "toRecipients": [_addr(x) for x in to],
    }
    if cc:
        payload["ccRecipients"] = [_addr(x) for x in cc]
    if inline_images:
        payload["attachments"] = inline_images
    url = f"{GRAPH}/users/{user_upn}/messages"
    log.info("POST %s  to=%s  subject=%r  inline_images=%d",
             url, to, subject, len(inline_images or []))
    r = requests.post(url, headers=headers, json=payload, timeout=25)
    if not r.ok:
        log.error("Graph create_draft failed: %s %s", r.status_code, r.text[:500])
    r.raise_for_status()
    msg_id = r.json().get("id", "<no id>")
    log.info("Draft created: %s", msg_id)
    return msg_id

def add_file_attachment(user_upn: str, message_id: str, path: str) -> None:
    # Graph small fileAttachment limit ~3MB; use upload session above that
    if os.path.getsize(path) <= 3 * 1024 * 1024:
        _add_small_attachment(user_upn, message_id, path)
    else:
        _add_large_attachment(user_upn, message_id, path)

def _add_small_attachment(user_upn: str, message_id: str, path: str) -> None:
    headers = {**_auth_headers(), "Content-Type": "application/json"}
    with open(path, "rb") as f:
        content_bytes = f.read()
    payload = {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": os.path.basename(path),
        "contentBytes": base64.b64encode(content_bytes).decode("ascii"),
        "contentType": _guess_mime(path),
    }
    url = f"{GRAPH}/users/{user_upn}/messages/{message_id}/attachments"
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()

def _add_large_attachment(user_upn: str, message_id: str, path: str) -> None:
    # Create upload session
    headers = _auth_headers()
    url = f"{GRAPH}/users/{user_upn}/messages/{message_id}/attachments/createUploadSession"
    payload = {"AttachmentItem": {
        "attachmentType": "file",
        "name": os.path.basename(path),
        "size": os.path.getsize(path),
        "contentType": _guess_mime(path),
    }}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    upload_url = r.json()["uploadUrl"]

    # Chunked upload (e.g., 5 MB chunks)
    chunk_size = 5 * 1024 * 1024
    total = os.path.getsize(path)
    with open(path, "rb") as f:
        start = 0
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            end = start + len(data) - 1
            headers = {
                "Content-Length": str(len(data)),
                "Content-Range": f"bytes {start}-{end}/{total}",
            }
            rr = requests.put(upload_url, headers=headers, data=data, timeout=120)
            # 200/201/202 are OK during upload session
            if rr.status_code not in (200, 201, 202):
                rr.raise_for_status()
            start = end + 1

def _guess_mime(path: str) -> str:
    # Minimal mapping; extend if needed
    ext = os.path.splitext(path)[1].lower()
    return {
        ".pdf": "application/pdf",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(ext, "application/octet-stream")