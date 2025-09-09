import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import tempfile
import mimetypes
from datetime import timezone
from email import policy
from email.parser import BytesParser
import re

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from streamlit_app.utils.auth_middleware import require_authentication
from streamlit_app.utils.auth_shim import get_user_role
from utils.rfq_logging import get_logger
from utils.rfq_tracking import get_tracker
from io import BytesIO
from boxsdk.exception import BoxAPIException
from streamlit_app.utils.box_client import get_box_client
from datetime import datetime, timedelta

# Require authentication for this page
if not require_authentication():
    st.stop()

# Logger
logger = get_logger(__name__)

# Build info to make changes visible in UI
BUILD_INFO = "RFQ Responses — Email attachments: extract and preview/download from EML/MSG; plus prior Box move fixes (2025-09-02 11:42)"


def setup_page():
    st.title("RFQ Responses")
    st.markdown(
        """
        View rfq_responses.csv. If Box is configured in secrets, the data is loaded from Box.
        Use the Refresh button to re-load from Box. You can also download the current view as CSV.
        """
    )
    st.caption(BUILD_INFO)


def _load_responses_df():
    """Load rfq_responses.csv via RFQTracking (Box if configured, else local fallback)."""
    tracker = get_tracker()
    try:
        # Ensure the responses file exists (creates in Box if configured, else local)
        tracker.ensure_responses_file()
    except Exception as e:
        logger.warning(f"ensure_responses_file failed: {e}")

    # Prefer Box store if available
    try:
        if tracker.responses_store is not None:
            df = tracker.responses_store.load_df()
            return df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    except Exception as e:
        logger.warning(f"Failed loading responses from Box; will try local. Err: {e}")

    # Local fallback
    try:
        return pd.read_csv(tracker.responses_path) if tracker.responses_path.exists() else pd.DataFrame()
    except Exception as e:
        logger.error(f"Failed loading local rfq_responses.csv: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_responses_df() -> pd.DataFrame:
    """Cached loader for rfq_responses.csv using Box if available.

    Returns:
        pd.DataFrame: The current responses table.
    """
    return _load_responses_df()


def save_responses_df(df: pd.DataFrame) -> None:
    """Persist responses DataFrame and clear cached reads.

    This writes to Box when configured (via tracker.responses_store),
    otherwise saves to the local path. After saving, the cached loader
    is invalidated so the UI shows the latest data.

    Args:
        df: Responses dataframe to persist.
    """
    tracker = get_tracker()
    try:
        if getattr(tracker, "responses_store", None) is not None:
            tracker.responses_store.save_df(df)
        else:
            try:
                tracker.ensure_responses_file()
            except Exception:
                pass
            df.to_csv(tracker.responses_path, index=False)
    except BoxAPIException as e:
        logger.error(f"Failed to save responses to Box: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to save responses: {e}")
        raise
    finally:
        try:
            load_responses_df.clear()  # invalidate cache
        except Exception:
            pass


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the actual column name in df matching any of candidate names (case-insensitive)."""
    if df is None or df.empty:
        return None
    cols = {c.strip().lower(): c for c in df.columns}
    for name in candidates:
        key = str(name).strip().lower()
        if key in cols:
            return cols[key]
    return None

def _now_utc_iso():
    try:
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return datetime.utcnow().isoformat() + "Z"

def _detect_filetype(name: str, default: str = "application/octet-stream") -> tuple[str, str]:
    try:
        mime, _ = mimetypes.guess_type(name)
        ext = ""
        if "." in name:
            ext = name.rsplit(".", 1)[-1].lower().strip()
        return (ext, mime or default)
    except Exception:
        return ("", default)

def _download_box_file_bytes(client, file_id: str) -> bytes:
    try:
        return client.file(file_id).content()
    except Exception as e:
        raise RuntimeError(f"Failed to download file content from Box: {e}")

def _safe_preview_text(txt: str, limit: int = 100000) -> str:
    if not txt:
        return ""
    return txt if len(txt) <= limit else txt[:limit] + " …"

def _try_parse_eml(content: bytes) -> dict:
    try:
        msg = BytesParser(policy=policy.default).parsebytes(content)
        subject = msg.get("subject", "")
        sender = msg.get("from", "")
        to = msg.get("to", "")
        date = msg.get("date", "")
        body = ""
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                cdispo = str(part.get_content_disposition() or "").lower()
                if part.get_content_type() == "text/plain" and not cdispo == "attachment":
                    try:
                        body = part.get_content()
                    except Exception:
                        try:
                            body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                        except Exception:
                            pass
                elif cdispo == "attachment":
                    fname = part.get_filename() or "attachment"
                    try:
                        data = part.get_payload(decode=True) or b""
                    except Exception:
                        data = b""
                    attachments.append({
                        "filename": fname,
                        "content_type": part.get_content_type() or "application/octet-stream",
                        "data": data,
                        "size": len(data) if isinstance(data, (bytes, bytearray)) else 0,
                    })
        else:
            if msg.get_content_type() == "text/plain":
                try:
                    body = msg.get_content()
                except Exception:
                    try:
                        body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
                    except Exception:
                        body = ""
        return {"subject": subject or "", "from": sender or "", "to": to or "", "date": date or "", "body": body or "", "attachments": attachments}
    except Exception as e:
        return {"error": f"EML parse failed: {e}"}

def _try_parse_msg(content: bytes) -> dict:
    try:
        import extract_msg  # optional dependency
    except Exception:
        return {"error": "MSG parsing requires 'extract-msg'. Add to requirements and install."}
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".msg") as tf:
            tf.write(content)
            tmp_path = tf.name
        msg = extract_msg.Message(tmp_path)
        atts = []
        try:
            for a in msg.attachments or []:
                try:
                    fname = getattr(a, 'longFilename', None) or getattr(a, 'shortFilename', None) or getattr(a, 'filename', None) or 'attachment'
                    data = a.data or b""
                    ctype = getattr(a, 'mimeType', None) or mimetypes.guess_type(fname or '')[0] or 'application/octet-stream'
                    atts.append({
                        'filename': fname,
                        'content_type': ctype,
                        'data': data,
                        'size': len(data) if isinstance(data, (bytes, bytearray)) else 0,
                    })
                except Exception:
                    continue
        except Exception:
            pass
        return {
            "subject": msg.subject or "",
            "from": msg.sender or "",
            "to": msg.to or "",
            "date": str(msg.date or ""),
            "body": msg.body or "",
            "attachments": atts,
        }
    except Exception as e:
        return {"error": f"MSG parse failed: {e}"}

def _try_parse_pdf(content: bytes) -> dict:
    # Try pdfplumber
    try:
        import pdfplumber  # optional dependency
        import io
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if pdf.pages:
                text = (pdf.pages[0].extract_text() or "").strip()
        return {"text_preview": text}
    except Exception:
        pass
    # Try PyPDF2
    try:
        import PyPDF2  # optional dependency
        import io
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        if reader.pages:
            text = (reader.pages[0].extract_text() or "").strip()
        return {"text_preview": text}
    except Exception as e:
        return {"error": f"PDF parse failed (install pdfplumber or PyPDF2?): {e}"}

def _try_parse_tabular(ext: str, content: bytes) -> dict:
    try:
        import io
        if ext in ("csv",):
            # Use Python engine with sep=None to infer delimiter (handles TSV or other delims)
            df = pd.read_csv(io.BytesIO(content), sep=None, engine="python")
        elif ext in ("xls", "xlsx"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            return {"error": f"Unsupported tabular type: {ext}"}
        return {"dataframe": df.head(10)}
    except Exception as e:
        return {"error": f"Tabular parse failed: {e}"}

# Render attachments found in parsed email data
# preview_data is dict possibly containing key 'attachments': list of {filename, content_type, data, size}
# selected_id is used to dedupe Streamlit widget keys across reruns

def _render_attachments(preview_data: dict, selected_id: str):
    try:
        atts = []
        if isinstance(preview_data, dict):
            atts = preview_data.get("attachments") or []
        if not atts:
            return
        st.subheader("Attachments")
        for i, att in enumerate(atts):
            try:
                fname = att.get("filename") if isinstance(att, dict) else None
                if not fname:
                    fname = f"attachment_{i+1}"
                ctype = (att.get("content_type") if isinstance(att, dict) else None) or "application/octet-stream"
                data = (att.get("data") if isinstance(att, dict) else None) or b""
                size = (att.get("size") if isinstance(att, dict) else None) or (len(data) if isinstance(data, (bytes, bytearray)) else 0)
                st.write(f"{fname} — {ctype} — {size} bytes")
                try:
                    st.download_button(
                        label=f"Download {fname}",
                        data=data,
                        file_name=fname,
                        mime=ctype,
                        key=f"dl_att_{i}_{selected_id}"
                    )
                except Exception:
                    pass
                # Quick preview
                ext_att, mime_att = _detect_filetype(fname)
                if ext_att in ("pdf",):
                    prev = _try_parse_pdf(data)
                    if "text_preview" in prev:
                        st.text_area(f"{fname} — PDF page 1 text", _safe_preview_text(prev["text_preview"]), height=160, key=f"att_pdf_prev_{i}_{selected_id}")
                elif ext_att in ("csv","xls","xlsx"):
                    prev = _try_parse_tabular(ext_att, data)
                    if "dataframe" in prev:
                        st.dataframe(prev["dataframe"], width='stretch', hide_index=True, key=f"att_tbl_prev_{i}_{selected_id}")
                elif ext_att in ("txt",):
                    try:
                        t = data.decode("utf-8", errors="replace")
                    except Exception:
                        t = ""
                    st.text_area(f"{fname} — text", _safe_preview_text(t), height=160, key=f"att_txt_prev_{i}_{selected_id}")
            except Exception:
                continue
    except Exception:
        pass

def _guess_vendor(name: str, email_from: str = "", body: str = "") -> str:
    try:
        if "@" in email_from:
            dom = email_from.split("@", 1)[-1].split(">")[0].strip().lower().strip("<>\"' ")
            if dom:
                return dom
        base = name.rsplit(".", 1)[0]
        tokens = [t for t in base.replace("_", " ").replace("-", " ").split() if t.isalpha()]
        if tokens:
            return tokens[0]
    except Exception:
        pass
    return ""

# Email address extraction helper
def _extract_email_address(raw_from: str) -> str:
    """Extract bare email from a From header like 'Name <user@domain.com>' or just 'user@domain.com'."""
    try:
        s = str(raw_from or "").strip()
        if not s:
            return ""
        # If angle brackets present, take inside
        if "<" in s and ">" in s:
            s = s[s.find("<")+1:s.rfind(">")]
        # Remove quotes and stray characters
        s = s.strip().strip("'\" ")
        # Basic sanity check
        return s if "@" in s else ""
    except Exception:
        return ""

# Contacts-based vendor helpers
@st.cache_data(show_spinner=False)
def _build_domain_vendor_map(df_contacts: pd.DataFrame) -> dict:
    """Build mapping: email domain -> set of Vendor names from contacts.csv.
    Expects df_contacts to contain columns named (case-insensitive) 'Email' and 'Vendor'."""
    mapping: dict[str, set[str]] = {}
    try:
        if df_contacts is None or df_contacts.empty:
            return mapping
        cols = {str(c).strip().lower(): c for c in df_contacts.columns}
        email_col = cols.get("email")
        vendor_col = cols.get("vendor")
        if not email_col or not vendor_col:
            return mapping
        for _, r in df_contacts.iterrows():
            em = str(r.get(email_col, "") or "").strip()
            vend = str(r.get(vendor_col, "") or "").strip()
            if not em or not vend or "@" not in em:
                continue
            dom = em.split("@", 1)[-1].split(">")[0].strip().lower().strip("<>\"' ")
            if not dom:
                continue
            mapping.setdefault(dom, set()).add(vend)
            parts = dom.split(".")
            if len(parts) > 2:
                base = ".".join(parts[-2:])
                mapping.setdefault(base, set()).add(vend)
    except Exception:
        # Fail quietly; caller will handle empty mapping
        return mapping
    return mapping

def _vendor_from_sender_domain(email_from: str, domain_map: dict) -> str:
    """Return canonical Vendor when sender domain maps to exactly one vendor; else ''."""
    try:
        if not email_from or "@" not in email_from or not domain_map:
            return ""
        dom = email_from.split("@", 1)[-1].split(">")[0].strip().lower().strip("<>\"' ")
        cands = domain_map.get(dom, set())
        if isinstance(cands, set) and len(cands) == 1:
            return next(iter(cands))
        # Try eTLD+1
        parts = dom.split(".")
        if len(parts) > 2:
            base = ".".join(parts[-2:])
            cands2 = domain_map.get(base, set())
            if isinstance(cands2, set) and len(cands2) == 1:
                return next(iter(cands2))
    except Exception:
        return ""
    return ""

def _load_master_df():
    """Load rfq_master.csv via RFQTracking (Box if configured, else local)."""
    tracker = get_tracker()
    try:
        if getattr(tracker, "master_store", None) is not None:
            df = tracker.master_store.load_df()
            if isinstance(df, pd.DataFrame):
                return df
    except Exception:
        pass
    try:
        p = getattr(tracker, "master_path", None)
        if p and Path(p).exists():
            try:
                return pd.read_csv(p, encoding="utf-8")
            except UnicodeDecodeError:
                return pd.read_csv(p, encoding="cp1252")
    except Exception:
        pass
    return pd.DataFrame()

def _master_cols(df: pd.DataFrame) -> dict:
    return {
        "rfq": _find_col(df, [
            "rfq#", "rfq #", "rfqno", "rfqid", "rfq number", "rfq no", "rfq_num", "rfq num", "rfq"
        ]),
        "part": _find_col(df, ["part_number", "part number", "part", "pn"]),
        "vendor": _find_col(df, ["vendor", "vendor_name", "vendor name"]),
        "process": _find_col(df, ["process"]),
    }

def _rfq_options_from_master(master_df: pd.DataFrame) -> list[str]:
    try:
        if master_df is None or master_df.empty:
            return []
        cols = _master_cols(master_df)
        rfq_col = cols.get("rfq")
        if not rfq_col:
            return []
        return sorted(master_df[rfq_col].dropna().astype(str).unique(), key=lambda x: (len(x), x))
    except Exception:
        return []

def _extract_numbers(text: str) -> list[int]:
    if not text:
        return []
    nums = re.findall(r"\b(\d{3,})\b", text)
    return [int(n) for n in nums if n.isdigit()]

def _auto_match_rfq(master_df: pd.DataFrame, name: str, subject: str, body: str, vendor_guess: str) -> dict:
    result = {"match": None, "candidates": pd.DataFrame(), "reason": ""}
    if master_df is None or master_df.empty:
        result["reason"] = "RFQ master is empty"
        return result
    cols = _master_cols(master_df)
    if not any(cols.values()):
        result["reason"] = "RFQ master missing required columns"
        return result

    subject = subject or ""
    body = body or ""
    text_all = " ".join([name or "", subject, body])

    # 1) RFQ# in text
    rfq_col = cols["rfq"]
    if rfq_col:
        rfq_nums = _extract_numbers(text_all)
        if rfq_nums:
            cand = master_df[master_df[rfq_col].astype(str).isin([str(n) for n in rfq_nums])]
            if len(cand) == 1:
                result["match"] = cand.iloc[0]
                result["reason"] = f"Matched by RFQ# {cand.iloc[0][rfq_col]}"
                return result
            elif len(cand) > 1:
                result["candidates"] = cand

    # 2) Part + Vendor
    part_col = cols["part"]
    vendor_col = cols["vendor"]
    if part_col:
        tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_]{3,}", name or "")
        tokens += re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_]{3,}", subject)
        tokens = sorted(set([t.strip() for t in tokens]), key=len, reverse=True)[:10]
        dfp = master_df
        if tokens:
            mask_part = pd.Series(False, index=dfp.index)
            for t in tokens:
                mask_part = mask_part | dfp[part_col].astype(str).str.contains(re.escape(t), case=False, na=False)
            dfp = dfp[mask_part] if not mask_part.empty and mask_part.any() else dfp
        if vendor_col and vendor_guess:
            v = str(vendor_guess).strip().lower()
            mask_vendor = dfp[vendor_col].astype(str).str.lower().str.contains(v, na=False) | (dfp[vendor_col].astype(str).str.lower() == v)
            dfpv = dfp[mask_vendor] if mask_vendor.any() else dfp
        else:
            dfpv = dfp
        if len(dfpv) == 1:
            result["match"] = dfpv.iloc[0]
            result["reason"] = "Matched by Part+Vendor"
            return result
        elif 1 < len(dfpv) <= 25:
            result["candidates"] = dfpv

    # 3) Part-only unique
    if part_col:
        part_tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_]{3,}", text_all)
        if part_tokens:
            mask = pd.Series(False, index=master_df.index)
            for t in set(part_tokens):
                mask = mask | master_df[part_col].astype(str).str.contains(re.escape(t), case=False, na=False)
            same_part_df = master_df[mask] if mask.any() else pd.DataFrame()
            if len(same_part_df) == 1:
                result["match"] = same_part_df.iloc[0]
                result["reason"] = "Matched by Part only"
                return result
            elif 1 < len(same_part_df) <= 25 and result["candidates"].empty:
                result["candidates"] = same_part_df

    if result["candidates"].empty and rfq_col:
        result["candidates"] = master_df.copy()
    result["reason"] = "No single match"
    return result

def _scrape_numbers_like_money(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"(?<!\w)(?:\$?\s?)(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})|\d+\.\d{2})(?!\w)", text)
    return m.group(0).strip() if m else ""

def _scrape_lead_time_days(text: str) -> int | None:
    if not text:
        return None
    m = re.search(r"(\d+)\s*(day|days|week|weeks)", text, re.IGNORECASE)
    if not m:
        return None
    qty = int(m.group(1))
    unit = m.group(2).lower()
    return qty if unit.startswith("day") else qty * 7

def _scrape_lot_min(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"(?:lot\s*min(?:imum)?|minimum\s*lot)\D{0,10}(\d{1,6})", text, re.IGNORECASE)
    return m.group(1) if m else ""

def _first_nonempty(*vals) -> str:
    for v in vals:
        if str(v or "").strip():
            return str(v)
    return ""

def _resolve_responses_folder_id(tracker) -> str | None:
    """
    Try to determine the Box folder_id where responses files should be uploaded.
    Priority:
      1) tracker.responses_store.folder_id if set
      2) Parent folder of tracker.responses_store.file_id (if only file_id configured)
    Returns folder_id or None if Box not configured/available.
    """
    try:
        store = getattr(tracker, "responses_store", None)
        if not store:
            return None
        folder_id = getattr(store, "folder_id", None)
        if folder_id:
            return folder_id
        file_id = getattr(store, "file_id", None)
        box = getattr(store, "box", None)
        client = getattr(box, "client", None) if box else None
        if file_id and client:
            try:
                fobj = client.file(file_id).get()
                parent = getattr(fobj, "parent", None)
                if parent and getattr(parent, "id", None):
                    return parent.id
            except Exception:
                return None
    except Exception:
        return None
    return None

# ---- Box helpers: resolve RFQs root, find/create RFQ folder, move file ----

def _get_rfq_root_folder_id() -> str | None:
    """Return Box RFQs root folder id from secrets if available, else None."""
    try:
        from core.secrets import get_section
        bx = get_section("box") or {}
        rid = str(bx.get("BOX_RFQS_FOLDER_ID", "")).strip()
        if rid:
            return rid
    except Exception:
        pass
    # Optional known constant from earlier notes; use only if present in secrets ideally
    return None


def _find_child_folder_by_name(client, parent_folder_id: str, child_name: str) -> str | None:
    try:
        items = client.folder(parent_folder_id).get_items(limit=1000, fields=["id", "name", "type"])
        for it in items:
            try:
                if getattr(it, "type", None) == "folder" and getattr(it, "name", "") == child_name:
                    return getattr(it, "id", None)
            except Exception:
                continue
    except Exception:
        return None
    return None


def _ensure_rfq_folder(client, rfq_root_id: str, rfq_num: str) -> str | None:
    name = str(rfq_num).strip()
    if not name:
        return None
    # find
    fid = _find_child_folder_by_name(client, rfq_root_id, name)
    if fid:
        return fid
    # create if missing
    try:
        newf = client.folder(rfq_root_id).create_subfolder(name)
        return getattr(newf, "id", None)
    except BoxAPIException as e:
        # If 409, fetch existing
        if getattr(e, "status", None) == 409:
            return _find_child_folder_by_name(client, rfq_root_id, name)
        return None
    except Exception:
        return None


def _move_file_to_rfq_folder(client, file_id: str, rfq_num: str) -> dict:
    """Move a Box file into the RFQ folder under the RFQs root.
    Returns dict: {"ok": bool, "rfq_folder_id": str|None, "message": str}
    """
    try:
        rfq_root_id = _get_rfq_root_folder_id()
        if not rfq_root_id:
            # If not configured, try to infer from Responses folder's parent (often RFQs)
            try:
                tracker = get_tracker()
                store = getattr(tracker, "responses_store", None)
                box = getattr(store, "box", None) if store else None
                client2 = getattr(box, "client", None) if box else None
                if client2 and getattr(store, "folder_id", None):
                    # parent of Responses folder is RFQs
                    resp_parent = client2.folder(store.folder_id).get().parent
                    rfq_root_id = getattr(resp_parent, "id", None)
            except Exception as e:
                pass
        if not rfq_root_id:
            return {"ok": False, "rfq_folder_id": None, "message": "RFQs root not configured"}
        rfq_folder_id = _ensure_rfq_folder(client, rfq_root_id, rfq_num)
        if not rfq_folder_id:
            return {"ok": False, "rfq_folder_id": None, "message": "Failed to resolve/create RFQ folder"}
        fobj = client.file(file_id).get()
        parent = getattr(getattr(fobj, "parent", None), "id", None)
        if parent == rfq_folder_id:
            return {"ok": True, "rfq_folder_id": rfq_folder_id, "message": "Already in RFQ folder"}
        client.file(file_id).move(client.folder(rfq_folder_id))
        return {"ok": True, "rfq_folder_id": rfq_folder_id, "message": "Moved"}
    except BoxAPIException as e:
        return {"ok": False, "rfq_folder_id": None, "message": f"BoxAPIException {getattr(e,'status', '')} {getattr(e,'code','')}"}
    except Exception as e:
        return {"ok": False, "rfq_folder_id": None, "message": f"Move failed: {e}"}

def _get_rfq_folder_id(client, rfq_num: str) -> str | None:
    rfq_root_id = _get_rfq_root_folder_id()
    if not rfq_root_id:
        try:
            tracker = get_tracker()
            store = getattr(tracker, "responses_store", None)
            box = getattr(store, "box", None) if store else None
            client2 = getattr(box, "client", None) if box else None
            if client2 and getattr(store, "folder_id", None):
                resp_parent = client2.folder(store.folder_id).get().parent
                rfq_root_id = getattr(resp_parent, "id", None)
        except Exception:
            rfq_root_id = None
    if not rfq_root_id:
        return None
    return _ensure_rfq_folder(client, rfq_root_id, str(rfq_num or "").strip())

# Helper to clear form/session state after saving to prevent accidental reuse
def _clear_response_form_state():
    keys = [
        "responses_selected_file_id",
        "responses_selected_file_name",
        "responses_valid_through_from_table",
        "responses_scope_from_table",
        "overwrite_confirm_master",
        "overwrite_confirm_master_always",
        "nq_mark_master",
        "nq_mark_master_always",
        "responses_pick_master",
        "responses_pick_master_always",
        "responses_select_file",
        "responses_select_file_always",
        "responses_select_file_local",
        "responses_select_file_local_always",
    ]
    for k in keys:
        try:
            st.session_state.pop(k, None)
        except Exception:
            pass

def display_responses(user, role):
    # Handle any pending post-save move across reruns (centralized)
    try:
        pend = st.session_state.get("responses_pending_move")
        if pend:
            tracker = get_tracker()
            store = getattr(tracker, "responses_store", None)
            box = getattr(store, "box", None) if store else None
            client = getattr(box, "client", None) if box else None
            file_id = str(pend.get("file_id", ""))
            rfq_num_clean = str(pend.get("rfq", "")).strip()
            if client and file_id.isdigit() and rfq_num_clean:
                res = _move_file_to_rfq_folder(client, file_id, rfq_num_clean)
                if res.get("ok"):
                    st.success("Moved file to RFQ folder on previous save")
                else:
                    st.warning(f"Move on previous save failed/skipped: {res.get('message','unknown')}")
                # Try to set quote_folder link
                try:
                    rfq_folder_id = res.get("rfq_folder_id") or _get_rfq_folder_id(client, rfq_num_clean)
                    if rfq_folder_id:
                        quote_url = f"https://app.box.com/folder/{rfq_folder_id}"
                        try:
                            df_curr = tracker.responses_store.load_df() if tracker.responses_store is not None else _load_responses_df()
                        except Exception:
                            df_curr = _load_responses_df()
                        if isinstance(df_curr, pd.DataFrame) and not df_curr.empty and "quote_folder" in df_curr.columns:
                            mask = (df_curr["file_id"].astype(str) == file_id) & (df_curr["rfq#"].astype(str).str.strip() == rfq_num_clean)
                            df_curr.loc[mask, "quote_folder"] = quote_url
                            save_responses_df(df_curr)
                except Exception as le:
                    logger.warning(f"quote_folder link update failed: {le}")
            st.session_state.pop("responses_pending_move", None)
    except Exception as _ex:
        logger.warning(f"pending move handler error: {_ex}")

    # Tabs: Upload/Process vs. Files list
    tab_upload, tab_files = st.tabs(["Upload / Process", "Responses Files"])

    with tab_upload:
        st.subheader("Upload Responses Files")
        st.caption("Drop files here to store them in the Box ‘responses’ folder (if configured).")
        uploaded = st.file_uploader(
            "Drop responses files here",
            type=["pdf","xlsx","xls","csv","docx","txt","zip","png","jpg","jpeg","msg","eml"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="responses_uploader",
        )

        if uploaded:
            st.info(f"Selected {len(uploaded)} file(s). Click Upload to send to Box.")
            if st.button("Upload selected to Box", key="upload_to_box"):
                tracker = get_tracker()
                store = getattr(tracker, "responses_store", None)
                box = getattr(store, "box", None) if store else None
                client = getattr(box, "client", None) if box else None

                # Resolve the target folder id deterministically
                target_folder_id = None
                try:
                    file_parent_id = None
                    if store and getattr(store, "file_id", None) and client:
                        try:
                            fobj = client.file(store.file_id).get()
                            if getattr(fobj, "parent", None) and getattr(fobj.parent, "id", None):
                                file_parent_id = fobj.parent.id
                        except Exception:
                            file_parent_id = None
                    explicit_folder_id = None
                    if store and getattr(store, "folder_id", None):
                        explicit_folder_id = store.folder_id
                    target_folder_id = file_parent_id or explicit_folder_id
                    if not target_folder_id:
                        try:
                            from core.secrets import get_section as _get_secret_section
                            _bx = _get_secret_section("box") or {}
                            val = str(_bx.get("BOX_RFQ_RESPONSES_FOLDER_ID", "")).strip()
                            target_folder_id = val or None
                        except Exception:
                            target_folder_id = None
                    if file_parent_id and explicit_folder_id and file_parent_id != explicit_folder_id:
                        target_folder_id = file_parent_id
                except Exception:
                    target_folder_id = None

                successes, failures = [], []
                if client and target_folder_id:
                    # Show which folder we will upload to
                    folder_name = "(unknown)"
                    try:
                        fobj = client.folder(target_folder_id).get()
                        folder_name = getattr(fobj, "name", folder_name)
                    except Exception:
                        pass
                    st.caption(f"Upload target: Box folder {target_folder_id} — {folder_name}")
                    try:
                        if store and target_folder_id and getattr(store, "folder_id", None) != target_folder_id:
                            store.folder_id = target_folder_id
                    except Exception:
                        pass
                    try:
                        file_parent_id_msg = None
                        explicit_folder_id_msg = None
                        if store and getattr(store, "file_id", None):
                            try:
                                pf = client.file(store.file_id).get()
                                if getattr(pf, "parent", None) and getattr(pf.parent, "id", None):
                                    file_parent_id_msg = pf.parent.id
                            except Exception:
                                pass
                        if store and getattr(store, "folder_id", None):
                            explicit_folder_id_msg = store.folder_id
                        if file_parent_id_msg and explicit_folder_id_msg and file_parent_id_msg != explicit_folder_id_msg:
                            try:
                                resp_folder_name = client.folder(file_parent_id_msg).get().name
                            except Exception:
                                resp_folder_name = "(unknown)"
                            try:
                                exp_folder_name = client.folder(explicit_folder_id_msg).get().name
                            except Exception:
                                exp_folder_name = "(unknown)"
                            st.warning(
                                f"Detected mismatch between responses file parent ({file_parent_id_msg} — {resp_folder_name}) "
                                f"and configured folder_id ({explicit_folder_id_msg} — {exp_folder_name}). Using the responses file parent."
                            )
                    except Exception:
                        pass

                    # Upload to Box
                    for uf in uploaded:
                        try:
                            uf.seek(0)
                            bio = BytesIO(uf.read())
                            bio.seek(0)
                            client.folder(target_folder_id).upload_stream(bio, uf.name)
                            successes.append(uf.name)
                        except BoxAPIException as e:
                            if e.status == 409:
                                try:
                                    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                                    if "." in uf.name:
                                        base, ext = uf.name.rsplit(".", 1)
                                        alt_name = f"{base} ({ts}).{ext}"
                                    else:
                                        alt_name = f"{uf.name} ({ts})"
                                    bio.seek(0)
                                    client.folder(target_folder_id).upload_stream(bio, alt_name)
                                    successes.append(f"{uf.name} -> {alt_name}")
                                except Exception as _re:
                                    failures.append(f"{uf.name}: 409 conflict and rename failed: {_re}")
                            else:
                                failures.append(f"{uf.name}: BoxAPIException {e.status} {getattr(e, 'code', '')}")
                        except Exception as e:
                            failures.append(f"{uf.name}: {e}")
                else:
                    # Local fallback if Box not configured/available
                    try:
                        local_base = getattr(tracker, "responses_path", None)
                        if local_base is not None:
                            local_folder = local_base.parent / "responses_uploads"
                            local_folder.mkdir(parents=True, exist_ok=True)
                            for uf in uploaded:
                                try:
                                    uf.seek(0)
                                    data = uf.read()
                                    (local_folder / uf.name).write_bytes(data)
                                    successes.append(f"{uf.name} (saved locally to {local_folder})")
                                except Exception as e:
                                    failures.append(f"{uf.name}: {e}")
                        else:
                            failures.append("Local fallback path not available")
                    except Exception as e:
                        failures.append(f"Local fallback failed: {e}")

                if successes:
                    st.success(f"Uploaded {len(successes)} file(s): " + ", ".join(successes))
                    with st.expander("Next steps", expanded=False):
                        st.markdown("- If you uploaded CSV updates, click ‘Refresh from Box’ below to reload the table.")
                if failures:
                    st.error("Some files could not be uploaded:")
                    for msg in failures:
                        st.write(f"- {msg}")

                st.session_state["responses_uploader"] = None
                st.rerun()

    # Second tab: show files in Responses folder
    with tab_files:
        st.subheader("Files in Responses folder")
        try:
            tracker = get_tracker()
            store = getattr(tracker, "responses_store", None)
            box = getattr(store, "box", None) if store else None
            client = getattr(box, "client", None) if box else None

            # Resolve target folder id using authoritative parent-of-file when possible
            target_folder_id = None
            file_parent_id = None
            explicit_folder_id = None
            try:
                if store and getattr(store, "file_id", None) and client:
                    try:
                        _f = client.file(store.file_id).get()
                        if getattr(_f, "parent", None) and getattr(_f.parent, "id", None):
                            file_parent_id = _f.parent.id
                    except Exception:
                        file_parent_id = None
                if store and getattr(store, "folder_id", None):
                    explicit_folder_id = store.folder_id
                target_folder_id = file_parent_id or explicit_folder_id
                if not target_folder_id:
                    try:
                        from core.secrets import get_section as _get_secret_section
                        _bx = _get_secret_section("box") or {}
                        val = str(_bx.get("BOX_RFQ_RESPONSES_FOLDER_ID", "")).strip()
                        target_folder_id = val or None
                    except Exception:
                        target_folder_id = None
                if file_parent_id and explicit_folder_id and file_parent_id != explicit_folder_id:
                    # Prefer file parent (should be 'Responses')
                    target_folder_id = file_parent_id
            except Exception:
                target_folder_id = None

            def _hr_size(n) -> str:
                try:
                    n = int(n or 0)
                    for unit in ["B", "KB", "MB", "GB", "TB"]:
                        if n < 1024 or unit == "TB":
                            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
                        n /= 1024
                except Exception:
                    return ""

            if client and target_folder_id:
                # Show folder context
                try:
                    folder_obj = client.folder(target_folder_id).get()
                    st.caption(f"Listing: Box folder {target_folder_id} — {getattr(folder_obj, 'name', '(unknown)')}")
                except Exception:
                    st.caption(f"Listing: Box folder {target_folder_id}")

                # Fetch first page of items
                try:
                    items = list(client.folder(target_folder_id).get_items(limit=1000, fields=["id","name","size","modified_at","sha1"]))
                except Exception as e:
                    items = []
                    st.error(f"Failed to list Box folder items: {e}")

                files = []
                for it in items:
                    try:
                        if getattr(it, "type", None) == "file":
                            files.append({
                                "id": getattr(it, "id", ""),
                                "name": getattr(it, "name", ""),
                                "size": getattr(it, "size", 0),
                                "modified_at": getattr(it, "modified_at", ""),
                            })
                    except Exception:
                        pass

                if files:
                    df_files = pd.DataFrame(files)
                    if not df_files.empty:
                        # Exclude the tracking CSV from processing list
                        try:
                            df_files = df_files[df_files["name"].str.lower() != "rfq_responses.csv"]
                        except Exception:
                            pass
                        # Sort newest first by modified_at (if available)
                        try:
                            df_files["modified_at_dt"] = pd.to_datetime(df_files["modified_at"], errors="coerce")
                            df_files = df_files.sort_values("modified_at_dt", ascending=False)
                        except Exception:
                            pass
                        # Prettify size
                        try:
                            df_files["size_readable"] = df_files["size"].apply(_hr_size)
                        except Exception:
                            df_files["size_readable"] = df_files["size"]
                        cols = [c for c in ["name", "size_readable", "modified_at", "id"] if c in df_files.columns]
                        st.dataframe(df_files[cols], width='stretch', hide_index=True)
                        st.caption(f"{len(df_files)} file(s) found. Use this tab to browse; processing controls remain on the main tab.")
                else:
                    st.info("No files found in the Responses folder.")
            else:
                # Local fallback listing
                try:
                    local_base = getattr(tracker, "responses_path", None)
                    if local_base is not None:
                        local_folder = local_base.parent / "responses_uploads"
                        local_folder.mkdir(parents=True, exist_ok=True)
                        local_files = []
                        for p in sorted(local_folder.glob("*")):
                            if p.is_file():
                                stat = p.stat()
                                local_files.append({
                                    "path": str(p),
                                    "name": p.name,
                                    "size": stat.st_size,
                                    "modified_at": pd.to_datetime(stat.st_mtime, unit='s').isoformat() if hasattr(pd, 'to_datetime') else str(stat.st_mtime),
                                })
                        if local_files:
                            df_local = pd.DataFrame(local_files)
                            try:
                                df_local["size_readable"] = df_local["size"].apply(_hr_size)
                            except Exception:
                                df_local["size_readable"] = df_local["size"]
                            cols = [c for c in ["name", "size_readable", "modified_at", "path"] if c in df_local.columns]
                            st.dataframe(df_local[cols], width='stretch', hide_index=True)
                            st.caption(f"{len(df_local)} local file(s) found in responses_uploads.")
                        else:
                            st.info("No local files found in responses_uploads.")
                    else:
                        st.info("Box not configured and no local fallback folder available.")
                except Exception as e:
                    st.error(f"Failed to list local uploads: {e}")
        except Exception as e:
            st.error(f"Failed to list files in the Responses folder: {e}")

        st.subheader("Files in Responses folder")
        try:
            tracker = get_tracker()
            store = getattr(tracker, "responses_store", None)
            box = getattr(store, "box", None) if store else None
            client = getattr(box, "client", None) if box else None

            # Resolve target folder id using authoritative parent-of-file when possible
            target_folder_id = None
            file_parent_id = None
            explicit_folder_id = None
            try:
                if store and getattr(store, "file_id", None) and client:
                    try:
                        _f = client.file(store.file_id).get()
                        if getattr(_f, "parent", None) and getattr(_f.parent, "id", None):
                            file_parent_id = _f.parent.id
                    except Exception:
                        file_parent_id = None
                if store and getattr(store, "folder_id", None):
                    explicit_folder_id = store.folder_id
                target_folder_id = file_parent_id or explicit_folder_id
                if not target_folder_id:
                    try:
                        from core.secrets import get_section as _get_secret_section
                        _bx = _get_secret_section("box") or {}
                        val = str(_bx.get("BOX_RFQ_RESPONSES_FOLDER_ID", "")).strip()
                        target_folder_id = val or None
                    except Exception:
                        target_folder_id = None
                if file_parent_id and explicit_folder_id and file_parent_id != explicit_folder_id:
                    # Prefer file parent (should be 'Responses')
                    target_folder_id = file_parent_id
            except Exception:
                target_folder_id = None

            def _hr_size(n) -> str:
                try:
                    n = int(n or 0)
                    for unit in ["B", "KB", "MB", "GB", "TB"]:
                        if n < 1024 or unit == "TB":
                            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
                        n /= 1024
                except Exception:
                    return ""

            selected_id = None
            selected_name = None

            if client and target_folder_id:
                # Show folder context
                try:
                    folder_obj = client.folder(target_folder_id).get()
                    st.caption(f"Listing: Box folder {target_folder_id} — {getattr(folder_obj, 'name', '(unknown)')}")
                except Exception:
                    st.caption(f"Listing: Box folder {target_folder_id}")

                # Fetch first page of items
                try:
                    items = list(client.folder(target_folder_id).get_items(limit=1000, fields=["id","name","size","modified_at","sha1"]))
                except Exception as e:
                    items = []
                    st.error(f"Failed to list Box folder items: {e}")

                files = []
                for it in items:
                    try:
                        if getattr(it, "type", None) == "file":
                            files.append({
                                "id": getattr(it, "id", ""),
                                "name": getattr(it, "name", ""),
                                "size": getattr(it, "size", 0),
                                "modified_at": getattr(it, "modified_at", ""),
                            })
                    except Exception:
                        pass

                if files:
                    df_files = pd.DataFrame(files)
                    if not df_files.empty:
                        try:
                            df_files["size_readable"] = df_files["size"].apply(_hr_size)
                        except Exception:
                            df_files["size_readable"] = df_files["size"]
                        cols = [c for c in ["name", "size_readable", "modified_at", "id"] if c in df_files.columns]
                        st.dataframe(df_files[cols], width='stretch', hide_index=True)

                        # Selection UI
                        labels = [f"{row['name']} (id {row['id']}, {_hr_size(row['size'])})" for _, row in
                                  df_files.iterrows()]
                        selected_label = st.selectbox(
                            "Select a file to process",
                            options=labels,
                            index=0 if labels else None,
                            key="responses_select_file",
                        )
                        if selected_label:
                            try:
                                idx = labels.index(selected_label)
                                selected_id = str(df_files.iloc[idx]["id"]) if "id" in df_files.columns else None
                                selected_name = str(df_files.iloc[idx]["name"]) if "name" in df_files.columns else None
                            except Exception:
                                selected_id = None
                                selected_name = None
                else:
                    st.info("No files found in the Responses folder.")
            else:
                # Local fallback listing
                try:
                    local_base = getattr(tracker, "responses_path", None)
                    if local_base is not None:
                        local_folder = local_base.parent / "responses_uploads"
                        local_folder.mkdir(parents=True, exist_ok=True)
                        local_files = []
                        for p in sorted(local_folder.glob("*")):
                            if p.is_file():
                                stat = p.stat()
                                local_files.append({
                                    "path": str(p),
                                    "name": p.name,
                                    "size": stat.st_size,
                                    "modified_at": pd.to_datetime(stat.st_mtime, unit='s').isoformat() if hasattr(pd,
                                                                                                                  'to_datetime') else str(
                                        stat.st_mtime),
                                })
                        if local_files:
                            df_local = pd.DataFrame(local_files)
                            try:
                                df_local["size_readable"] = df_local["size"].apply(_hr_size)
                            except Exception:
                                df_local["size_readable"] = df_local["size"]
                            cols = [c for c in ["name", "size_readable", "modified_at", "path"] if
                                    c in df_local.columns]
                            st.dataframe(df_local[cols], width='stretch', hide_index=True)
                            labels = [f"{row['name']} ({_hr_size(row['size'])})" for _, row in df_local.iterrows()]
                            selected_label = st.selectbox(
                                "Select a local file to process",
                                options=labels,
                                index=0 if labels else None,
                                key="responses_select_file_local",
                            )
                            if selected_label:
                                try:
                                    idx = labels.index(selected_label)
                                    selected_id = str(df_local.iloc[idx]["path"])  # reuse as id in local mode
                                    selected_name = str(
                                        df_local.iloc[idx]["name"]) if "name" in df_local.columns else None
                                except Exception:
                                    selected_id = None
                                    selected_name = None
                        else:
                            st.info("No local files found in responses_uploads.")
                    else:
                        st.info("Box not configured and no local fallback folder available.")
                except Exception as e:
                    st.error(f"Failed to list local uploads: {e}")

            # If we have a selected file, offer processing
            if selected_id:
                st.session_state["responses_selected_file_id"] = selected_id
                st.session_state["responses_selected_file_name"] = selected_name

                # New: Allow sending file to RFQ folder without logging to CSV
                with st.expander("Send file to RFQ folder (no log)", expanded=False):
                    rfq_options = _rfq_options_from_master(_load_master_df())
                    if rfq_options:
                        rfq_move_in = st.selectbox(
                            "RFQ # to send file to (no log)",
                            options=rfq_options,
                            index=0,
                            key="responses_move_rfq_once",
                        )
                    else:
                        rfq_move_in = st.text_input(
                            "RFQ # to send file to (no log)",
                            value="",
                            key="responses_move_rfq_once"
                        )
                        try:
                            mdf = _load_master_df()
                            src = "Box" if getattr(get_tracker(), "master_store", None) is not None else "local"
                            st.caption(f"RFQ dropdown unavailable — RFQ master empty or RFQ column not found. Source: {src}; columns: {list(mdf.columns) if not mdf.empty else '[]'}")
                        except Exception:
                            st.caption("RFQ dropdown unavailable — RFQ master empty or RFQ column not found.")
                    col_mv1, col_mv2 = st.columns([1, 5])
                    with col_mv1:
                        if st.button("Send file to RFQ folder (no log)", key="responses_send_only_once"):
                            try:
                                rfq_num_clean = str(rfq_move_in or "").strip()
                                if not rfq_num_clean:
                                    st.warning("Please enter an RFQ #.")
                                else:
                                    # Only supported in Box mode with numeric file id
                                    if client and str(selected_id).isdigit():
                                        res = _move_file_to_rfq_folder(client, str(selected_id), rfq_num_clean)
                                        if res.get("ok"):
                                            st.success(f"{res.get('message','Moved')} — file sent to RFQ {rfq_num_clean}")
                                        else:
                                            st.warning(f"Move failed/skipped: {res.get('message','unknown')}")
                                    else:
                                        st.info("Sending to RFQ folder is only available when Box is configured.")
                            except Exception as _merr:
                                st.error(f"Move failed: {_merr}")

                if st.button("Process selected file", key="process_selected_response_file"):
                    try:
                        raw = None
                        ext = ""
                        mime = ""

                        # Box mode
                        if client and str(selected_id).isdigit():
                            raw = _download_box_file_bytes(client, selected_id)
                            ext, mime = _detect_filetype(selected_name)
                        else:
                            # Local mode: selected_id is a path
                            try:
                                p = Path(selected_id)
                                raw = p.read_bytes()
                                ext, mime = _detect_filetype(selected_name or p.name)
                            except Exception as le:
                                raise RuntimeError(f"Failed to read local file: {le}")

                        st.caption(f"Detected type: .{ext or '(none)'} — {mime or ''}")

                        preview_data = {}
                        subject = ""
                        email_from = ""
                        body_excerpt = ""
                        vendor_guess = ""

                        # Parse previews
                        if ext in ("eml",):
                            preview_data = _try_parse_eml(raw)
                            if "error" in preview_data:
                                st.warning(preview_data["error"])
                            else:
                                subject = preview_data.get("subject", "")
                                email_from = preview_data.get("from", "")
                                body_excerpt = _safe_preview_text(preview_data.get("body", ""))
                                # Prefer contacts-based vendor mapping
                                try:
                                    tracker = get_tracker()
                                    domain_map = _build_domain_vendor_map(getattr(tracker, "contacts_df", pd.DataFrame()))
                                except Exception:
                                    domain_map = {}
                                vendor_from_contacts = _vendor_from_sender_domain(email_from, domain_map)
                                vendor_guess = vendor_from_contacts or _guess_vendor(selected_name, email_from, body_excerpt)
                                st.write(f"Subject: {subject}")
                                st.write(f"From: {email_from}")
                                st.caption("Vendor source: " + ("contacts.csv domain→vendor" if vendor_from_contacts else "heuristic guess"))
                                st.text_area("Body preview", body_excerpt, height=200)
                                _render_attachments(preview_data, str(selected_id))

                        elif ext in ("msg",):
                            preview_data = _try_parse_msg(raw)
                            if "error" in preview_data:
                                st.warning(preview_data["error"])
                            else:
                                subject = preview_data.get("subject", "")
                                email_from = preview_data.get("from", "")
                                body_excerpt = _safe_preview_text(preview_data.get("body", ""))
                                # Prefer contacts-based vendor mapping
                                try:
                                    tracker = get_tracker()
                                    domain_map = _build_domain_vendor_map(getattr(tracker, "contacts_df", pd.DataFrame()))
                                except Exception:
                                    domain_map = {}
                                vendor_from_contacts = _vendor_from_sender_domain(email_from, domain_map)
                                vendor_guess = vendor_from_contacts or _guess_vendor(selected_name, email_from, body_excerpt)
                                st.write(f"Subject: {subject}")
                                st.write(f"From: {email_from}")
                                st.caption("Vendor source: " + ("contacts.csv domain→vendor" if vendor_from_contacts else "heuristic guess"))
                                st.text_area("Body preview", body_excerpt, height=200)
                                _render_attachments(preview_data, str(selected_id))

                        elif ext in ("csv", "xls", "xlsx"):
                            preview_data = _try_parse_tabular(ext, raw)
                            if "dataframe" in preview_data:
                                st.write("Preview of first 10 rows:")
                                st.dataframe(preview_data["dataframe"], width='stretch', hide_index=True)
                                vendor_guess = _guess_vendor(selected_name)
                            else:
                                st.warning(preview_data.get("error", "Failed to parse table."))

                        elif ext in ("pdf",):
                            preview_data = _try_parse_pdf(raw)
                            if "text_preview" in preview_data:
                                st.text_area("PDF page 1 text preview",
                                             _safe_preview_text(preview_data["text_preview"]), height=200)
                                vendor_guess = _guess_vendor(selected_name)
                            else:
                                st.warning(preview_data.get("error", "Failed to parse PDF."))

                        elif ext in ("txt",):
                            try:
                                text = raw.decode("utf-8", errors="replace")
                            except Exception:
                                text = ""
                            body_excerpt = _safe_preview_text(text)
                            vendor_guess = _guess_vendor(selected_name)
                            st.text_area("Text preview", body_excerpt, height=200)

                        else:
                            st.info("No parser for this file type yet. You can still record a processed entry.")
                            vendor_guess = _guess_vendor(selected_name)

                        # -- Load RFQ master and try to match RFQ --
                        master_df = _load_master_df()
                        mcols = _master_cols(master_df)

                        selected_rfq_num_val = ""
                        selected_part_val = ""
                        selected_vendor_val = ""
                        selected_process_val = ""
                        # Additional values from RFQ master
                        selected_qtso_val = ""
                        selected_rev_val = ""
                        selected_qty_val = ""
                        selected_contact_val = ""
                        received_ts = _first_nonempty(
                            (preview_data.get("date") if isinstance(preview_data, dict) else ""),
                            _now_utc_iso()
                        )

                        if master_df is not None and not master_df.empty:
                            auto = _auto_match_rfq(
                                master_df,
                                selected_name or "",
                                subject or "",
                                body_excerpt or "",
                                vendor_guess or "",
                            )
                            if auto.get("match") is not None:
                                row = auto["match"]
                                try:
                                    selected_rfq_num_val = str(row[mcols.get("rfq")]) if mcols.get("rfq") else ""
                                    selected_part_val = str(row[mcols.get("part")]) if mcols.get("part") else ""
                                    selected_vendor_val = str(row[mcols.get("vendor")]) if mcols.get("vendor") else ""
                                    selected_process_val = str(row[mcols.get("process")]) if mcols.get(
                                        "process") else ""
                                    # Populate Qty from RFQ Master when available (include template header "quantities")
                                    try:
                                        qty_col = _find_col(master_df, [
                                            "qty", "quantity", "quantities", "order qty", "order quantity", "rfq qty"
                                        ])
                                        if qty_col and qty_col in row:
                                            selected_qty_val = str(row[qty_col]) if pd.notna(row[qty_col]) else ""
                                    except Exception:
                                        pass
                                    # Populate QT/SO # from RFQ Master when available
                                    try:
                                        qtso_col = _find_col(master_df, [
                                            "qt/so #", "qt/so#", "qt", "so", "quote", "so #", "qt #"
                                        ])
                                        if qtso_col and qtso_col in row:
                                            selected_qtso_val = str(row[qtso_col]) if pd.notna(row[qtso_col]) else ""
                                    except Exception:
                                        pass
                                    st.success(
                                        f"Auto-matched RFQ: RFQ {selected_rfq_num_val} — {selected_part_val} — {selected_vendor_val} — {selected_process_val}"
                                    )
                                except Exception:
                                    pass
                            else:
                                cands = auto.get("candidates") if isinstance(auto.get("candidates"),
                                                                             pd.DataFrame) else pd.DataFrame()
                                if not cands.empty:
                                    view_cols = []
                                    for key in ("rfq", "part", "vendor", "process"):
                                        col = mcols.get(key)
                                        if col:
                                            view_cols.append(col)
                                    st.write("Select an RFQ from master:")
                                    view_df = cands[view_cols].copy() if view_cols else cands.copy()
                                    st.dataframe(view_df, width='stretch', hide_index=True)

                                    labels = []
                                    for _, r in cands.iterrows():
                                        rfq = str(r[mcols["rfq"]]) if mcols.get("rfq") else ""
                                        partv = str(r[mcols["part"]]) if mcols.get("part") else ""
                                        vendv = str(r[mcols["vendor"]]) if mcols.get("vendor") else ""
                                        procv = str(r[mcols["process"]]) if mcols.get("process") else ""
                                        labels.append(f"RFQ {rfq} — {partv} — {vendv} — {procv}")

                                    pick = st.selectbox(
                                        "RFQ selection",
                                        options=labels,
                                        index=0 if labels else None,
                                        key="responses_pick_master",
                                    )
                                    if pick:
                                        try:
                                            idx = labels.index(pick)
                                            row = cands.iloc[idx]
                                            selected_rfq_num_val = str(row[mcols["rfq"]]) if mcols.get("rfq") else ""
                                            selected_part_val = str(row[mcols["part"]]) if mcols.get("part") else ""
                                            selected_vendor_val = str(row[mcols["vendor"]]) if mcols.get(
                                                "vendor") else ""
                                            selected_process_val = str(row[mcols["process"]]) if mcols.get(
                                                "process") else ""
                                            # Also populate QT/SO # and Qty from the selected master row when available
                                            try:
                                                qtso_col = _find_col(master_df, [
                                                    "qt/so #", "qt/so#", "qt so #", "qt", "so", "quote", "so #", "qt #"
                                                ])
                                                if qtso_col and qtso_col in row:
                                                    selected_qtso_val = str(row[qtso_col]) if pd.notna(row[qtso_col]) else ""
                                            except Exception:
                                                pass
                                            try:
                                                qty_col = _find_col(master_df, [
                                                    "qty", "quantity", "quantities", "order qty", "order quantity", "rfq qty"
                                                ])
                                                if qty_col and qty_col in row:
                                                    selected_qty_val = str(row[qty_col]) if pd.notna(row[qty_col]) else ""
                                            except Exception:
                                                pass
                                        except Exception:
                                            pass

                        if not selected_vendor_val:
                            selected_vendor_val = vendor_guess or ""

                        # If we have a tabular preview, try to prefill fields from its first row
                        try:
                            if ext in ("csv", "xls", "xlsx") and isinstance(preview_data, dict) and "dataframe" in preview_data:
                                dfp0 = preview_data["dataframe"]
                                if isinstance(dfp0, pd.DataFrame) and not dfp0.empty:
                                    r0 = dfp0.iloc[0]
                                    def _get_col(df_, names):
                                        c = _find_col(df_, names)
                                        return str(r0[c]) if c and c in df_.columns and pd.notna(r0[c]) else ""
                                    # Prefill only if not already set by auto-match
                                    if not selected_rfq_num_val:
                                        selected_rfq_num_val = _get_col(dfp0, ["rfq#", "rfq #", "rfqno", "rfqid"]) or selected_rfq_num_val
                                    if not selected_part_val:
                                        selected_part_val = _get_col(dfp0, ["part_number", "part number", "part", "pn"]) or selected_part_val
                                    if not selected_process_val:
                                        selected_process_val = _get_col(dfp0, ["process"]) or selected_process_val
                                    if not selected_vendor_val:
                                        selected_vendor_val = _get_col(dfp0, ["vendor", "vendor_name", "vendor name"]) or selected_vendor_val
                                    # Extras
                                    try:
                                        selected_qtso_val
                                    except NameError:
                                        selected_qtso_val = ""
                                    try:
                                        selected_rev_val
                                    except NameError:
                                        selected_rev_val = ""
                                    try:
                                        selected_qty_val
                                    except NameError:
                                        selected_qty_val = ""
                                    try:
                                        selected_contact_val
                                    except NameError:
                                        selected_contact_val = ""
                                    qtso_from = _get_col(dfp0, ["qt/so #", "qt/so#", "qt", "so", "quote", "so #", "qt #"]) or ""
                                    rev_from = _get_col(dfp0, ["rev", "revision", "rev_level", "revision level"]) or ""
                                    qty_from = _get_col(dfp0, ["qty", "quantity", "quantities", "order qty", "order quantity"]) or ""
                                    contact_from = _get_col(dfp0, ["contact", "contact_email", "email", "contact email"]) or ""
                                    if not selected_qtso_val:
                                        selected_qtso_val = qtso_from or selected_qtso_val
                                    if not selected_rev_val:
                                        selected_rev_val = rev_from or selected_rev_val
                                    if not selected_qty_val:
                                        selected_qty_val = qty_from or selected_qty_val
                                    if not selected_contact_val:
                                        selected_contact_val = contact_from or selected_contact_val
                                    # Pull received timestamp and potential validity/scope for later UI defaults
                                    received_from = _get_col(dfp0, ["received_timestamp", "received ts", "received", "date", "timestamp"]) or ""
                                    valid_through_from = _get_col(dfp0, ["valid_through", "valid through", "expires", "expiration", "expiry", "good_through"]) or ""
                                    scope_from = _get_col(dfp0, ["scope_notes", "scope notes", "notes", "description", "details"]) or ""
                                    if received_from:
                                        received_ts = received_from
                                    # Store these into session state for later defaulting in the UI if desired
                                    st.session_state["responses_valid_through_from_table"] = valid_through_from
                                    st.session_state["responses_scope_from_table"] = scope_from
                        except Exception:
                            pass

                        # -- Scrape extracted values you requested --
                        unit_price_val = ""
                        lot_min_val = ""
                        lead_time_days_val = None
                        scope_notes_val = ""

                        raw_text_for_scrape = body_excerpt or (subject or "")

                        # If table preview exists (CSV/XLSX), try columns first
                        if ext in ("csv", "xls", "xlsx") and "dataframe" in preview_data:
                            try:
                                dfp = preview_data["dataframe"]
                                col_price = _find_col(dfp, ["unit_price", "unit price", "price", "unit cost", "cost"])
                                if col_price and unit_price_val == "":
                                    unit_price_val = str(dfp[col_price].iloc[0])

                                col_lot = _find_col(dfp, ["lot_min", "lot min", "min_lot", "minimum lot", "min order",
                                                          "moq"])
                                if col_lot and not lot_min_val:
                                    lot_min_val = str(dfp[col_lot].iloc[0])

                                col_lead = _find_col(dfp, ["lead_time_days", "lead time days", "lead_time", "lead time",
                                                           "lt days", "lt"])
                                if col_lead and lead_time_days_val is None:
                                    lead_time_days_val = int(
                                        pd.to_numeric(dfp[col_lead].iloc[0], errors="coerce")) if pd.notna(
                                        dfp[col_lead].iloc[0]) else None
                            except Exception:
                                pass

                        # Fallback: scrape from text
                        if not unit_price_val:
                            unit_price_val = _scrape_numbers_like_money(raw_text_for_scrape)
                        if not lot_min_val:
                            lot_min_val = _scrape_lot_min(raw_text_for_scrape)
                        if lead_time_days_val is None:
                            lead_time_days_val = _scrape_lead_time_days(raw_text_for_scrape)
                        scope_notes_val = _safe_preview_text(raw_text_for_scrape, limit=500)

                        # -- Final confirmation UI (replaces the old one) --
                        with st.expander("Record this processing in rfq_responses.csv?", expanded=True):
                            # Build options from master
                            rfq_options = _rfq_options_from_master(master_df)

                            if rfq_options:
                                # Preselect if there’s an inferred value
                                preselect = selected_rfq_num_val if selected_rfq_num_val in rfq_options else None
                                idx = rfq_options.index(preselect) if preselect in rfq_options else 0
                                rfq_num_in = st.selectbox("RFQ #", options=rfq_options, index=idx)
                            else:
                                # Fallback if master is empty or RFQ column not found
                                rfq_num_in = st.text_input("RFQ #", value=selected_rfq_num_val)
                                src = "Box" if getattr(get_tracker(), "master_store", None) is not None else "local"
                                try:
                                    mdf = master_df if isinstance(master_df, pd.DataFrame) else pd.DataFrame()
                                    st.caption(f"RFQ dropdown unavailable — RFQ master empty or RFQ column not found. Source: {src}; columns: {list(mdf.columns) if not mdf.empty else '[]'}")
                                except Exception:
                                    st.caption("RFQ dropdown unavailable — RFQ master empty or RFQ column not found.")

                            part_in = st.text_input("Part #", value=selected_part_val)
                            process_in = st.text_input("Process", value=selected_process_val)
                            vendor_in = st.text_input("Vendor", value=selected_vendor_val)
                            # From master (editable)
                            qtso_in = st.text_input("QT/SO #", value=selected_qtso_val)
                            rev_in = st.text_input("Rev", value=selected_rev_val)
                            qty_in = st.text_input("Qty", value=selected_qty_val)
                            # Default contact: sender email if available
                            contact_default = selected_contact_val or _extract_email_address(email_from)
                            contact_in = st.text_input("Contact", value=contact_default)

                            # No-Quote control
                            nq_mark = st.checkbox("Mark as No-Quote (NQ)", key="nq_mark_master")

                            if nq_mark:
                                # Force values to NQ and render as disabled for clarity
                                unit_price_in = st.text_input("Unit price", value="NQ", disabled=True)
                                lot_min_in = st.text_input("Lot min", value="NQ", disabled=True)
                            else:
                                unit_price_in = st.text_input("Unit price", value=str(unit_price_val or ""))
                                lot_min_in = st.text_input("Lot min", value=str(lot_min_val or ""))

                            # Default lead time to 7 days if not parsed/found
                            default_lead = int(lead_time_days_val) if isinstance(lead_time_days_val, int) else 7
                            lead_time_in = st.number_input(
                                "Lead time (days)",
                                value=default_lead,
                                min_value=0, step=1
                            )
                            received_ts_in = st.text_input("Received timestamp (ISO)", value=str(received_ts))
                            # Use prefilled scope/valid_through from table if available
                            pref_valid = st.session_state.get("responses_valid_through_from_table", "")
                            pref_scope = scope_notes_val or st.session_state.get("responses_scope_from_table", "")

                            # Require a reason when NQ is marked; otherwise optional
                            nq_reason = ""
                            if nq_mark:
                                nq_reason = st.text_area("Reason for no-quote (required)", value="")
                            scope_notes_in = st.text_area("Scope notes", value=pref_scope)
                            # Valid-through quick picks: default to 30 days unless pref_valid already provided
                            from datetime import datetime, timedelta
                            base_dt = None
                            try:
                                base_dt = datetime.fromisoformat(str(received_ts).replace("Z", "+00:00"))
                            except Exception:
                                try:
                                    base_dt = datetime.utcnow()
                                except Exception:
                                    base_dt = None
                            # Determine initial valid value
                            if str(pref_valid).strip():
                                valid_default = str(pref_valid)
                            else:
                                try:
                                    valid_default = (base_dt + timedelta(days=30)).date().isoformat() if base_dt else ""
                                except Exception:
                                    valid_default = ""
                            col_v1, col_v2, col_v3, col_v4 = st.columns(4)
                            valid_choice = None
                            with col_v1:
                                if st.button("30 days", key="valid_30_master"):
                                    valid_choice = 30
                            with col_v2:
                                if st.button("60 days", key="valid_60_master"):
                                    valid_choice = 60
                            with col_v3:
                                if st.button("90 days", key="valid_90_master"):
                                    valid_choice = 90
                            with col_v4:
                                st.caption("Quick set Valid through")
                            # Compute chosen value if any
                            if valid_choice and base_dt:
                                valid_default = (base_dt + timedelta(days=valid_choice)).date().isoformat()
                            valid_through_in = st.text_input("Valid through (date or notes)", value=valid_default)

                            # subject_val = st.text_input("Subject (if email)", value=subject or "")
                            base_notes = f"Processed preview for {selected_name}"
                            notes_val = st.text_area("Notes", value=base_notes)

                            # Suggest adjusting vendor approvals (stub for now)
                            if nq_mark:
                                st.info(f"No-Quote flagged for Vendor '{vendor_in}' on Process '{process_in}'. Consider updating vendor approvals to exclude this process/spec.")
                                st.button("Open Vendors (adjust approvals)", key="open_vendors_from_nq_master", disabled=True)

                            overwrite_ok = st.checkbox("Overwrite existing log entry", key="overwrite_confirm_master")

                            if st.button("Confirm and append record", key="confirm_append_response_record_master"):
                                try:
                                    tracker = get_tracker()
                                    try:
                                        df_curr = tracker.responses_store.load_df() if tracker.responses_store is not None else None
                                    except Exception:
                                        df_curr = None
                                    if df_curr is None:
                                        df_curr = pd.DataFrame()

                                    needed_cols = [
                                        "processed_at", "file_id", "file_name", "quote_folder",
                                        "rfq#", "part_number", "process", "vendor",
                                        "qt/so #", "qty", "contact",
                                        "unit_price", "lot_min", "lead_time_days", "received_timestamp",
                                        "scope_notes", "valid_through", "notes",
                                    ]
                                    for c in needed_cols:
                                        if c not in df_curr.columns:
                                            df_curr[c] = pd.Series(dtype="object")

                                    # If NQ is marked, enforce values and inject reason
                                    if 'nq_mark_master' in st.session_state and st.session_state['nq_mark_master']:
                                        # Validate reason
                                        if not (locals().get('nq_reason', '') or '').strip():
                                            st.error("Please provide a reason for the no-quote.")
                                            return
                                        unit_price_in = "NQ"
                                        lot_min_in = "NQ"
                                        reason_txt = (locals().get('nq_reason', '') or '').strip()
                                        prefix = f"no quote per vendor — {reason_txt}"
                                        scope_notes_in = (prefix + (f" | {scope_notes_in}" if str(scope_notes_in).strip() else ""))
                                        notes_val = (prefix + (f" | {notes_val}" if str(notes_val).strip() else ""))

                                    new_row = pd.DataFrame([{
                                        "processed_at": _now_utc_iso(),
                                        "file_id": selected_id,
                                        "file_name": selected_name,
                                        "quote_folder": "",  # will set after Box move
                                        "rfq#": rfq_num_in,
                                        "part_number": part_in,
                                        "process": process_in,
                                        "vendor": vendor_in,
                                        "qt/so #": qtso_in,
                                        "qty": qty_in,
                                        "contact": contact_in,
                                        "unit_price": unit_price_in,
                                        "lot_min": lot_min_in,
                                        "lead_time_days": str(lead_time_in),
                                        "received_timestamp": received_ts_in,
                                        "scope_notes": scope_notes_in,
                                        "valid_through": valid_through_in,
                                        "notes": notes_val or "",
                                    }])

                                    # Duplicate detection by file_id (Box) or fallback rfq#+file_name
                                    dup_mask = pd.Series(False, index=df_curr.index)
                                    try:
                                        if "file_id" in df_curr.columns:
                                            dup_mask = dup_mask | (df_curr["file_id"].astype(str) == str(selected_id))
                                    except Exception:
                                        pass
                                    try:
                                        if not dup_mask.any() and "rfq#" in df_curr.columns and "file_name" in df_curr.columns:
                                            dup_mask = (df_curr["rfq#"].astype(str).str.strip() == str(rfq_num_in).strip()) & \
                                                       (df_curr["file_name"].astype(str).str.strip().str.lower() == str(selected_name or "").strip().lower())
                                    except Exception:
                                        pass

                                    if dup_mask.any():
                                        st.warning("This response is already logged — would you like to overwrite the log?")
                                        if overwrite_ok:
                                            try:
                                                df_kept = df_curr[~dup_mask].copy()
                                                df_out = pd.concat([df_kept, new_row], ignore_index=True)
                                            except Exception:
                                                df_out = pd.concat([df_curr, new_row], ignore_index=True)
                                        else:
                                            st.info("Canceled. Existing log kept unchanged.")
                                            return
                                    else:
                                        df_out = pd.concat([df_curr, new_row], ignore_index=True)

                                    save_responses_df(df_out)
                                    st.success(
                                        f"Saved record to rfq_responses.csv. Total rows: {len(df_out)}")

                                    # After save: attempt to move the processed file to the RFQ folder (Box only)
                                    try:
                                        store = getattr(tracker, "responses_store", None)
                                        box = getattr(store, "box", None) if store else None
                                        client = getattr(box, "client", None) if box else None
                                        rfq_num_clean = str(rfq_num_in).strip()
                                        if client and str(selected_id).isdigit() and rfq_num_clean:
                                            # Folder move is already attempted above
                                            rfq_folder_id = _get_rfq_folder_id(client, rfq_num_clean)
                                            if rfq_folder_id:
                                                quote_url = f"https://app.box.com/folder/{rfq_folder_id}"
                                                mask = (df_out["file_id"].astype(str) == str(selected_id)) & \
                                                       (df_out["rfq#"].astype(str).str.strip() == rfq_num_clean)
                                                if "quote_folder" in df_out.columns:
                                                    df_out.loc[mask, "quote_folder"] = quote_url
                                                    if tracker.responses_store is not None:
                                                        tracker.responses_store.save_df(df_out)
                                                    else:
                                                        df_out.to_csv(tracker.responses_path, index=False)
                                    except Exception as me:
                                        logger.warning(f"Setting quote_folder skipped/failed: {me}")

                                    # Stash a pending move across rerun, then clear form and rerun
                                    try:
                                        st.session_state["responses_pending_move"] = {"file_id": selected_id, "rfq": rfq_num_in}
                                    except Exception:
                                        pass
                                    _clear_response_form_state()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to append/overwrite record: {e}")


                    except Exception as e:
                        st.error(f"Processing failed: {e}")

        except Exception as e:
            st.error(f"Failed to list files in the Responses folder: {e}")

    # List files available to process in the Responses folder (always visible)
    st.subheader("Files in Responses folder")
    try:
        tracker = get_tracker()
        store = getattr(tracker, "responses_store", None)
        box = getattr(store, "box", None) if store else None
        client = getattr(box, "client", None) if box else None

        # Resolve target folder id using authoritative parent-of-file when possible
        target_folder_id = None
        file_parent_id = None
        explicit_folder_id = None
        try:
            if store and getattr(store, "file_id", None) and client:
                try:
                    _f = client.file(store.file_id).get()
                    if getattr(_f, "parent", None) and getattr(_f.parent, "id", None):
                        file_parent_id = _f.parent.id
                except Exception:
                    file_parent_id = None
            if store and getattr(store, "folder_id", None):
                explicit_folder_id = store.folder_id
            target_folder_id = file_parent_id or explicit_folder_id
            if not target_folder_id:
                try:
                    from core.secrets import get_section as _get_secret_section
                    _bx = _get_secret_section("box") or {}
                    val = str(_bx.get("BOX_RFQ_RESPONSES_FOLDER_ID", "")).strip()
                    target_folder_id = val or None
                except Exception:
                    target_folder_id = None
            if file_parent_id and explicit_folder_id and file_parent_id != explicit_folder_id:
                # Prefer file parent (should be 'Responses')
                target_folder_id = file_parent_id
        except Exception:
            target_folder_id = None

        def _hr_size(n) -> str:
            try:
                n = int(n or 0)
                for unit in ["B", "KB", "MB", "GB", "TB"]:
                    if n < 1024 or unit == "TB":
                        return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
                    n /= 1024
            except Exception:
                return ""

        selected_id = None
        selected_name = None

        if client and target_folder_id:
            # Show folder context
            try:
                folder_obj = client.folder(target_folder_id).get()
                st.caption(f"Listing: Box folder {target_folder_id} — {getattr(folder_obj, 'name', '(unknown)')}")
            except Exception:
                st.caption(f"Listing: Box folder {target_folder_id}")

            # Fetch first page of items
            try:
                items = list(client.folder(target_folder_id).get_items(limit=1000, fields=["id","name","size","modified_at","sha1"]))
            except Exception as e:
                items = []
                st.error(f"Failed to list Box folder items: {e}")

            files = []
            for it in items:
                try:
                    if getattr(it, "type", None) == "file":
                        files.append({
                            "id": getattr(it, "id", ""),
                            "name": getattr(it, "name", ""),
                            "size": getattr(it, "size", 0),
                            "modified_at": getattr(it, "modified_at", ""),
                        })
                except Exception:
                    pass

            if files:
                df_files = pd.DataFrame(files)
                if not df_files.empty:
                    # Exclude the tracking CSV from processing list
                    try:
                        df_files = df_files[df_files["name"].str.lower() != "rfq_responses.csv"]
                    except Exception:
                        pass
                    # Sort newest first by modified_at (if available)
                    try:
                        df_files["modified_at_dt"] = pd.to_datetime(df_files["modified_at"], errors="coerce")
                        df_files = df_files.sort_values("modified_at_dt", ascending=False)
                    except Exception:
                        pass
                    # Prettify size
                    try:
                        df_files["size_readable"] = df_files["size"].apply(_hr_size)
                    except Exception:
                        df_files["size_readable"] = df_files["size"]
                    # Show a small summary and a manual reload trigger (clicking will rerun)
                    st.caption(f"{len(df_files)} file(s) found. Click 'Reload file list' to refresh.")
                    st.button("Reload file list", key="responses_reload_list")
                    # Display
                    cols = [c for c in ["name", "size_readable", "modified_at", "id"] if c in df_files.columns]
                    st.dataframe(df_files[cols], width='stretch', hide_index=True)

                    # Selection UI
                    labels = [f"{row['name']} (id {row['id']}, {_hr_size(row['size'])})" for _, row in df_files.iterrows()]
                    selected_label = st.selectbox(
                        "Select a file to process",
                        options=labels,
                        index=0 if labels else None,
                        key="responses_select_file_always",
                    )
                    if selected_label:
                        try:
                            idx = labels.index(selected_label)
                            selected_id = str(df_files.iloc[idx]["id"]) if "id" in df_files.columns else None
                            selected_name = str(df_files.iloc[idx]["name"]) if "name" in df_files.columns else None
                        except Exception:
                            selected_id = None
                            selected_name = None
            else:
                st.info("No files found in the Responses folder.")
        else:
            # Local fallback listing
            try:
                local_base = getattr(tracker, "responses_path", None)
                if local_base is not None:
                    local_folder = local_base.parent / "responses_uploads"
                    local_folder.mkdir(parents=True, exist_ok=True)
                    local_files = []
                    for p in sorted(local_folder.glob("*")):
                        if p.is_file():
                            stat = p.stat()
                            local_files.append({
                                "path": str(p),
                                "name": p.name,
                                "size": stat.st_size,
                                "modified_at": pd.to_datetime(stat.st_mtime, unit='s').isoformat() if hasattr(pd, 'to_datetime') else str(stat.st_mtime),
                            })
                    if local_files:
                        df_local = pd.DataFrame(local_files)
                        try:
                            df_local["size_readable"] = df_local["size"].apply(_hr_size)
                        except Exception:
                            df_local["size_readable"] = df_local["size"]
                        cols = [c for c in ["name", "size_readable", "modified_at", "path"] if c in df_local.columns]
                        st.dataframe(df_local[cols], width='stretch', hide_index=True)
                        labels = [f"{row['name']} ({_hr_size(row['size'])})" for _, row in df_local.iterrows()]
                        selected_label = st.selectbox(
                            "Select a local file to process",
                            options=labels,
                            index=0 if labels else None,
                            key="responses_select_file_local_always",
                        )
                        if selected_label:
                            try:
                                idx = labels.index(selected_label)
                                selected_id = str(df_local.iloc[idx]["path"])  # reuse as id in local mode
                                selected_name = str(df_local.iloc[idx]["name"]) if "name" in df_local.columns else None
                            except Exception:
                                selected_id = None
                                selected_name = None
                    else:
                        st.info("No local files found in responses_uploads.")
                else:
                    st.info("Box not configured and no local fallback folder available.")
            except Exception as e:
                st.error(f"Failed to list local uploads: {e}")

        # If we have a selected file, offer processing
        if selected_id:
            st.session_state["responses_selected_file_id"] = selected_id
            st.session_state["responses_selected_file_name"] = selected_name

            # New: Allow sending file to RFQ folder without logging to CSV
            with st.expander("Send file to RFQ folder (no log)", expanded=False):
                rfq_options = _rfq_options_from_master(_load_master_df())
                if rfq_options:
                    rfq_move_in2 = st.selectbox(
                        "RFQ # to send file to (no log)",
                        options=rfq_options,
                        index=0,
                        key="responses_move_rfq_always",
                    )
                else:
                    rfq_move_in2 = st.text_input(
                        "RFQ # to send file to (no log)",
                        value="",
                        key="responses_move_rfq_always"
                    )
                    try:
                        mdf2 = _load_master_df()
                        src2 = "Box" if getattr(get_tracker(), "master_store", None) is not None else "local"
                        st.caption(f"RFQ dropdown unavailable — RFQ master empty or RFQ column not found. Source: {src2}; columns: {list(mdf2.columns) if not mdf2.empty else '[]'}")
                    except Exception:
                        st.caption("RFQ dropdown unavailable — RFQ master empty or RFQ column not found.")
                col_mvA, col_mvB = st.columns([1, 5])
                with col_mvA:
                    if st.button("Send file to RFQ folder (no log)", key="responses_send_only_always"):
                        try:
                            rfq_num_clean2 = str(rfq_move_in2 or "").strip()
                            if not rfq_num_clean2:
                                st.warning("Please enter an RFQ #.")
                            else:
                                # Only supported in Box mode with numeric file id
                                if client and str(selected_id).isdigit():
                                    res = _move_file_to_rfq_folder(client, str(selected_id), rfq_num_clean2)
                                    if res.get("ok"):
                                        st.success(f"{res.get('message','Moved')} — file sent to RFQ {rfq_num_clean2}")
                                    else:
                                        st.warning(f"Move failed/skipped: {res.get('message','unknown')}")
                                else:
                                    st.info("Sending to RFQ folder is only available when Box is configured.")
                        except Exception as _merr2:
                            st.error(f"Move failed: {_merr2}")

            start_processing = st.button("Process selected file", key="process_selected_response_file_always")
            if start_processing:
                st.session_state["responses_processing_active"] = True
                st.session_state["responses_selected_file_id"] = selected_id
                st.session_state["responses_selected_file_name"] = selected_name

            # Use session state to persist processing UI across reruns (e.g., when selecting an RFQ)
            processing_active = st.session_state.get("responses_processing_active", False)
            sess_selected_id = st.session_state.get("responses_selected_file_id")
            sess_selected_name = st.session_state.get("responses_selected_file_name")

            if processing_active and sess_selected_id:
                # Allow canceling processing mode
                col_a, col_b = st.columns([1, 4])
                with col_a:
                    if st.button("Cancel processing", key="responses_cancel_processing"):
                        st.session_state["responses_processing_active"] = False
                        st.stop()  # stop to avoid rendering stale UI; next run shows list again

                try:
                    # Use the persisted selection
                    selected_id = str(sess_selected_id)
                    selected_name = sess_selected_name

                    raw = None
                    ext = ""
                    mime = ""

                    # Box mode
                    if client and str(selected_id).isdigit():
                        raw = _download_box_file_bytes(client, selected_id)
                        ext, mime = _detect_filetype(selected_name)
                    else:
                        # Local mode: selected_id is a path
                        try:
                            p = Path(selected_id)
                            raw = p.read_bytes()
                            ext, mime = _detect_filetype(selected_name or p.name)
                        except Exception as le:
                            raise RuntimeError(f"Failed to read local file: {le}")

                    st.caption(f"Detected type: .{ext or '(none)'} — {mime or ''}")

                    preview_data = {}
                    subject = ""
                    email_from = ""
                    body_excerpt = ""
                    vendor_guess = ""

                    # Parse previews
                    if ext in ("eml",):
                        preview_data = _try_parse_eml(raw)
                        if "error" in preview_data:
                            st.warning(preview_data["error"])
                        else:
                            subject = preview_data.get("subject", "")
                            email_from = preview_data.get("from", "")
                            body_excerpt = _safe_preview_text(preview_data.get("body", ""))
                            # Prefer contacts-based vendor mapping
                            try:
                                tracker = get_tracker()
                                domain_map = _build_domain_vendor_map(getattr(tracker, "contacts_df", pd.DataFrame()))
                            except Exception:
                                domain_map = {}
                            vendor_from_contacts = _vendor_from_sender_domain(email_from, domain_map)
                            vendor_guess = vendor_from_contacts or _guess_vendor(selected_name, email_from, body_excerpt)
                            st.write(f"Subject: {subject}")
                            st.write(f"From: {email_from}")
                            st.caption("Vendor source: " + ("contacts.csv domain→vendor" if vendor_from_contacts else "heuristic guess"))
                            st.text_area("Body preview", body_excerpt, height=200)
                            _render_attachments(preview_data, str(selected_id))

                    elif ext in ("msg",):
                        preview_data = _try_parse_msg(raw)
                        if "error" in preview_data:
                            st.warning(preview_data["error"])
                        else:
                            subject = preview_data.get("subject", "")
                            email_from = preview_data.get("from", "")
                            body_excerpt = _safe_preview_text(preview_data.get("body", ""))
                            # Prefer contacts-based vendor mapping
                            try:
                                tracker = get_tracker()
                                domain_map = _build_domain_vendor_map(getattr(tracker, "contacts_df", pd.DataFrame()))
                            except Exception:
                                domain_map = {}
                            vendor_from_contacts = _vendor_from_sender_domain(email_from, domain_map)
                            vendor_guess = vendor_from_contacts or _guess_vendor(selected_name, email_from, body_excerpt)
                            st.write(f"Subject: {subject}")
                            st.write(f"From: {email_from}")
                            st.caption("Vendor source: " + ("contacts.csv domain→vendor" if vendor_from_contacts else "heuristic guess"))
                            st.text_area("Body preview", body_excerpt, height=200)
                            _render_attachments(preview_data, str(selected_id))

                    elif ext in ("csv", "xls", "xlsx"):
                        preview_data = _try_parse_tabular(ext, raw)
                        if "dataframe" in preview_data:
                            st.write("Preview of first 10 rows:")
                            st.dataframe(preview_data["dataframe"], width='stretch', hide_index=True)
                            vendor_guess = _guess_vendor(selected_name)
                        else:
                            st.warning(preview_data.get("error", "Failed to parse table."))

                    elif ext in ("pdf",):
                        preview_data = _try_parse_pdf(raw)
                        if "text_preview" in preview_data:
                            st.text_area("PDF page 1 text preview", _safe_preview_text(preview_data["text_preview"]), height=200)
                            vendor_guess = _guess_vendor(selected_name)
                        else:
                            st.warning(preview_data.get("error", "Failed to parse PDF."))

                    elif ext in ("txt",):
                        try:
                            text = raw.decode("utf-8", errors="replace")
                        except Exception:
                            text = ""
                        body_excerpt = _safe_preview_text(text)
                        vendor_guess = _guess_vendor(selected_name)
                        st.text_area("Text preview", body_excerpt, height=200)

                    else:
                        st.info("No parser for this file type yet. You can still record a processed entry.")
                        vendor_guess = _guess_vendor(selected_name)

                    # -- Load RFQ master and try to match RFQ --
                    master_df = _load_master_df()
                    mcols = _master_cols(master_df)

                    selected_rfq_num_val = ""
                    selected_part_val = ""
                    selected_vendor_val = ""
                    selected_process_val = ""
                    # Additional values from RFQ master
                    selected_qtso_val = ""
                    selected_rev_val = ""
                    selected_qty_val = ""
                    selected_contact_val = ""
                    received_ts = _first_nonempty(
                        (preview_data.get("date") if isinstance(preview_data, dict) else ""),
                        _now_utc_iso()
                    )

                    if master_df is not None and not master_df.empty:
                        auto = _auto_match_rfq(
                            master_df,
                            selected_name or "",
                            subject or "",
                            body_excerpt or "",
                            vendor_guess or "",
                        )
                        if auto.get("match") is not None:
                            row = auto["match"]
                            try:
                                selected_rfq_num_val = str(row[mcols.get("rfq")]) if mcols.get("rfq") else ""
                                selected_part_val = str(row[mcols.get("part")]) if mcols.get("part") else ""
                                selected_vendor_val = str(row[mcols.get("vendor")]) if mcols.get("vendor") else ""
                                selected_process_val = str(row[mcols.get("process")]) if mcols.get("process") else ""
                                # Populate Qty from RFQ Master when available (include template header "quantities")
                                try:
                                    qty_col = _find_col(master_df, [
                                        "qty", "quantity", "quantities", "order qty", "order quantity", "rfq qty"
                                    ])
                                    if qty_col and qty_col in row:
                                        selected_qty_val = str(row[qty_col]) if pd.notna(row[qty_col]) else ""
                                except Exception:
                                    pass
                                # Populate QT/SO # from RFQ Master when available
                                try:
                                    qtso_col = _find_col(master_df, [
                                        "qt/so #", "qt/so#", "qt so #", "qt", "so", "quote", "so #", "qt #"
                                    ])
                                    if qtso_col and qtso_col in row:
                                        selected_qtso_val = str(row[qtso_col]) if pd.notna(row[qtso_col]) else ""
                                except Exception:
                                    pass
                                st.success(
                                    f"Auto-matched RFQ: RFQ {selected_rfq_num_val} — {selected_part_val} — {selected_vendor_val} — {selected_process_val}"
                                )
                            except Exception:
                                pass
                        else:
                            cands = auto.get("candidates") if isinstance(auto.get("candidates"), pd.DataFrame) else pd.DataFrame()
                            if not cands.empty:
                                view_cols = []
                                for key in ("rfq", "part", "vendor", "process"):
                                    col = mcols.get(key)
                                    if col:
                                        view_cols.append(col)
                                st.write("Select an RFQ from master:")
                                view_df = cands[view_cols].copy() if view_cols else cands.copy()
                                st.dataframe(view_df, width='stretch', hide_index=True)

                                labels = []
                                for _, r in cands.iterrows():
                                    rfq = str(r[mcols["rfq"]]) if mcols.get("rfq") else ""
                                    partv = str(r[mcols["part"]]) if mcols.get("part") else ""
                                    vendv = str(r[mcols["vendor"]]) if mcols.get("vendor") else ""
                                    procv = str(r[mcols["process"]]) if mcols.get("process") else ""
                                    labels.append(f"RFQ {rfq} — {partv} — {vendv} — {procv}")

                                pick = st.selectbox(
                                    "RFQ selection",
                                    options=labels,
                                    index=0 if labels else None,
                                    key="responses_pick_master_always",
                                )
                                if pick:
                                    try:
                                        idx = labels.index(pick)
                                        row = cands.iloc[idx]
                                        selected_rfq_num_val = str(row[mcols["rfq"]]) if mcols.get("rfq") else ""
                                        selected_part_val = str(row[mcols["part"]]) if mcols.get("part") else ""
                                        selected_vendor_val = str(row[mcols["vendor"]]) if mcols.get("vendor") else ""
                                        selected_process_val = str(row[mcols["process"]]) if mcols.get("process") else ""
                                        # Also populate QT/SO # and Qty from the selected master row when available
                                        try:
                                            qtso_col = _find_col(master_df, [
                                                "qt/so #", "qt/so#", "qt so #", "qt", "so", "quote", "so #", "qt #"
                                            ])
                                            if qtso_col and qtso_col in row:
                                                selected_qtso_val = str(row[qtso_col]) if pd.notna(row[qtso_col]) else ""
                                        except Exception:
                                            pass
                                        try:
                                            qty_col = _find_col(master_df, [
                                                "qty", "quantity", "quantities", "order qty", "order quantity", "rfq qty"
                                            ])
                                            if qty_col and qty_col in row:
                                                selected_qty_val = str(row[qty_col]) if pd.notna(row[qty_col]) else ""
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass

                    if not selected_vendor_val:
                        selected_vendor_val = vendor_guess or ""

                    # If we have a tabular preview, try to prefill fields from its first row
                    try:
                        if ext in ("csv", "xls", "xlsx") and isinstance(preview_data, dict) and "dataframe" in preview_data:
                            dfp0 = preview_data["dataframe"]
                            if isinstance(dfp0, pd.DataFrame) and not dfp0.empty:
                                r0 = dfp0.iloc[0]
                                def _get_col(df_, names):
                                    c = _find_col(df_, names)
                                    return str(r0[c]) if c and c in df_.columns and pd.notna(r0[c]) else ""
                                # Prefill only if not already set by auto-match
                                if not selected_rfq_num_val:
                                    selected_rfq_num_val = _get_col(dfp0, ["rfq#", "rfq #", "rfqno", "rfqid"]) or selected_rfq_num_val
                                if not selected_part_val:
                                    selected_part_val = _get_col(dfp0, ["part_number", "part number", "part", "pn"]) or selected_part_val
                                if not selected_process_val:
                                    selected_process_val = _get_col(dfp0, ["process"]) or selected_process_val
                                if not selected_vendor_val:
                                    selected_vendor_val = _get_col(dfp0, ["vendor", "vendor_name", "vendor name"]) or selected_vendor_val
                                # Extras
                                qtso_from = _get_col(dfp0, ["qt/so #", "qt/so#", "qt", "so", "quote", "so #", "qt #"]) or ""
                                rev_from = _get_col(dfp0, ["rev", "revision", "rev_level", "revision level"]) or ""
                                qty_from = _get_col(dfp0, ["qty", "quantity", "quantities", "order qty", "order quantity"]) or ""
                                contact_from = _get_col(dfp0, ["contact", "contact_email", "email", "contact email"]) or ""
                                if not selected_qtso_val:
                                    selected_qtso_val = qtso_from or selected_qtso_val
                                if not selected_rev_val:
                                    selected_rev_val = rev_from or selected_rev_val
                                if not selected_qty_val:
                                    selected_qty_val = qty_from or selected_qty_val
                                if not selected_contact_val:
                                    selected_contact_val = contact_from or selected_contact_val
                                # Pull received timestamp and potential validity/scope for later UI defaults
                                received_from = _get_col(dfp0, ["received_timestamp", "received ts", "received", "date", "timestamp"]) or ""
                                valid_through_from = _get_col(dfp0, ["valid_through", "valid through", "expires", "expiration", "expiry", "good_through"]) or ""
                                scope_from = _get_col(dfp0, ["scope_notes", "scope notes", "notes", "description", "details"]) or ""
                                if received_from:
                                    received_ts = received_from
                                st.session_state["responses_valid_through_from_table"] = valid_through_from
                                st.session_state["responses_scope_from_table"] = scope_from
                    except Exception:
                        pass

                    # -- Scrape extracted values you requested --
                    unit_price_val = ""
                    lot_min_val = ""
                    lead_time_days_val = None
                    scope_notes_val = ""

                    raw_text_for_scrape = body_excerpt or (subject or "")

                    # If table preview exists (CSV/XLSX), try columns first
                    if ext in ("csv", "xls", "xlsx") and "dataframe" in preview_data:
                        try:
                            dfp = preview_data["dataframe"]
                            col_price = _find_col(dfp, ["unit_price", "unit price", "price", "unit cost", "cost"])
                            if col_price and unit_price_val == "":
                                unit_price_val = str(dfp[col_price].iloc[0])

                            col_lot = _find_col(dfp, ["lot_min", "lot min", "min_lot", "minimum lot", "min order", "moq"])
                            if col_lot and not lot_min_val:
                                lot_min_val = str(dfp[col_lot].iloc[0])

                            col_lead = _find_col(dfp, ["lead_time_days", "lead time days", "lead_time", "lead time", "lt days", "lt"])
                            if col_lead and lead_time_days_val is None:
                                lead_time_days_val = int(pd.to_numeric(dfp[col_lead].iloc[0], errors="coerce")) if pd.notna(dfp[col_lead].iloc[0]) else None
                        except Exception:
                            pass

                    # Fallback: scrape from text
                    if not unit_price_val:
                        unit_price_val = _scrape_numbers_like_money(raw_text_for_scrape)
                    if not lot_min_val:
                        lot_min_val = _scrape_lot_min(raw_text_for_scrape)
                    if lead_time_days_val is None:
                        lead_time_days_val = _scrape_lead_time_days(raw_text_for_scrape)
                    scope_notes_val = _safe_preview_text(raw_text_for_scrape, limit=500)

                    # -- Final confirmation UI (replaces the old one) --
                    with st.expander("Record this processing in rfq_responses.csv?", expanded=True):
                        # Build options from master (same as earlier UI)
                        rfq_options = _rfq_options_from_master(master_df)

                        if rfq_options:
                            preselect = selected_rfq_num_val if selected_rfq_num_val in rfq_options else None
                            idx = rfq_options.index(preselect) if preselect in rfq_options else 0
                            rfq_num_in = st.selectbox("RFQ #", options=rfq_options, index=idx)
                        else:
                            rfq_num_in = st.text_input("RFQ #", value=selected_rfq_num_val)
                            src = "Box" if getattr(get_tracker(), "master_store", None) is not None else "local"
                            try:
                                mdf = master_df if isinstance(master_df, pd.DataFrame) else pd.DataFrame()
                                st.caption(f"RFQ dropdown unavailable — RFQ master empty or RFQ column not found. Source: {src}; columns: {list(mdf.columns) if not mdf.empty else '[]'}")
                            except Exception:
                                st.caption("RFQ dropdown unavailable — RFQ master empty or RFQ column not found.")

                        part_in = st.text_input("Part #", value=selected_part_val)
                        process_in = st.text_input("Process", value=selected_process_val)
                        vendor_in = st.text_input("Vendor", value=selected_vendor_val)
                        # From master (editable)
                        qtso_in = st.text_input("QT/SO #", value=selected_qtso_val)
                        # Rev removed; Qty is auto-filled from RFQ Master but editable
                        qty_in = st.text_input("Qty", value=str(selected_qty_val or ""))
                        # Default contact: sender email if available
                        contact_default = selected_contact_val or _extract_email_address(email_from)
                        contact_in = st.text_input("Contact", value=contact_default)

                        # No-Quote control
                        nq_mark_always = st.checkbox("Mark as No-Quote (NQ)", key="nq_mark_master_always")

                        if nq_mark_always:
                            # Force values to NQ and render as disabled for clarity
                            unit_price_in = st.text_input("Unit price", value="NQ", disabled=True)
                            lot_min_in = st.text_input("Lot min", value="NQ", disabled=True)
                        else:
                            unit_price_in = st.text_input("Unit price", value=str(unit_price_val or ""))
                            lot_min_in = st.text_input("Lot min", value=str(lot_min_val or ""))

                        # Default lead time to 7 days if not parsed/found
                        default_lead = int(lead_time_days_val) if isinstance(lead_time_days_val, int) else 7
                        lead_time_in = st.number_input(
                            "Lead time (days)",
                            value=default_lead,
                            min_value=0, step=1
                        )
                        received_ts_in = st.text_input("Received timestamp (ISO)", value=str(received_ts))
                        pref_valid = st.session_state.get("responses_valid_through_from_table", "")
                        pref_scope = scope_notes_val or st.session_state.get("responses_scope_from_table", "")

                        # Require a reason when NQ is marked; otherwise optional
                        nq_reason_always = ""
                        if nq_mark_always:
                            nq_reason_always = st.text_area("Reason for no-quote (required)", value="")
                        scope_notes_in = st.text_area("Scope notes", value=pref_scope)
                        # Valid-through quick picks: default to 30 days unless pref_valid already provided
                        from datetime import datetime, timedelta
                        base_dt2 = None
                        try:
                            base_dt2 = datetime.fromisoformat(str(received_ts).replace("Z", "+00:00"))
                        except Exception:
                            try:
                                base_dt2 = datetime.utcnow()
                            except Exception:
                                base_dt2 = None
                        if str(pref_valid).strip():
                            valid_default2 = str(pref_valid)
                        else:
                            try:
                                valid_default2 = (base_dt2 + timedelta(days=30)).date().isoformat() if base_dt2 else ""
                            except Exception:
                                valid_default2 = ""
                        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
                        valid_choice2 = None
                        with col_w1:
                            if st.button("30 days", key="valid_30_master_always"):
                                valid_choice2 = 30
                        with col_w2:
                            if st.button("60 days", key="valid_60_master_always"):
                                valid_choice2 = 60
                        with col_w3:
                            if st.button("90 days", key="valid_90_master_always"):
                                valid_choice2 = 90
                        with col_w4:
                            st.caption("Quick set Valid through")
                        if valid_choice2 and base_dt2:
                            valid_default2 = (base_dt2 + timedelta(days=valid_choice2)).date().isoformat()
                        valid_through_in = st.text_input("Valid through (date or notes)", value=valid_default2)

                        # subject_val = st.text_input("Subject (if email)", value=subject or "")
                        base_notes = f"Processed preview for {selected_name}"
                        notes_val = st.text_area("Notes", value=base_notes)

                        # Suggest adjusting vendor approvals (stub for now)
                        if nq_mark_always:
                            st.info(f"No-Quote flagged for Vendor '{vendor_in}' on Process '{process_in}'. Consider updating vendor approvals to exclude this process/spec.")
                            st.button("Open Vendors (adjust approvals)", key="open_vendors_from_nq_master_always", disabled=True)

                        overwrite_ok_always = st.checkbox("Overwrite existing log entry", key="overwrite_confirm_master_always")

                        if st.button("Confirm and append record", key="confirm_append_response_record_master_always"):
                            try:
                                tracker = get_tracker()
                                try:
                                    df_curr = tracker.responses_store.load_df() if tracker.responses_store is not None else None
                                except Exception:
                                    df_curr = None
                                if df_curr is None:
                                    df_curr = pd.DataFrame()

                                needed_cols = [
                                    "processed_at", "file_id", "file_name", "quote_folder",
                                    "rfq#", "part_number", "process", "vendor",
                                    "qt/so #", "qty", "contact",
                                    "unit_price", "lot_min", "lead_time_days", "received_timestamp",
                                    "scope_notes", "valid_through", "notes",
                                ]
                                for c in needed_cols:
                                    if c not in df_curr.columns:
                                        df_curr[c] = pd.Series(dtype="object")

                                # If NQ is marked, enforce values and inject reason
                                if 'nq_mark_master_always' in st.session_state and st.session_state['nq_mark_master_always']:
                                    if not (locals().get('nq_reason_always', '') or '').strip():
                                        st.error("Please provide a reason for the no-quote.")
                                        return
                                    unit_price_in = "NQ"
                                    lot_min_in = "NQ"
                                    reason_txt = (locals().get('nq_reason_always', '') or '').strip()
                                    prefix = f"no quote per vendor — {reason_txt}"
                                    scope_notes_in = (prefix + (f" | {scope_notes_in}" if str(scope_notes_in).strip() else ""))
                                    notes_val = (prefix + (f" | {notes_val}" if str(notes_val).strip() else ""))

                                new_row = pd.DataFrame([{
                                    "processed_at": _now_utc_iso(),
                                    "file_id": selected_id,
                                    "file_name": selected_name,
                                    "quote_folder": "",  # will set after Box move
                                    "rfq#": rfq_num_in,
                                    "part_number": part_in,
                                    "process": process_in,
                                    "vendor": vendor_in,
                                    "qt/so #": qtso_in,
                                    "qty": qty_in,
                                    "contact": contact_in,
                                    "unit_price": unit_price_in,
                                    "lot_min": lot_min_in,
                                    "lead_time_days": str(lead_time_in),
                                    "received_timestamp": received_ts_in,
                                    "scope_notes": scope_notes_in,
                                    "valid_through": valid_through_in,
                                    "notes": notes_val or "",
                                }])

                                # Duplicate detection by file_id (Box) or fallback rfq#+file_name
                                dup_mask = pd.Series(False, index=df_curr.index)
                                try:
                                    if "file_id" in df_curr.columns:
                                        dup_mask = dup_mask | (df_curr["file_id"].astype(str) == str(selected_id))
                                except Exception:
                                    pass
                                try:
                                    if not dup_mask.any() and "rfq#" in df_curr.columns and "file_name" in df_curr.columns:
                                        dup_mask = (df_curr["rfq#"].astype(str).str.strip() == str(rfq_num_in).strip()) & \
                                                   (df_curr["file_name"].astype(str).str.strip().str.lower() == str(selected_name or "").strip().lower())
                                except Exception:
                                    pass

                                if dup_mask.any():
                                    st.warning("This response is already logged — would you like to overwrite the log?")
                                    if overwrite_ok_always:
                                        try:
                                            df_kept = df_curr[~dup_mask].copy()
                                            df_out = pd.concat([df_kept, new_row], ignore_index=True)
                                        except Exception:
                                            df_out = pd.concat([df_curr, new_row], ignore_index=True)
                                    else:
                                        st.info("Canceled. Existing log kept unchanged.")
                                        return
                                else:
                                    df_out = pd.concat([df_curr, new_row], ignore_index=True)

                                if tracker.responses_store is not None:
                                    tracker.responses_store.save_df(df_out)
                                    st.success(f"Saved record to rfq_responses.csv in Box. Total rows: {len(df_out)}")
                                else:
                                    df_out.to_csv(tracker.responses_path, index=False)
                                    st.success(f"Saved record to local rfq_responses.csv. Total rows: {len(df_out)}")

                                # After save: attempt to move the processed file to the RFQ folder (Box only)
                                try:
                                    store = getattr(tracker, "responses_store", None)
                                    box = getattr(store, "box", None) if store else None
                                    client = getattr(box, "client", None) if box else None
                                    rfq_num_clean = str(rfq_num_in).strip()
                                    if client and str(selected_id).isdigit() and rfq_num_clean:
                                        # Folder move is already attempted above
                                        rfq_folder_id = _get_rfq_folder_id(client, rfq_num_clean)
                                        if rfq_folder_id:
                                            quote_url = f"https://app.box.com/folder/{rfq_folder_id}"
                                            mask = (df_out["file_id"].astype(str) == str(selected_id)) & \
                                                   (df_out["rfq#"].astype(str).str.strip() == rfq_num_clean)
                                            if "quote_folder" in df_out.columns:
                                                df_out.loc[mask, "quote_folder"] = quote_url
                                                if tracker.responses_store is not None:
                                                    tracker.responses_store.save_df(df_out)
                                                else:
                                                    df_out.to_csv(tracker.responses_path, index=False)
                                except Exception as me:
                                    logger.warning(f"Setting quote_folder skipped/failed: {me}")

                                # Stash a pending move across rerun, then clear form and rerun
                                try:
                                    st.session_state["responses_pending_move"] = {"file_id": selected_id, "rfq": rfq_num_in}
                                except Exception:
                                    pass
                                _clear_response_form_state()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to append/overwrite record: {e}")

                except Exception as e:
                    st.error(f"Processing failed: {e}")

    except Exception as e:
        st.error(f"Failed to list files in the Responses folder: {e}")

    # Load once initially
    df = _load_responses_df()

    if df is None or df.empty:
        st.info("No responses found yet.")
    else:
        # Filters
        with st.expander("Filters", expanded=False):
            search = st.text_input("Search (matches any column)", "")
            c1, c2 = st.columns(2)
            with c1:
                part_filter = st.text_input("Part number contains", "", placeholder="e.g. 12345 or ABC-001")
            with c2:
                vendor_filter = st.text_input("Vendor contains", "", placeholder="e.g. Acme Metals")

        # Start with full df
        df_filtered = df

        # Apply global search across all columns
        if search:
            try:
                mask = pd.Series(False, index=df_filtered.index)
                for c in df_filtered.columns:
                    mask = mask | df_filtered[c].astype(str).str.contains(search, case=False, na=False)
                df_filtered = df_filtered[mask]
            except Exception:
                pass

        # Apply part number filter
        if part_filter:
            col_part = _find_col(df_filtered, ["part_number", "part number", "part", "pn"])
            if col_part:
                try:
                    mask = df_filtered[col_part].astype(str).str.contains(part_filter, case=False, na=False)
                    df_filtered = df_filtered[mask]
                except Exception:
                    pass

        # Apply vendor filter
        if vendor_filter:
            col_vendor = _find_col(df_filtered, ["vendor", "vendor_name", "vendor name"])
            if col_vendor:
                try:
                    mask = df_filtered[col_vendor].astype(str).str.contains(vendor_filter, case=False, na=False)
                    df_filtered = df_filtered[mask]
                except Exception:
                    pass

        st.dataframe(df_filtered, width='stretch', hide_index=True)

        # Download filtered/current view
        csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="rfq_responses_view.csv",
            mime="text/csv",
            key="download_responses_csv",
        )

    # Refresh from Box button
    if st.button("Refresh from Box", key="refresh_responses_from_box"):
        try:
            tracker = get_tracker()
            if tracker.responses_store is not None:
                refreshed = tracker.responses_store.load_df()
                if refreshed is None:
                    refreshed = pd.DataFrame()
                st.success(f"Loaded {len(refreshed)} row(s) from Box.")
                st.dataframe(refreshed, width='stretch', hide_index=True)
            else:
                st.warning("Box is not configured for rfq_responses.csv; showing local data instead.")
                refreshed = _load_responses_df()
                st.dataframe(refreshed, width='stretch', hide_index=True)
        except Exception as e:
            st.error(f"Refresh from Box failed: {e}")
            logger.exception("Refresh from Box failed for rfq_responses.csv")

    if st.button("Open RFQ Master Editor"):
        st.session_state["return_to_page"] = "Responses"
        st.switch_page("pages/02_Rfq_Master.py")

def main():
    setup_page()

    # Get user info from session
    if "user" not in st.session_state:
        st.warning("Please select a user in the sidebar of the main page.")
        return

    user = st.session_state.user
    role = get_user_role(user)

    # Sidebar info
    st.sidebar.markdown(f"**User:** {user['name']}")
    st.sidebar.markdown(f"**Role:** {role}")

    # Display
    display_responses(user, role)


if __name__ == "__main__":
    main()
