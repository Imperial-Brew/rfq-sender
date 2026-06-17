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
    process: Optional[str] = None
    access: str = "open"


class BoxResult(BaseModel):
    share_link: str = ""
    password: str = ""
    is_cui: bool = False
    files_uploaded: int = 0
    error: Optional[str] = None


class SaveLinkRequest(BaseModel):
    process: Optional[str] = None
    share_link: str = ""
    password: str = ""


class EmailRequest(BaseModel):
    process: Optional[str] = None
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

def _find_part_row(df: pd.DataFrame, part_number: str, process: Optional[str] = None):
    """Return the DataFrame row matching part_number (and optionally process), or raise 404."""
    col_part = next((c for c in df.columns if c.lower().strip() == "part_number"), None)
    if col_part is None:
        raise HTTPException(status_code=500, detail="Queue has no part_number column.")
    
    # Standardize types and whitespace for matching
    df_part = df[col_part].astype(str).str.strip()
    target_part = str(part_number).strip()
    
    mask = df_part == target_part
    
    if process:
        col_proc = next((c for c in df.columns if c.lower().strip() == "process"), None)
        if col_proc:
            df_proc = df[col_proc].astype(str).str.strip()
            target_proc = str(process).strip()
            mask = mask & (df_proc == target_proc)
    
    logger.info(f"[_find_part_row] Finding part={target_part!r} process={process!r}. Matches found: {mask.sum()}")
    
    if mask.sum() > 1:
        # If we have multiple matches even WITH process, or if no process was provided
        # and there are multiple parts with same number, log it.
        logger.warning(f"[_find_part_row] Multiple matches ({mask.sum()}) for part={target_part!r} process={process!r}. Using first.")

    if not mask.any():
        detail = f"'{part_number}'" + (f" with process '{process}'" if process else "") + " not found in queue."
        raise HTTPException(status_code=404, detail=detail)
    
    # If multiple matches exist and process was provided, we've already filtered by it.
    # If no process was provided and multiple matches exist, it picks the first one (original behavior).
    idx = df.index[mask][0]
    logger.info(f"[_find_part_row] Selected row index: {idx}")
    return df[mask].iloc[0], idx


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
    process: Optional[str] = Form(None),
    access: str = Form("open"),
    files: List[UploadFile] = File(default=[]),
    user: dict = Depends(get_current_user),
):
    """Create a Box folder for *part_number* and optionally upload files to it.

    Accepts ``multipart/form-data``:
    - ``process`` (string, optional)
    - ``access``  (string, default ``"open"``)
    - ``files``   (zero or more file uploads)

    If no files are provided the folder is still created and the queue's
    ``file_location`` path is scanned as a fallback.
    """
    df = load_queue()
    if df.empty:
        raise HTTPException(status_code=404, detail="Queue is empty.")

    row_series, row_idx = _find_part_row(df, part_number, process=process)

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

    # Persist Box metadata back to queue.
    # The Box folder is per-part (not per-process), so write the share link and
    # password to ALL rows with this part_number so every process line can see it.
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
        # Propagate share link / password to any sibling rows (same part, different process)
        part_col = next((c for c in df.columns if c.lower().strip() == "part_number"), None)
        share_link_val = result.get("share_link", "")
        password_val = result.get("password", "")
        if part_col and share_link_val:
            sibling_mask = (df[part_col].astype(str).str.strip() == str(part_number).strip()) & (df.index != row_idx)
            df.loc[sibling_mask, 'box_share_link'] = share_link_val
            if password_val:
                df.loc[sibling_mask, 'box_password'] = password_val
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

    _, row_idx = _find_part_row(df, part_number, process=body.process)

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

    # We must have a process to distinguish between duplicates.
    # If not in body, try to get it from the queue if there's only one match,
    # but that defeats the purpose. So we prefer it being in the body.
    process_param = body.process
    if not process_param:
        logger.warning(f"No process provided in request body for {part_number}. Falling back to first match.")

    row_series, row_idx = _find_part_row(df, part_number, process=process_param)
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
    share_link = (body.share_link or '').strip()
    if share_link.lower() in _bad:
        share_link = str(row_dict.get("box_share_link", "")).strip()
    if share_link.lower() in _bad:
        share_link = ''

    # We MUST ensure box_password is recovered even if not in the body
    box_password = (body.password or '').strip()
    if not box_password or box_password.lower() in _bad:
        box_password = str(row_dict.get("box_password", "")).strip()
    
    if box_password.lower() in _bad:
        box_password = ''

    is_cui_val = detect_cui_itar(row_series)

    # Auto-fix missing password for CUI/ITAR
    if is_cui_val and not box_password and share_link:
        logger.info(f"CUI/ITAR detected for {part_number} but no password found. Attempting to auto-generate and update Box.")
        try:
            from streamlit_app.utils.box_helpers import generate_password
            box = _get_box()
            folder_id = str(row_dict.get("box_part_folder_id", "")).strip()
            
            if box and folder_id:
                new_password = generate_password()
                # Re-create share link with password (Box API updates existing link)
                updated_link = box.create_share_link(
                    folder=box.client.folder(folder_id).get(),
                    access="open",
                    password=new_password,
                    expire_days=30
                )
                if updated_link:
                    box_password = new_password
                    share_link = updated_link
                    # Persist to queue
                    df.loc[row_idx, 'box_password'] = box_password
                    df.loc[row_idx, 'box_share_link'] = share_link
                    save_queue(df)
                    logger.info(f"Successfully auto-generated password and updated Box for {part_number}")
                else:
                    logger.warning(f"Failed to update Box share link with password for {part_number}")
            else:
                logger.warning(f"Box integration or folder ID missing for {part_number}, cannot auto-fix password.")
        except Exception as e:
            logger.error(f"Error during auto-password generation for {part_number}: {e}")

    results: List[EmailResult] = []
    any_success = False

    print(
        f"[ROUTE] create_email_drafts: part={part_number!r} process_param={body.process!r} vendors={len(vendors)}"
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
            # LOGIC: we only send the second email if box_password is not empty.
            if box_password:
                pw_subject = f"Box Folder Password – {part_number}"
                pw_body = (
                    f"<p>The password for the RFQ Box folder for part "
                    f"<strong>{part_number}</strong> is:</p>"
                    f"<p><code style=\"font-size:16px;\">{box_password}</code></p>"
                    f"<p>Please use this password to access the folder shared in the "
                    f"accompanying RFQ email.</p>"
                )
                print(f"[ROUTE] sending password draft to={recipient!r} password={box_password!r} is_cui={is_cui_val}", flush=True)
                pw_success = em.create_draft_email(
                    recipient=recipient,
                    subject=pw_subject,
                    body=pw_body,
                    user_upn=user.get("sub"),
                )
                if not pw_success:
                    logger.error(f"Failed to create password draft for {vendor.name} ({recipient})")
            elif is_cui_val:
                logger.warning(f"CUI/ITAR detected but NO password found for {part_number!r}")

    # Mark item as sent today if at least one draft was created.
    # Reload from the store immediately before saving to minimise the window
    # for ETag conflicts (another request could have written in the meantime).
    if any_success:
        try:
            fresh_df = load_queue()
            part_col = next((c for c in fresh_df.columns if c.lower().strip() == "part_number"), None)
            proc_col = next((c for c in fresh_df.columns if c.lower().strip() == "process"), None)
            sent_col = next((c for c in fresh_df.columns if c.lower() == "sent"), "sent")
            if part_col is not None:
                mask = fresh_df[part_col].astype(str).str.strip() == part_number.strip()
                if proc_col is not None and process:
                    mask = mask & (fresh_df[proc_col].astype(str).str.strip() == process.strip())
                fresh_df.loc[mask, sent_col] = date.today().isoformat()
            save_queue(fresh_df)
        except Exception as e:
            logger.warning(f"Could not mark item as sent: {e}")

    return results
