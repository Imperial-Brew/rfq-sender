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
from datetime import datetime

# Require authentication for this page
if not require_authentication():
    st.stop()

# Logger
logger = get_logger(__name__)


def setup_page():
    st.title("RFQ Responses")
    st.markdown(
        """
        View rfq_responses.csv. If Box is configured in secrets, the data is loaded from Box.
        Use the Refresh button to re-load from Box. You can also download the current view as CSV.
        """
    )


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

def _safe_preview_text(txt: str, limit: int = 500) -> str:
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
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
        else:
            if msg.get_content_type() == "text/plain":
                body = msg.get_content()
        return {"subject": subject or "", "from": sender or "", "to": to or "", "date": date or "", "body": body or ""}
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
        return {
            "subject": msg.subject or "",
            "from": msg.sender or "",
            "to": msg.to or "",
            "date": str(msg.date or ""),
            "body": msg.body or "",
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
            df = pd.read_csv(io.BytesIO(content))
        elif ext in ("xls", "xlsx"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            return {"error": f"Unsupported tabular type: {ext}"}
        return {"dataframe": df.head(10)}
    except Exception as e:
        return {"error": f"Tabular parse failed: {e}"}

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
        "rfq": _find_col(df, ["rfq#", "rfq #", "rfqno", "rfqid"]),
        "part": _find_col(df, ["part_number", "part number", "part", "pn"]),
        "vendor": _find_col(df, ["vendor", "vendor_name", "vendor name"]),
        "process": _find_col(df, ["process"]),
    }

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

def display_responses(user, role):
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
        tracker = get_tracker()
        store = getattr(tracker, "responses_store", None)
        box = getattr(store, "box", None) if store else None
        client = getattr(box, "client", None) if box else None

        # Resolve the target folder id deterministically
        # Prefer the parent of the configured responses file_id (authoritative),
        # then fallback to an explicit folder_id, then secrets.
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

            # Choose parent-of-file first if available
            target_folder_id = file_parent_id or explicit_folder_id

            # Final fallback to secrets
            if not target_folder_id:
                try:
                    from core.secrets import get_section as _get_secret_section
                    _bx = _get_secret_section("box") or {}
                    val = str(_bx.get("BOX_RFQ_RESPONSES_FOLDER_ID", "")).strip()
                    target_folder_id = val or None
                except Exception:
                    target_folder_id = None

            # If both exist and differ, prefer the file parent (more authoritative)
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
            # Ensure the store reflects the chosen folder id for consistency in this session
            try:
                if store and target_folder_id and getattr(store, "folder_id", None) != target_folder_id:
                    store.folder_id = target_folder_id
            except Exception:
                pass
            # Warn if a configured folder_id differs from the responses file parent
            try:
                # Recompute the two candidates for messaging
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
                        # Auto-rename on conflict and retry
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

        # List files available to process in the Responses folder
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
                    items = list(client.folder(target_folder_id).get_items(limit=1000))
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
                                vendor_guess = _guess_vendor(selected_name, email_from, body_excerpt)
                                st.write(f"Subject: {subject}")
                                st.write(f"From: {email_from}")
                                st.text_area("Body preview", body_excerpt, height=200)

                        elif ext in ("msg",):
                            preview_data = _try_parse_msg(raw)
                            if "error" in preview_data:
                                st.warning(preview_data["error"])
                            else:
                                subject = preview_data.get("subject", "")
                                email_from = preview_data.get("from", "")
                                body_excerpt = _safe_preview_text(preview_data.get("body", ""))
                                vendor_guess = _guess_vendor(selected_name, email_from, body_excerpt)
                                st.write(f"Subject: {subject}")
                                st.write(f"From: {email_from}")
                                st.text_area("Body preview", body_excerpt, height=200)

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
                                        except Exception:
                                            pass

                        if not selected_vendor_val:
                            selected_vendor_val = vendor_guess or ""

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
                            rfq_num_in = st.text_input("RFQ #", value=selected_rfq_num_val)
                            part_in = st.text_input("Part #", value=selected_part_val)
                            process_in = st.text_input("Process", value=selected_process_val)
                            vendor_in = st.text_input("Vendor", value=selected_vendor_val)

                            unit_price_in = st.text_input("Unit price", value=str(unit_price_val or ""))
                            lot_min_in = st.text_input("Lot min", value=str(lot_min_val or ""))
                            lead_time_in = st.number_input(
                                "Lead time (days)",
                                value=int(lead_time_days_val) if isinstance(lead_time_days_val, int) else 0,
                                min_value=0, step=1
                            )
                            received_ts_in = st.text_input("Received timestamp (ISO)", value=str(received_ts))
                            scope_notes_in = st.text_area("Scope notes", value=scope_notes_val or "")

                            subject_val = st.text_input("Subject (if email)", value=subject or "")
                            notes_val = st.text_area("Notes", value=f"Processed preview for {selected_name}")

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
                                        "processed_at", "file_id", "file_name", "file_type",
                                        "rfq#", "part_number", "process", "vendor",
                                        "unit_price", "lot_min", "lead_time_days", "received_timestamp", "scope_notes",
                                        "subject", "body_excerpt", "notes",
                                    ]
                                    for c in needed_cols:
                                        if c not in df_curr.columns:
                                            df_curr[c] = pd.Series(dtype="object")

                                    new_row = pd.DataFrame([{
                                        "processed_at": _now_utc_iso(),
                                        "file_id": selected_id,
                                        "file_name": selected_name,
                                        "file_type": ext or "",
                                        "rfq#": rfq_num_in,
                                        "part_number": part_in,
                                        "process": process_in,
                                        "vendor": vendor_in,
                                        "unit_price": unit_price_in,
                                        "lot_min": lot_min_in,
                                        "lead_time_days": str(lead_time_in),
                                        "received_timestamp": received_ts_in,
                                        "scope_notes": scope_notes_in,
                                        "subject": subject_val or "",
                                        "body_excerpt": body_excerpt or "",
                                        "notes": notes_val or "",
                                    }])

                                    df_out = pd.concat([df_curr, new_row], ignore_index=True)

                                    if tracker.responses_store is not None:
                                        tracker.responses_store.save_df(df_out)
                                        st.success(
                                            f"Appended record to rfq_responses.csv in Box. Total rows: {len(df_out)}")
                                    else:
                                        df_out.to_csv(tracker.responses_path, index=False)
                                        st.success(
                                            f"Appended record to local rfq_responses.csv. Total rows: {len(df_out)}")
                                except Exception as e:
                                    st.error(f"Failed to append record: {e}")


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
