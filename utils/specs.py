from typing import List, Optional
from core.specs.spec_manager import SpecManager
from core.config import Paths

SPECS_PATH = Paths.SPECS_PATH

# Create a spec manager instance using path from config and Box when available
import os
_box_spec_id = (
    os.environ.get("BOX_FAMILIAR_SPECS_FILE_ID", "").strip()
    or os.environ.get("BOX_BOX_FAMILIAR_SPECS_FILE_ID", "").strip()
)
spec_manager = SpecManager(Paths.SPECS_PATH, box_file_id=_box_spec_id or None)


def load_familiar_specs():
    """Load the familiar specs DataFrame from the configured CSV.

    Returns:
        pandas.DataFrame: DataFrame of familiar specs.
    """
    return spec_manager.load_familiar_specs()


def load_process_list() -> List[str]:
    """Return a list of unique process names from familiar specs.

    Returns:
        List[str]: Unique process names.
    """
    return spec_manager.load_process_list()


def load_specs_for_process(process: Optional[str]) -> List[str]:
    """Return specs for a given process with safe handling for None/empty.

    Args:
        process: Process name to filter by. If None/empty, returns [].

    Returns:
        List[str]: Sorted list of spec names for the process.
    """
    return spec_manager.load_specs_for_process(process)


def load_issuers() -> List[str]:
    """Return a sorted list of unique issuers from familiar specs.

    Returns:
        List[str]: Unique issuer names.
    """
    return spec_manager.load_issuers()


def spec_exists(process: str, spec: str) -> bool:
    """Check if a spec exists for a specific process.

    Args:
        process: Process name.
        spec: Spec identifier/name.

    Returns:
        bool: True if spec exists for the process.
    """
    return spec_manager.spec_exists(process, spec)


def add_spec_entry(process: str, spec: str, issuer: str = "", notes: str = "") -> bool:
    """Add a new familiar spec entry to the persistent CSV store.

    Args:
        process: Process name.
        spec: Spec identifier/name.
        issuer: Issuer string (optional).
        notes: Optional notes.

    Returns:
        bool: True on success, False otherwise.
    """
    return spec_manager.add_spec_entry(process, spec, issuer, notes)