from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# External Box integration
from scripts.box.box_integration import BoxIntegration

import secrets
import string


def detect_cui_itar(row: pd.Series) -> bool:
    """Return True if the queue row is marked as CUI or ITAR.

    Check order:
    1. Explicit ``cui_itar`` column value:
       - Boolean True/False → returned directly
       - "TRUE"/"YES"/"Y"/"1"/"CUI"/"ITAR" → True
       - "FALSE"/"NO"/"N"/"0"/"" → False
       - Anything else → fall through to heuristic scan
    2. Keyword scan of cui_itar + spec + process + callout + material for
       the strings "CUI" or "ITAR".
    """
    try:
        flag = row.get('cui_itar', None)
        # Treat NaN / NaT as absent
        try:
            if pd.isna(flag):
                flag = None
        except (TypeError, ValueError):
            pass

        if flag is not None:
            if isinstance(flag, bool):
                return bool(flag)
            s = str(flag).strip().upper()
            # Explicit true values — including the literal strings CUI / ITAR
            if s in ("TRUE", "YES", "Y", "1", "CUI", "ITAR", "CUI/ITAR"):
                return True
            # Explicit false values
            if s in ("FALSE", "NO", "N", "0", ""):
                return False
            # Otherwise fall through to keyword scan below
    except Exception:
        pass

    # Heuristic: scan cui_itar itself plus related fields for the keywords
    fields_to_scan = [
        str(row.get('cui_itar', '')),
        str(row.get('spec', '')),
        str(row.get('process', '')),
        str(row.get('callout', '')),
        str(row.get('material', '')),
    ]
    text = " ".join(fields_to_scan).upper()
    return ("CUI" in text) or ("ITAR" in text)


def generate_password(length: int = 14) -> str:
    """Generate a random, email-friendly password."""
    alphabet = string.ascii_letters + string.digits + "-_@#"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_rfq_part_folder(box: "BoxIntegration", qt_so: str, part_number: str):
    """
    Ensure Box folders exist for 'RFQs/[qt/so #]/[Part_Number]'.
    Returns (rfqs_root, quote_folder, part_folder) or (None, None, None) on failure.
    """
    rfqs_root = box.create_folder("RFQs", parent_folder_id="0")
    if not rfqs_root:
        return None, None, None

    quote_name = str(qt_so).strip() if qt_so else str(part_number).strip()
    quote_folder = box.create_folder(quote_name, parent_folder_id=rfqs_root.id)
    if not quote_folder:
        return rfqs_root, None, None

    part_folder = box.create_folder(str(part_number).strip(), parent_folder_id=quote_folder.id)
    if not part_folder:
        return rfqs_root, quote_folder, None

    return rfqs_root, quote_folder, part_folder


def upload_and_share_for_part(
    box: "BoxIntegration",
    row: pd.Series,
    attachments: List[str],
    access: str = "open",
    default_expire_days: int = 30,
):
    """
    - Creates RFQs/[qt/so #]/[Part_Number]
    - Uploads attachments to the part folder
    - Counts actual files in the Box part folder (authoritative)
    - Detects CUI/ITAR to optionally add password protection
    - Returns a dict with: share_link, password, is_cui, part_folder, quote_folder, rfqs_root,
      files_uploaded, unshared_at
    """
    qt_so = row.get("qt/so #", "")
    part_number = row.get("part_number", "")
    if not part_number:
        return {"error": "Missing part_number"}

    rfqs_root, quote_folder, part_folder = ensure_rfq_part_folder(box, qt_so, part_number)
    if not part_folder:
        return {"error": f"Failed to prepare Box folder for {part_number}"}

    # 1) Upload files (if any)
    if attachments:
        try:
            box.upload_files(attachments, part_folder)
        except Exception as e:
            # Continue; we'll still try to count folder contents
            try:
                import logging
                logging.getLogger(__name__).warning(
                    f"Upload failed for some files in {part_number}: {e}")
            except Exception:
                pass

    # 2) Authoritative count from Box (with pagination-safe iteration)
    files_uploaded = 0
    try:
        items = box.client.folder(part_folder.id).get_items(limit=1000)
        files_uploaded = sum(1 for it in items if getattr(it, 'type', '') == 'file')
    except Exception:
        files_uploaded = len(attachments or [])

    # 3) Decide protection and create share link
    is_cui = detect_cui_itar(row)
    password = generate_password() if is_cui else None

    # Compute expiration timestamp for recording (intended expiry)
    unshared_at = None
    if default_expire_days and default_expire_days > 0:
        unshared_at = (datetime.now() + timedelta(days=default_expire_days)).isoformat()

    share_link = box.create_share_link(
        part_folder,
        access=access,
        password=password,
        expire_days=default_expire_days,
    )

    return {
        "share_link": share_link or "",
        "password": password or "",
        "is_cui": is_cui,
        "part_folder": part_folder,
        "quote_folder": quote_folder,
        "rfqs_root": rfqs_root,
        "files_uploaded": files_uploaded,
        "unshared_at": unshared_at or "",
    }


def get_rfq_files(file_location: str, part_number: str) -> List[str]:
    """Scan *file_location* for files that belong to *part_number*.

    Tries progressively looser glob patterns so typos and mixed-case
    filenames are still found:
      1. ``*{part_number}*``  (exact part number anywhere in filename)
      2. All files if the directory has ≤ 20 items and pattern 1 matched nothing

    Returns a deduplicated, sorted list of absolute file paths.
    Skips hidden files (``.*``) and Office temp files (``~$*``).
    """
    import logging
    from pathlib import Path as _Path

    _log = logging.getLogger(__name__)

    _bad = {'', 'nan', 'none', 'null'}
    if not file_location or str(file_location).strip().lower() in _bad:
        return []

    loc = _Path(str(file_location).strip())
    if not loc.exists():
        _log.warning("file_location does not exist: %s", loc)
        return []

    # Single file — return it directly.
    if loc.is_file():
        return [str(loc)]

    def _skip(p: _Path) -> bool:
        return p.name.startswith('.') or p.name.startswith('~$')

    # Recursive glob for part number pattern
    pn = str(part_number).strip()
    found: List[str] = []
    for p in loc.rglob(f"*{pn}*"):
        if p.is_file() and not _skip(p):
            found.append(str(p))

    # Fallback: if nothing matched and the folder is small, take everything
    if not found:
        all_files = [str(p) for p in loc.rglob("*") if p.is_file() and not _skip(p)]
        if len(all_files) <= 20:
            found = all_files
        else:
            _log.warning(
                "No files matched part_number=%r in %s and folder has >20 files — skipping",
                pn, loc,
            )

    return sorted(set(found))


def inject_box_link_into_body(html_body: str, share_link: str, is_cui: bool) -> str:
    """Append a styled Box link section to the existing HTML email body.

    Note: the FastAPI stack passes box_link to the Jinja template instead of
    calling this function.  This helper is kept for the legacy Streamlit path.
    """
    # Reject empty strings and the literal "nan" that pandas produces for NaN cells.
    _bad = {'', 'nan', 'none', 'null'}
    if not share_link or share_link.strip().lower() in _bad:
        return html_body
    share_link = share_link.strip()

    banner = f"""
    <div style=\"margin-top:16px;padding:14px;border:1px solid #d0d7de;border-radius:8px;background:#f6f8fa;\">
      <div style=\"font-size:16px;font-weight:600;margin-bottom:6px;\">
        RFQ Files in Box { '(Password Protected)' if is_cui else '' }
      </div>
      <div>
        <a href=\"{share_link}\" style=\"display:inline-block;padding:10px 14px;background:#2d7ff9;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;\">
          Open RFQ Folder
        </a>
      </div>
      <div style=\"margin-top:8px;color:#57606a;font-size:13px;\">
        If you have trouble opening the link, copy and paste this URL into your browser:<br/>
        <code style=\"font-size:12px;\">{share_link}</code>
      </div>
    </div>
    """
    updated = html_body
    if "</body>" in html_body:
        updated = html_body.replace("</body>", banner + "\n</body>")
    elif "</html>" in html_body:
        updated = html_body.replace("</html>", banner + "\n</html>")
    else:
        updated = html_body + banner
    return updated


def persist_box_update(
    queue: pd.DataFrame,
    row_index,
    *,
    share_link: Optional[str] = None,
    password: Optional[str] = None,
    unshared_at: Optional[str] = None,
    files_uploaded: Optional[int] = None,
    part_folder=None,
    quote_folder=None,
    box: Optional[BoxIntegration] = None,
    create_quote_link: bool = True,
) -> None:
    """
    Persist Box-related fields for a single row, following the newer schema.
    - Writes box_rfq_folder (open link, no password) if quote_folder provided.
    - Writes part-folder id, share_link, password, unshared_at, last_updated, files_uploaded.
    - Does NOT write deprecated columns (box_access, file_manifest, box_rfq_root_id).
    """
    # Quote-level open link (no password, no expiry)
    if create_quote_link and quote_folder is not None and box is not None:
        try:
            quote_share_link = box.create_share_link(
                quote_folder,
                access="open",
                password=None,
                expire_days=None,
            )
        except Exception:
            quote_share_link = None
        queue.loc[row_index, 'box_rfq_folder'] = quote_share_link or ''

    # Part folder id (retain if useful)
    if part_folder is not None:
        queue.loc[row_index, 'box_part_folder_id'] = getattr(part_folder, 'id', '')

    # Main share link (part folder)
    if share_link is not None:
        queue.loc[row_index, 'box_share_link'] = share_link or ''

    # Password and link metadata
    if password is not None:
        queue.loc[row_index, 'box_password'] = password or ''

    if unshared_at is not None:
        queue.loc[row_index, 'box_unshared_at'] = unshared_at or ''

    # Timestamp
    queue.loc[row_index, 'box_last_updated'] = datetime.now().isoformat()

    # Files uploaded (count provided by caller)
    if files_uploaded is not None:
        queue.loc[row_index, 'files_uploaded'] = int(files_uploaded)
