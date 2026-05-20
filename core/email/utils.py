from __future__ import annotations
from typing import Any, Mapping, Dict, Union
import pandas as pd


def _to_str(v: Any) -> str:
    """Safely convert any value to a stripped string.

    Handles the pandas NaT / NaN / None cases that arise when a CSV column
    has a datetime dtype and an empty cell is read as pd.NaT.  Those objects
    are *truthy* in Python, so the usual ``(v or "")`` guard does not help —
    it would return the NaT/float-NaN and then ``.strip()`` would raise.
    """
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        # pd.isna raises TypeError on some non-scalar types; that's fine —
        # it means v is not NaN/NaT.
        pass
    if v is None:
        return ""
    return str(v).strip()


def extract_rfq_fields(item: Union[pd.Series, Mapping[str, Any]]) -> Dict[str, str]:
    """Extract text fields of interest from an RFQ item and normalize them.

    Parameters
    ----------
    item : Union[pd.Series, Mapping[str, Any]]
        RFQ data containing possible ``process``, ``part_number``,
        ``quantities``, ``spec``, ``material``, ``due_date``, and
        ``notes`` keys.

    Normalization
    -------------
    Missing, ``None``, ``NaN``, or ``NaT`` values are replaced with empty
    strings and all values are stripped of leading and trailing whitespace.

    Returns
    -------
    Dict[str, str]
    A mapping with normalized field values.
    """
    d = item.to_dict() if isinstance(item, pd.Series) else dict(item)
    return {
        "process":     _to_str(d.get("process")),
        "part_number": _to_str(d.get("part_number")),
        "quantities":  _to_str(d.get("quantities")),
        "spec":        _to_str(d.get("spec")),
        "material":    _to_str(d.get("material")),
        "due_date":    _to_str(d.get("due_date")),
        "notes":       _to_str(d.get("notes")),
    }
