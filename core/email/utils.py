from __future__ import annotations
from typing import Any, Mapping, Dict, Union
import pandas as pd


def extract_rfq_fields(item: Union[pd.Series, Mapping[str, Any]]) -> Dict[str, str]:
    d = item.to_dict() if isinstance(item, pd.Series) else dict(item)
    return {
        "process":     (d.get("process", "") or "").strip(),
        "part_number": (d.get("part_number", "") or "").strip(),
        "quantities":  (d.get("quantities", "") or "").strip(),
        "spec":        (d.get("spec", "") or "").strip(),
        "material":    (d.get("material", "") or "").strip(),
    }