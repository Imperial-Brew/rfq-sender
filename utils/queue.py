import pandas as pd
import os
import logging
from pathlib import Path
from core.config import Paths, LoggingConfig, init_config

# Initialize configuration
init_config()

# Set up logging using the centralized configuration
logger = LoggingConfig.setup_logging(__name__, "queue.log")

# Use the centralized path from config
QUEUE_PATH = Paths.QUEUE_PATH

# Lazy imports for Box
_box_checked = False
_box_store = None


def _get_box_store():
    """Return an initialized BoxQueueStore if BOX is configured; otherwise None."""
    global _box_checked, _box_store
    if _box_checked:
        return _box_store

    _box_checked = True
    try:
        # Prefer explicit env var first
        file_id = os.environ.get("BOX_QUEUE_FILE_ID", "").strip()
        folder_id = os.environ.get("BOX_QUEUE_FOLDER_ID", "").strip()

        # Also look for secrets-mapped env like BOX_BOX_QUEUE_FILE_ID
        if not file_id:
            file_id = os.environ.get("BOX_BOX_QUEUE_FILE_ID", "").strip()
        if not folder_id:
            folder_id = os.environ.get("BOX_BOX_QUEUE_FOLDER_ID", "").strip()

        # If still missing, try pulling from secrets [box]
        if (not file_id) or (not folder_id):
            try:
                from core.secrets import get_section as _get_secret_section
                _box = _get_secret_section("box") or {}
                if not file_id:
                    file_id = str(_box.get("BOX_QUEUE_FILE_ID", "")).strip()
                if not folder_id:
                    folder_id = str(_box.get("BOX_QUEUE_FOLDER_ID", "")).strip()
            except Exception as _e:
                logger.debug(f"No secrets box section available for queue ids: {_e}")

        if not file_id:
            logger.info("BOX_QUEUE_FILE_ID not set; using local queue path")
            _box_store = None
            return None

        # Initialize BoxIntegration
        try:
            from scripts.box.box_integration import BoxIntegration
            from scripts.box.box_queue_store import BoxQueueStore
        except Exception as imp_e:
            logger.warning(f"Box modules not available: {imp_e}")
            _box_store = None
            return None

        box = BoxIntegration(logger=logger)
        if not getattr(box, "client", None):
            diag = {}
            try:
                diag = box.diagnostics()
            except Exception:
                pass
            logger.warning(f"Box initialization failed; falling back to local. Diagnostics: {diag}")
            _box_store = None
            return None

        _box_store = BoxQueueStore(box_integration=box, file_id=file_id or None, folder_id=folder_id or None, logger=logger)
        return _box_store
    except Exception as e:
        logger.warning(f"Error preparing Box queue store (fallback to local): {e}")
        _box_store = None
        return None


def _standardize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [col.lower() for col in df.columns]
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace('\n', ' ').str.strip()
        if col in ['sent', 'quantities', 'qt/so #', 'rev', 'process', 'spec',
                   'material', 'part_number', 'print callout', 'file_location',
                   'submitted_by', 'rfq #']:
            df[col] = df[col].astype(str).replace('nan', '')
        elif col in ['due_date']:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        elif col in ['rfq #']:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna('')
            except Exception as e:
                logger.warning(f"Error converting {col} to numeric: {str(e)}")
                df[col] = df[col].astype(str).replace('nan', '')
    return df


def load_queue(path: str | None = None) -> pd.DataFrame:
    """
    Load the RFQ queue.
    If BOX_QUEUE_FILE_ID is configured and Box initializes, load from Box via BoxQueueStore.
    Otherwise, load from the local filesystem path Paths.QUEUE_PATH.
    """
    # Try Box first
    store = _get_box_store()
    if store is not None:
        try:
            logger.info("Loading queue from Box (BoxQueueStore)")
            df = store.load_df()
            return _standardize_df(df)
        except Exception as e:
            logger.warning(f"Failed loading queue from Box; falling back to local: {e}")

    # Local fallback
    local_path = path or QUEUE_PATH
    logger.info(f"Loading queue from local path {local_path}")
    if not os.path.exists(local_path):
        logger.warning(f"Queue file not found at {local_path}, returning empty DataFrame")
        return pd.DataFrame()
    try:
        df = pd.read_csv(local_path)
        logger.info(f"Successfully loaded queue with {len(df)} entries")
        return _standardize_df(df)
    except Exception as e:
        logger.error(f"Error loading queue from {local_path}: {str(e)}")
        return pd.DataFrame()



def save_queue(df: pd.DataFrame, path: str | None = None) -> None:
    # One-time cleanup: drop legacy RFQ # if present
    df = df.drop(columns=["rfq #", "RFQ #"], errors="ignore")

    store = _get_box_store()
    if store is not None:
        logger.info("Saving queue to Box (BoxQueueStore)")
        store.save_df(df)
        return
    # Local fallback
    local_path = path or QUEUE_PATH
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving queue to local path {local_path}")
    df.to_csv(local_path, index=False)


def add_to_queue(entry_or_path, maybe_entry: dict | None = None):
    """
    Add a new entry to the queue (Box-backed if configured; otherwise local CSV).
    Backward compatible:
    - add_to_queue(entry)
    - add_to_queue(path, entry)
    """
    try:
        # Determine call style
        local_path_override = None
        if isinstance(entry_or_path, dict) and maybe_entry is None:
            entry = entry_or_path
        else:
            local_path_override = str(entry_or_path) if entry_or_path is not None else None
            entry = maybe_entry or {}

        # Normalize new fields: 'qt/so #' and 'cui_itar'
        qt_so = (entry.get('qt/so #') or '').strip()
        entry['qt/so #'] = qt_so
        cui_val = entry.get('cui_itar', '')
        if isinstance(cui_val, bool):
            entry['cui_itar'] = 'TRUE' if cui_val else 'FALSE'
        else:
            s = str(cui_val).strip().upper()
            entry['cui_itar'] = 'TRUE' if s in ('TRUE', 'YES', 'Y', '1') else ('FALSE' if s else '')

        # Load existing queue
        df = load_queue(local_path_override)
        # Add new entry
        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)

        # Save updated queue (Box if available, else local)
        store = _get_box_store()
        if store is not None:
            logger.info("Saving updated queue to Box")
            store.save_df(df)
        else:
            path = local_path_override or QUEUE_PATH
            logger.info(f"Saving updated queue to local path {path}")
            # Ensure parent dir exists
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(path, index=False)

        logger.info(f"Successfully added entry to queue: {entry.get('part_number', 'Unknown part')} - {entry.get('process', 'Unknown process')}")
    except Exception as e:
        logger.error(f"Error adding entry to queue: {str(e)}")
        raise
