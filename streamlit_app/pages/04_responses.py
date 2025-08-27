import streamlit as st
import pandas as pd
from pathlib import Path
import sys

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
        target_folder_id = None
        try:
            if store and getattr(store, "folder_id", None):
                target_folder_id = store.folder_id
            if (not target_folder_id) and store and getattr(store, "file_id", None) and client:
                try:
                    fobj = client.file(store.file_id).get()
                    if getattr(fobj, "parent", None) and getattr(fobj.parent, "id", None):
                        target_folder_id = fobj.parent.id
                except Exception:
                    pass
            if not target_folder_id:
                try:
                    from core.secrets import get_section as _get_secret_section
                    _bx = _get_secret_section("box") or {}
                    val = str(_bx.get("BOX_RFQ_RESPONSES_FOLDER_ID", "")).strip()
                    target_folder_id = val or None
                except Exception:
                    target_folder_id = None
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
