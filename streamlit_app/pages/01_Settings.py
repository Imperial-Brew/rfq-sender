import sys
from pathlib import Path
import streamlit as st

# Add project root to path so we can import shared utils
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from streamlit_app.utils.auth_middleware import require_authentication
from streamlit_app.utils.auth_shim import get_user_role
from utils.rfq_tracking import get_tracker

# Optional secret helpers (graceful fallback if not present)
def _get_secrets_section(section: str) -> dict:
    try:
        from core.secrets import get_section
        return get_section(section) or {}
    except Exception:
        return {}

def _set_secrets_section(section: str, data: dict) -> bool:
    try:
        from core.secrets import set_section
        set_section(section, data or {})
        return True
    except Exception:
        return False

def _test_box_connection():
    ok, msg, folder_name = False, "", ""
    try:
        tracker = get_tracker()
        store = getattr(tracker, "responses_store", None)
        mstore = getattr(tracker, "master_store", None)

        box_client = None
        if store and getattr(store, "box", None) and getattr(store.box, "client", None):
            box_client = store.box.client
        elif mstore and getattr(mstore, "box", None) and getattr(mstore.box, "client", None):
            box_client = mstore.box.client

        if not box_client:
            return False, "Box client not configured", ""

        # Prefer checking Responses folder (if configured), else try master store parent
        folder_id = None
        try:
            if store and getattr(store, "folder_id", None):
                folder_id = store.folder_id
            elif store and getattr(store, "file_id", None):
                fobj = box_client.file(store.file_id).get()
                folder_id = getattr(getattr(fobj, "parent", None), "id", None)
        except Exception:
            pass

        if not folder_id and mstore and getattr(mstore, "file_id", None):
            try:
                fobj = box_client.file(mstore.file_id).get()
                folder_id = getattr(getattr(fobj, "parent", None), "id", None)
            except Exception:
                pass

        if not folder_id:
            return False, "Could not resolve a Box folder to test (configure Responses/Master first)", ""

        folder = box_client.folder(folder_id).get()
        # Attempt a lightweight list
        _ = list(box_client.folder(folder_id).get_items(limit=1))
        return True, f"Connected to Box folder {folder_id}", getattr(folder, "name", "")
    except Exception as e:
        return False, f"Box test failed: {e}", ""

def _test_email_connection(config: dict):
    # Placeholder: adapt for IMAP/SMTP/Graph per your project
    # Return (ok: bool, message: str)
    try:
        required = ["provider", "username"]
        missing = [k for k in required if not str(config.get(k, "")).strip()]
        if missing:
            return False, f"Missing fields: {', '.join(missing)}"
        # TODO: implement actual IMAP/SMTP/Graph tests
        return True, "Email settings look plausible (no live test implemented)"
    except Exception as e:
        return False, f"Email test failed: {e}"

def main():
    user = require_authentication()
    role = get_user_role(user)

    st.title("Settings")
    st.caption("Configure Email and Box connections. Editing can be restricted to Admins.")

    is_admin = str(role).lower() in {"admin", "owner", "administrator"}

    # Load existing secret sections (if core.secrets is used in your project)
    email_secrets = _get_secrets_section("email")
    box_secrets = _get_secrets_section("box")

    with st.expander("Email Settings", expanded=True):
        provider = st.selectbox(
            "Provider",
            options=["IMAP", "SMTP", "Graph", "Other"],
            index=["IMAP", "SMTP", "Graph", "Other"].index(
                str(email_secrets.get("provider", "IMAP")) if email_secrets.get("provider") in ["IMAP","SMTP","Graph","Other"] else "IMAP"
            ),
            disabled=not is_admin
        )
        username = st.text_input("Username", value=str(email_secrets.get("username", "")), disabled=not is_admin)
        imap_host = st.text_input("IMAP Host", value=str(email_secrets.get("imap_host", "")), disabled=not is_admin)
        imap_port = st.number_input("IMAP Port", value=int(email_secrets.get("imap_port", 993) or 993), step=1, disabled=not is_admin)
        smtp_host = st.text_input("SMTP Host", value=str(email_secrets.get("smtp_host", "")), disabled=not is_admin)
        smtp_port = st.number_input("SMTP Port", value=int(email_secrets.get("smtp_port", 587) or 587), step=1, disabled=not is_admin)
        graph_tenant = st.text_input("Graph Tenant", value=str(email_secrets.get("graph_tenant", "")), disabled=not is_admin)
        graph_client_id = st.text_input("Graph Client ID", value=str(email_secrets.get("graph_client_id", "")), disabled=not is_admin)
        graph_client_secret = st.text_input("Graph Client Secret", value=str(email_secrets.get("graph_client_secret", "")), type="password", disabled=not is_admin)

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button("Test Email Connection"):
                ok, msg = _test_email_connection({
                    "provider": provider,
                    "username": username,
                    "imap_host": imap_host,
                    "imap_port": imap_port,
                    "smtp_host": smtp_host,
                    "smtp_port": smtp_port,
                    "graph_tenant": graph_tenant,
                    "graph_client_id": graph_client_id,
                    "graph_client_secret": graph_client_secret,
                })
                (st.success if ok else st.error)(msg)

        with col_e2:
            if is_admin and st.button("Save Email Settings"):
                data = {
                    "provider": provider,
                    "username": username,
                    "imap_host": imap_host,
                    "imap_port": int(imap_port or 0),
                    "smtp_host": smtp_host,
                    "smtp_port": int(smtp_port or 0),
                    "graph_tenant": graph_tenant,
                    "graph_client_id": graph_client_id,
                    "graph_client_secret": graph_client_secret,
                }
                if _set_secrets_section("email", data):
                    st.success("Email settings saved")
                else:
                    st.error("Failed to save Email settings")

    with st.expander("Box Settings", expanded=True):
        responses_folder_id = st.text_input(
            "Responses Folder ID (Box)",
            value=str(box_secrets.get("BOX_RFQ_RESPONSES_FOLDER_ID", "")),
            help="Folder where incoming response files are uploaded/listed.",
            disabled=not is_admin
        )
        master_file_id = st.text_input(
            "RFQ Master File ID (Box)",
            value=str(box_secrets.get("BOX_RFQ_MASTER_FILE_ID", "")),
            help="If using a single master CSV file on Box, set its file ID.",
            disabled=not is_admin
        )
        master_folder_id = st.text_input(
            "RFQ Master Folder ID (Box)",
            value=str(box_secrets.get("BOX_RFQ_MASTER_FOLDER_ID", "")),
            help="If your master store uses a folder container, specify here (optional).",
            disabled=not is_admin
        )

        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            if st.button("Test Box Connection"):
                ok, msg, fname = _test_box_connection()
                (st.success if ok else st.error)(msg + (f" — {fname}" if fname else ""))

        with col_b2:
            if is_admin and st.button("Save Box Settings"):
                data = dict(box_secrets)
                data["BOX_RFQ_RESPONSES_FOLDER_ID"] = responses_folder_id.strip()
                data["BOX_RFQ_MASTER_FILE_ID"] = master_file_id.strip()
                data["BOX_RFQ_MASTER_FOLDER_ID"] = master_folder_id.strip()
                if _set_secrets_section("box", data):
                    st.success("Box settings saved")
                else:
                    st.error("Failed to save Box settings")

        with col_b3:
            if st.button("Show Store Status"):
                try:
                    tracker = get_tracker()
                    st.write("Tracker fields:")
                    st.code({
                        "master_path": getattr(tracker, "master_path", None),
                        "has_master_store": getattr(tracker, "master_store", None) is not None,
                        "has_responses_store": getattr(tracker, "responses_store", None) is not None,
                    }, language="json")
                except Exception as e:
                    st.error(f"Failed to load tracker: {e}")

if __name__ == "__main__":
    main()