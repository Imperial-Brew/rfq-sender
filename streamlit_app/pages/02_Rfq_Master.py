import sys
from pathlib import Path
from typing import Tuple, Dict, Optional
import pandas as pd
import streamlit as st

# Add project root to path so we can import shared utils
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from streamlit_app.utils.auth_middleware import require_authentication
from streamlit_app.utils.auth_shim import get_user_role
from utils.rfq_tracking import get_tracker

# -------- Helpers

def _load_master_df() -> pd.DataFrame:
    """
    Load rfq_master.csv via RFQTracking (Box if configured, else local path).
    Mirrors the logic used in 04_responses.py.
    """
    tracker = get_tracker()
    # Try Box-backed store
    try:
        if getattr(tracker, "master_store", None) is not None:
            df = tracker.master_store.load_df()
            if isinstance(df, pd.DataFrame):
                return df
    except Exception:
        pass
    # Fallback to local path
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

def _save_master_df(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Save rfq_master.csv via RFQTracking (Box if configured, else local path).
    """
    tracker = get_tracker()
    # Prefer master_store if available
    try:
        if getattr(tracker, "master_store", None) is not None:
            tracker.master_store.save_df(df)
            return True, "Saved to Box master store"
    except Exception as e:
        return False, f"Failed to save to Box master store: {e}"

    # Fallback to master_path
    try:
        p = getattr(tracker, "master_path", None)
        if not p:
            return False, "master_path is not configured"
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(p, index=False, encoding="utf-8")
        return True, f"Saved to local file: {p}"
    except Exception as e:
        return False, f"Failed to save to local path: {e}"

def _find_col(df: pd.DataFrame, aliases) -> Optional[str]:
    cols = [c for c in df.columns]
    low = {c.lower().strip(): c for c in cols}
    for a in aliases:
        if a.lower() in low:
            return low[a.lower()]
    # partial match
    for a in aliases:
        for c in cols:
            if a.lower() in c.lower():
                return c
    return None

def _master_cols(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    return {
        "rfq": _find_col(df, ["rfq", "rfq#", "rfq #", "rfqno", "rfqid"]),
        "part": _find_col(df, ["part_number", "part number", "part", "pn"]),
        "vendor": _find_col(df, ["vendor", "vendor_name", "vendor name"]),
        "process": _find_col(df, ["process"]),
    }

def _validate_master_df(df: pd.DataFrame) -> Tuple[bool, str]:
    if df is None or df.empty:
        return False, "Master is empty"
    cols = _master_cols(df)
    required = ["rfq", "part"]  # adjust your required columns
    missing = [k for k in required if not cols.get(k)]
    if missing:
        return False, f"Missing required column(s): {', '.join(missing)}"
    # Duplicate RFQ check (when rfq exists)
    if cols["rfq"]:
        rfq_series = df[cols["rfq"]].astype(str).str.strip()
        dups = rfq_series[rfq_series.duplicated(keep=False)]
        if not dups.empty:
            dup_vals = ", ".join(sorted(set(dups.head(10).tolist())))
            return False, f"Duplicate RFQ values detected: {dup_vals} (and possibly more)"
    return True, "Validation passed"

def _import_csv(uploaded_file) -> pd.DataFrame:
    try:
        return pd.read_csv(uploaded_file)
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding="cp1252")
    except Exception as e:
        st.error(f"Failed to import CSV: {e}")
        return pd.DataFrame()

# -------- Page

def main():
    user = require_authentication()
    role = get_user_role(user)
    is_admin_or_editor = str(role).lower() in {"admin", "owner", "administrator", "editor"}

    st.title("RFQ Master")
    st.caption("View, filter, edit, and save the RFQ master table. Edits may be restricted by role.")

    # Optional: quick navigation back to Responses if you came from there
    if st.session_state.get("return_to_page") == "Responses":
        if st.button("Back to Responses"):
            st.session_state["return_to_page"] = None
            st.switch_page("pages/03_responses.py")

    # Load current master
    df = _load_master_df()
    if df is None:
        df = pd.DataFrame()

    with st.expander("Import / Export", expanded=False):
        up = st.file_uploader("Import CSV to replace current view (not saved until you click Save)", type=["csv"])
        col_ie1, col_ie2 = st.columns(2)
        if up is not None and col_ie1.button("Load CSV into editor"):
            new_df = _import_csv(up)
            if not new_df.empty:
                st.session_state["rfq_master_editor_df"] = new_df
                st.success(f"Loaded {len(new_df)} rows into editor (not yet saved)")
            else:
                st.warning("Imported CSV is empty or failed to parse")
        if col_ie2.button("Download current (editor) as CSV"):
            to_dl = st.session_state.get("rfq_master_editor_df", df)
            st.download_button(
                label="Download (current editor view) as CSV",
                data=to_dl.to_csv(index=False).encode("utf-8"),
                file_name="rfq_master_export.csv", mime="text/csv" )

    # Decide which DF to show in the editor
    editor_df = st.session_state.get("rfq_master_editor_df", df.copy())

    st.subheader("Editor")
    st.caption("Inline edit the table. Click Validate & Save to persist changes.")
    column_config = {
        # You can enforce types/hints here with st.column_config.* if desired
        # e.g., "rfq": st.column_config.TextColumn("RFQ #", required=True),
    }

    edited_df = st.data_editor(
        editor_df,
        use_container_width=True,
        num_rows="dynamic" if is_admin_or_editor else "fixed",
        disabled=not is_admin_or_editor,
        column_config=column_config or None,
        key="rfq_master_data_editor",
        height=520,
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Validate"):
            ok, msg = _validate_master_df(edited_df)
            (st.success if ok else st.error)(msg)

    with col_b:
        if is_admin_or_editor and st.button("Validate & Save"):
            ok, msg = _validate_master_df(edited_df)
            if not ok:
                st.error(msg)
            else:
                saved, smsg = _save_master_df(edited_df)
                if saved:
                    st.success(smsg)
                    st.session_state.pop("rfq_master_editor_df", None)
                else:
                    st.error(smsg)

    with col_c:
        if st.button("Reload from Source"):
            st.session_state.pop("rfq_master_editor_df", None)
            st.rerun()

    with st.expander("Store Status", expanded=False):
        try:
            tracker = get_tracker()
            st.code({
                "master_path": getattr(tracker, "master_path", None),
                "has_master_store": getattr(tracker, "master_store", None) is not None,
            }, language="json")
        except Exception as e:
            st.error(f"Failed to inspect tracker: {e}")

    st.subheader("Quick Find")
    query = st.text_input("Search RFQ / Part / Vendor")
    if query and not edited_df.empty:
        q = str(query).strip()
        cols = edited_df.columns
        mask = pd.Series(False, index=edited_df.index)
        for c in cols:
            try:
                mask = mask | edited_df[c].astype(str).str.contains(q, case=False, na=False)
            except Exception:
                pass
        results = edited_df[mask]
        st.caption(f"{len(results)} rows matched")
        st.dataframe(results, use_container_width=True, height=240)

        if st.button("Use Selected RFQ in Responses (first row)"):
            if not results.empty:
                cols_map = _master_cols(results)
                rfq_col = cols_map.get("rfq")
                selected_val = str(results.iloc[0][rfq_col]) if rfq_col else None
                st.session_state["selected_rfq_id"] = selected_val
                st.session_state["return_to_page"] = None
                st.switch_page("pages/03_responses.py")
            else:
                st.warning("No results to select")

if __name__ == "__main__":
    main()