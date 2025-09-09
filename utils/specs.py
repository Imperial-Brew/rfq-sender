from typing import List, Optional
import os
from core.specs.spec_manager import SpecManager
from core.config import Paths
from core.secrets import get_section

SPECS_PATH = Paths.SPECS_PATH


def _get_box_id() -> str:
    """Return the Familiar Specs Box file ID from env or secrets.

    Order of discovery:
    - BOX_FAMILIAR_SPECS_FILE_ID
    - BOX_BOX_FAMILIAR_SPECS_FILE_ID (flattened from Streamlit secrets)
    - .streamlit/secrets.toml [box].BOX_FAMILIAR_SPECS_FILE_ID
    """
    bid = (
        os.environ.get("BOX_FAMILIAR_SPECS_FILE_ID", "").strip()
        or os.environ.get("BOX_BOX_FAMILIAR_SPECS_FILE_ID", "").strip()
    )
    if not bid:
        try:
            bid = str(get_section("box").get("BOX_FAMILIAR_SPECS_FILE_ID", "")).strip()
        except Exception:
            bid = ""
    return bid


def get_spec_manager() -> SpecManager:
    """Build a fresh SpecManager each call to avoid stale Box IDs."""
    box_id = _get_box_id() or None
    return SpecManager(SPECS_PATH, box_file_id=box_id)


# Public helpers (always use a fresh SpecManager)

def load_familiar_specs():
    """Load the familiar specs DataFrame from Box or local fallback."""
    return get_spec_manager().load_familiar_specs()


def load_process_list() -> List[str]:
    """Return a list of unique process names from familiar specs."""
    return get_spec_manager().load_process_list()


def load_specs_for_process(process: Optional[str]) -> List[str]:
    """Return specs for a given process with safe handling for None/empty.

    Args:
        process: Process name to filter by. If None/empty, returns [].

    Returns:
        List[str]: Sorted list of spec names for the process.
    """
    return get_spec_manager().load_specs_for_process(process)


def load_issuers() -> List[str]:
    """Return a sorted list of unique issuers from familiar specs."""
    return get_spec_manager().load_issuers()


def spec_exists(process: str, spec: str) -> bool:
    """Check if a spec exists for a specific process."""
    return get_spec_manager().spec_exists(process, spec)


def add_spec_entry(process: str, spec: str, issuer: str = "", notes: str = "") -> bool:
    """Add a new familiar spec entry to the persistent CSV/Box store."""
    return get_spec_manager().add_spec_entry(process, spec, issuer, notes)
