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


def display_responses(user, role):
    st.subheader("Responses Table")

    # Load once initially
    df = _load_responses_df()

    if df is None or df.empty:
        st.info("No responses found yet.")
    else:
        # Simple search filter across columns
        with st.expander("Filters", expanded=False):
            search = st.text_input("Search (matches any column)", "")
        if search:
            try:
                mask = pd.Series(False, index=df.index)
                for c in df.columns:
                    mask = mask | df[c].astype(str).str.contains(search, case=False, na=False)
                df_filtered = df[mask]
            except Exception:
                df_filtered = df
        else:
            df_filtered = df

        st.dataframe(df_filtered, use_container_width=True, hide_index=True)

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
                st.dataframe(refreshed, use_container_width=True, hide_index=True)
            else:
                st.warning("Box is not configured for rfq_responses.csv; showing local data instead.")
                refreshed = _load_responses_df()
                st.dataframe(refreshed, use_container_width=True, hide_index=True)
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
