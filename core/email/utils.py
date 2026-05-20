from __future__ import annotations
from typing import Any, Mapping, Dict, Union
import pandas as pd


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
    Missing or ``None`` values for these fields are replaced with empty
    strings and all values are stripped of leading and trailing whitespace.

    Returns
    -------
    Dict[str, str]
    A mapping with normalized field values.
    """
    d = item.to_dict() if isinstance(item, pd.Series) else dict(item)
    return {
        "process":     (d.get("process", "") or "").strip(),
        "part_number": (d.get("part_number", "") or "").strip(),
        "quantities":  (d.get("quantities", "") or "").strip(),
        "spec":        (d.get("spec", "") or "").strip(),
        "material":    (d.get("material", "") or "").strip(),
        "due_date":    (d.get("due_date", "") or "").strip(),
        "notes":       (d.get("notes", "") or "").strip(),
    }
