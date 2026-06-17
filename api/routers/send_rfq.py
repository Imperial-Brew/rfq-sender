"""
Send RFQ routes.

GET   /send-rfq/queue                  — queue items; ?include_sent=true returns all
GET   /send-rfq/vendors                — preview vendor matching (process + spec query params)
POST  /send-rfq/box/{part_number}      — create Box folder; optional multipart file uploads
PATCH /send-rfq/box-link/{part_number} — save a manually entered Box link to the queue
POST  /send-rfq/email/{part_number}    — create Outlook draft emails; marks item as sent
"""

import logging
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from api.deps import get_current_user
from utils.rfq_queue import load_queue, save_queue
from streamlit_app.utils.box_helpers import detect_cui_itar

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SendQueueItem(BaseModel):
    part_number: str
    process: str = ""
    spec: str = ""
    material: str = ""
    quantities: str = ""
    qt_so_number: str = ""
    cui_itar: str = ""
    rev: str = ""
    notes: str = ""
    file_location: str = ""
    sent: str = ""
    box_share_link: str = ""
    box_password: str = ""


class VendorMatch(BaseModel):
    name: str
    contact_name: str
    contact_email: str


class BoxRequest(BaseModel):
    access: str = "open"


class BoxResult(BaseModel):
    share_link: str = ""
    password: str = ""
    is_cui: bool = False
    files_uploaded: int = 0
    error: Optional[str] = None


class SaveLinkRequest(BaseModel):
    share_link: str = ""
    password: str = ""


class EmailRequest(BaseModel):
    share_link: str = ""
    password: str = ""


class EmailResult(BaseModel):
    vendor: str
    contact_email: str
    success: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_part_row(df: pd.DataFrame, part_number: str):
    """Return the first DataFrame row matching part_number, or raise 404."""
    col = next((c for c in df.columns if c.lower().strip() == "part_number"), None)
    if col is None:
        raise HTTPException(status_code=500, detail="Queue has no part_number column.")
    mask = df[col].astype(str).str.strip() == part_number.strip()
    if not mask.any():
        raise HTTPException(status_code=404, detail=f"'{part_number}' not found in queue.")
    return df[mask].iloc[0], df[mask].index[0]


def _get_vendor_manager():
    try:
        from core.vendors.vendor_manager import VendorManager
        return VendorManager()
    except Exception as e:
        logger.warning(f"Could not initialize VendorManager: {e}")
        return None


def _get_email_manager():
    try:
        from core.email.email_manager import EmailManager
        from core.config import Paths

        template_path = getattr(Paths, "EMAIL_TEMPLATE_PATH", None)
        if not template_path or not Path(str(template_path)).exists():
            # Fallback discovery
            root = Path(__file__).parent.parent.parent
            for candidate in [
                root / "templates" / "rfq_email_template.html",
                root / "config" / "templates" / "rfq_email_template.html",
                root / "config" / "templates" / "rfq_email.html",
            ]:
                if candidate.exists():
                    template_path = str(candidate)
                    break

        return EmailManager(template_path=str(template_path) if template_path else None)
    except Exception as e:
        logger.warning(f"Could not initialize EmailManager: {e}")
        return None


def _get_box():
    """Return a BoxIntegration instance or None."""
    try:
        from scripts.box.box_integration import BoxIntegration
        box = BoxIntegration()
        if not getattr(box, "client", None):
            return None
        return box
    except Exception as e:
        logger.warning(f"Box not available: {e}")
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/queue", response_model=List[SendQueueItem])
def get_unsent_queue(
    include_sent: bool = Query(False, description="If true, return all items including already-sent ones."),
    user: dict = Depends(get_current_user),
):
    df = load_queue()
    if df.empty:
        return []

    sent_col = next((c for c in df.columns if c.lower() == "sent"), None)
    if sent_col and not include_sent:
        df = df[df[sent_col].astype(str).str.strip().isin(["", "nan"])]

    # Convert datetime columns to strings before fillna (same fix as queue router)
    import pandas as _pd
    for col in df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
        df[col] = df[col].apply(lambda x: x.strftime("%Y-%m-%d") if _pd.notna(x) else "")

    records = df.fillna("").to_dict("records")
    result = []
    for r in records:
        result.append(SendQueueItem(
            part_number=str(r.get("part_number", "")),
            process=str(r.get("process", "")),
            spec=str(r.get("spec", "")),
            material=str(r.get("material", "")),
            quantities=str(r.get("quantities", "")),
            qt_so_number=str(r.get("qt/so #", r.get("qt_so_number", ""))),
            cui_itar=str(r.get("cui_itar", "")),
            rev=str(r.get("rev", "")),
            notes=str(r.get("notes", "")),
            file_location=str(r.get("file_location", "")),
            sent=str(r.get("sent", "")),
            box_share_link=str(r.get("box_share_link", "")),
            box_password=str(r.get("box_password", "")),
        ))
    return result


@router.get("/vendors", response_model=List[VendorMatch])
def preview_vendors(
    process: str = Query(...),
    spec: str = Query(""),
    user: dict = Depends(get_current_user),
):
    vm = _get_vendor_manager()
    if vm is None:
        raise HTTPException(status_code=503, detail="Vendor data not available.")

    vendors = vm.find_vendors_for_process_and_spec(process, spec or None)
    result = []
    for v in vendors:
        contact = vm.get_primary_contact(v)
        result.append(VendorMatch(
            name=v.name,
            contact_name=contact.name if contact else "",
            contact_email=contact.email if contact else "",
        ))
    return result


@router.post("/box/{part_number}", response_model=BoxResult)
async def create_box_folder(
    part_number: str,
    access: str = Form("open"),
    files: List[UploadFile] = File(default=[]),
    user: dict = Depends(get_current_user),
):
    """Create a Box folder for *part_number* and optionally upload files to it.

    Accepts ``multipart/form-data``:
    - ``access``  (string, default ``"open"``)
    - ``files``   (zero or more file uploads)

    If no files are provided the folder is still created and the queue's
    ``file_location`` path is scanned as a fallback.
    """
    df = load_queue()
    if df.empty:
        raise HTTPException(status_code=404, detail="Queue is empty.")

    row_series, row_idx = _find_part_row(df, part_number)

    box = _get_box()
    if box is None:
        return BoxResult(error="Box is not configured or could not connect.")

    try:
        from streamlit_app.utils.box_helpers import (
            upload_and_share_for_part, persist_box_update, get_rfq_files,
        )

        attachments: List[str] = []

        # 1. Files uploaded directly from the browser
        if files:
            with tempfile.TemporaryDirectory() as tmp:
                for uf in files:
                    dest = Path(tmp) / (uf.filename or "upload")
                    dest.write_bytes(await uf.read())
                    attachments.append(str(dest))
                logger.info("Box upload: %d browser file(s) for %s", len(attachments), part_number)
                result = upload_and_share_for_part(
                    box=box,
                    row=row_series,
                    attachments=attachments,
                    access=access,
                )
        else:
            # 2. Fallback: scan file_location from the queue row
            file_location = str(row_series.get("file_location", "") or "").strip()
            if file_location:
                attachments = get_rfq_files(file_location, part_number)
                if attachments:
                    logger.info("Box upload: found %d file(s) in %s", len(attachments), file_location)
            result = upload_and_share_for_part(
                box=box,
                row=row_series,
                attachments=attachments,
                access=access,
            )

    except Exception as e:
        logger.error(f"Box folder creation failed for {part_number}: {e}")
        return BoxResult(error=str(e))

    if "error" in result:
        return BoxResult(error=result["error"])

    # Persist Box metadata back to queue
    try:
        persist_box_update(
            df, row_idx,
            share_link=result.get("share_link", ""),
            password=result.get("password", ""),
            unshared_at=result.get("unshared_at", ""),
            files_uploaded=result.get("files_uploaded", 0),
            part_folder=result.get("part_folder"),
            quote_folder=result.get("quote_folder"),
            box=box,
        )
        save_queue(df)
    except Exception as e:
        logger.warning(f"Could not persist Box update to queue: {e}")

    return BoxResult(
        share_link=result.get("share_link", ""),
        password=result.get("password", ""),
        is_cui=bool(result.get("is_cui", False)),
        files_uploaded=int(result.get("files_uploaded", 0)),
    )


@router.patch("/box-link/{part_number}", response_model=BoxResult)
def save_box_link(
    part_number: str,
    body: SaveLinkRequest,
    user: dict = Depends(get_current_user),
):
    """Save a manually entered Box share link (and optional password) to the queue."""
    _bad = {'', 'nan', 'none', 'null'}
    share_link = body.share_link.strip() if body.share_link else ''
    if share_link.lower() in _bad:
        raise HTTPException(status_code=422, detail="share_link is required.")

    df = load_queue()
    if df.empty:
        raise HTTPException(status_code=404, detail="Queue is empty.")

    _, row_idx = _find_part_row(df, part_number)

    password = body.password.strip() if body.password else ''

    # Write directly — no Box API call needed
    df.loc[row_idx, 'box_share_link'] = share_link
    df.loc[row_idx, 'box_password'] = password
    try:
        save_queue(df)
    except Exception as e:
        logger.error(f"Could not save box link for {part_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Queue save failed: {e}")

    return BoxResult(share_link=share_link, password=password)


@router.post("/email/{part_number}", response_model=List[EmailResult])
def create_email_drafts(
    part_number: str,
    body: EmailRequest = EmailRequest(),
    user: dict = Depends(get_current_user),
):
    df = load_queue()
    if df.empty:
        raise HTTPException(status_code=404, detail="Queue is empty.")

    row_series, row_idx = _find_part_row(df, part_number)
    row_dict = row_series.to_dict()

    process = str(row_dict.get("process", "")).strip()
    spec = str(row_dict.get("spec", "")).strip()

    if not process:
        raise HTTPException(status_code=422, detail="Queue item has no process.")

    vm = _get_vendor_manager()
    if vm is None:
        raise HTTPException(status_code=503, detail="Vendor data not available.")

    vendors = vm.find_vendors_for_process_and_spec(process, spec or None)
    if not vendors:
        raise HTTPException(status_code=404, detail=f"No vendors found for process='{process}', spec='{spec}'.")

    em = _get_email_manager()
    if em is None:
        raise HTTPException(status_code=503, detail="Email manager could not be initialized.")

    # Resolve share link and password: prefer what was passed in the request body,
    # fall back to whatever is stored in the queue row.
    # Reject the literal string "nan" that pandas produces from NaN cells.
    _bad = {'', 'nan', 'none', 'null'}
    share_link = body.share_link.strip() if body.share_link else ''
    if share_link.lower() in _bad:
        share_link = str(row_dict.get("box_share_link", "")).strip()
    if share_link.lower() in _bad:
        share_link = ''

    box_password = body.password.strip() if body.password else ''
    if not box_password:
        box_password = str(row_dict.get("box_password", "")).strip()
    if box_password.lower() in _bad:
        box_password = ''

    is_cui_val = detect_cui_itar(row_series)

    results: List[EmailResult] = []
    any_success = False

    print(
        f"[ROUTE] create_email_drafts: part={part_number!r} vendors={len(vendors)}"
        f" upn={user.get('sub')!r} share_link={share_link!r}",
        flush=True,
    )

    for vendor in vendors:
        contact = vm.get_primary_contact(vendor)
        if not contact or not contact.email:
            results.append(EmailResult(
                vendor=vendor.name,
                contact_email="",
                success=False,
                error="No contact email found.",
            ))
            continue

        print(f"[ROUTE] building email for vendor={vendor.name!r} contact={contact.email!r}", flush=True)
        try:
            recipient, subject, html_body = em.create_rfq_email(
                queue_item=row_series,
                vendor={"name": vendor.name},
                contact={"name": contact.name, "email": contact.email},
                box_link=share_link,
                box_password=box_password,
                is_cui=is_cui_val,
            )
        except Exception as e:
            print(f"[ROUTE] create_rfq_email FAILED for {vendor.name!r}: {type(e).__name__}: {e}", flush=True)
            results.append(EmailResult(
                vendor=vendor.name,
                contact_email=contact.email,
                success=False,
                error=f"Template render failed: {e}",
            ))
            continue

        print(f"[ROUTE] rfq_email built ok, calling create_draft_email to={recipient!r}", flush=True)
        success = em.create_draft_email(
            recipient=recipient,
            subject=subject,
            body=html_body,
            user_upn=user.get("sub"),
        )
        results.append(EmailResult(
            vendor=vendor.name,
            contact_email=recipient,
            success=success,
            error=None if success else "Graph draft creation failed (check logs).",
        ))
        if success:
            any_success = True
            # CUI/ITAR: send the Box folder password in a separate email so
            # it is never in the same message as the folder link.
            if box_password:
                pw_subject = f"Box Folder Password – {part_number}"
                pw_body = (
                    f"<p>The password for the RFQ Box folder for part "
                    f"<strong>{part_number}</strong> is:</p>"
                    f"<p><code style=\"font-size:16px;\">{box_password}</code></p>"
                    f"<p>Please use this password to access the folder shared in the "
                    f"accompanying RFQ email.</p>"
                )
                print(f"[ROUTE] sending password draft to={recipient!r}", flush=True)
                em.create_draft_email(
                    recipient=recipient,
                    subject=pw_subject,
                    body=pw_body,
                    user_upn=user.get("sub"),
                )

    # Mark item as sent today if at least one draft was created.
    # Reload from the store immediately before saving to minimise the window
    # for ETag conflicts (another request could have written in the meantime).
    if any_success:
        try:
            fresh_df = load_queue()
            part_col = next((c for c in fresh_df.columns if c.lower().strip() == "part_number"), None)
            sent_col = next((c for c in fresh_df.columns if c.lower() == "sent"), "sent")
            if part_col is not None:
                mask = fresh_df[part_col].astype(str).str.strip() == part_number.strip()
                fresh_df.loc[mask, sent_col] = date.today().isoformat()
            save_queue(fresh_df)
        except Exception as e:
            logger.warning(f"Could not mark item as sent: {e}")

    return results
