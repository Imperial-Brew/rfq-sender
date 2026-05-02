from pydantic import BaseModel
from typing import Optional


class ContactOut(BaseModel):
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    primary: bool = False
    state: str = ""
    website: str = ""


class VendorSummary(BaseModel):
    """Lightweight shape for the list view — no contacts or approvals."""
    name: str
    processes: list[str] = []
    active: bool = True
    rating: int = 0
    primary_contact: Optional[ContactOut] = None


class VendorDetail(VendorSummary):
    """Full shape for the detail panel."""
    id: str = ""
    notes: str = ""
    address: dict = {}
    contacts: list[ContactOut] = []
    # { "Anodize": ["AMS 2468", "AMS 2469"], ... }
    approvals: dict[str, list[str]] = {}
