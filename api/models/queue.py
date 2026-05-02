"""
Pydantic models for queue items.

These define what a valid queue item looks like — both what comes IN from
the React form (QueueItemCreate) and what goes OUT to the table (QueueItem).

The split between Create and full Item matters because:
- When creating, the user provides part_number, process, spec, etc.
- The API fills in submitted_by from the JWT (not user-supplied)
- Fields like "sent" are system-managed, not user-supplied
"""

from pydantic import BaseModel
from typing import Optional


class QueueItemCreate(BaseModel):
    part_number: str
    process: str
    spec: str
    material: Optional[str] = ""
    quantities: Optional[str] = ""
    due_date: Optional[str] = None
    qt_so_number: Optional[str] = ""   # maps to "qt/so #" column in the CSV
    cui_itar: Optional[bool] = False
    rev: Optional[str] = ""
    notes: Optional[str] = ""


class QueueItem(QueueItemCreate):
    # These fields exist in the CSV but aren't set by the user on creation
    sent: Optional[str] = ""
    submitted_by: Optional[str] = ""
    file_location: Optional[str] = ""
    print_callout: Optional[str] = ""

    # from_attributes=True lets Pydantic build this model from a dict
    # (pandas .to_dict("records") produces dicts, not QueueItem objects)
    model_config = {"from_attributes": True}
