"""
Vendor routes.

GET /vendors/                          — all vendors (summary list)
GET /vendors/{name}                    — full detail: contacts + approvals
GET /vendors/search?process=X&spec=Y  — vendors approved for a process/spec
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from api.deps import get_current_user
from api.models.vendor import ContactOut, VendorDetail, VendorSummary
from core.vendors.vendor_manager import VendorManager

router = APIRouter()

# One shared instance per process lifetime — VendorManager loads files once.
# If the underlying YAML/JSON changes on disk, call vendor_manager.reload_vendors().
_vm = VendorManager()


def _contact_to_out(c) -> ContactOut:
    """Convert a Contact dataclass to a Pydantic ContactOut."""
    return ContactOut(
        name=c.name,
        first_name=c.first_name,
        last_name=c.last_name,
        email=c.email,
        phone=c.phone,
        primary=c.primary,
        state=c.state,
        website=c.website,
    )


@router.get("/", response_model=list[VendorSummary])
def list_vendors(user: dict = Depends(get_current_user)):
    """
    Returns all vendors with a summary and their primary contact.
    The frontend uses this to populate the vendor list.
    """
    out = []
    for v in _vm.vendors:
        primary = _vm.get_primary_contact(v)
        out.append(VendorSummary(
            name=v.name,
            processes=sorted(v.processes),
            active=v.active,
            rating=v.rating,
            primary_contact=_contact_to_out(primary) if primary else None,
        ))
    return sorted(out, key=lambda v: v.name)


@router.get("/search", response_model=list[VendorSummary])
def search_vendors(
    process: str,
    spec: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    Returns vendors approved for a given process (and optional spec).
    Powers the "Find by Spec" tab on the frontend.

    Note: this route is defined BEFORE /{name} so FastAPI matches
    /vendors/search?... before treating "search" as a vendor name.
    """
    matches = _vm.find_vendors_for_process_and_spec(process, spec)
    out = []
    for v in matches:
        primary = _vm.get_primary_contact(v)
        out.append(VendorSummary(
            name=v.name,
            processes=sorted(v.processes),
            active=v.active,
            rating=v.rating,
            primary_contact=_contact_to_out(primary) if primary else None,
        ))
    return out


@router.get("/{name}", response_model=VendorDetail)
def get_vendor(name: str, user: dict = Depends(get_current_user)):
    """
    Returns full detail for one vendor: all contacts + all approved specs.
    Called when the user clicks a vendor in the list.
    """
    vendor = next((v for v in _vm.vendors if v.name == name), None)
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor '{name}' not found.")

    contacts = _vm.get_contacts_for_vendor(name)
    approvals = _vm.get_vendor_approvals(name)

    return VendorDetail(
        id=vendor.id,
        name=vendor.name,
        processes=sorted(vendor.processes),
        active=vendor.active,
        rating=vendor.rating,
        notes=vendor.notes,
        address=vendor.address if isinstance(vendor.address, dict) else {},
        contacts=[_contact_to_out(c) for c in contacts],
        approvals=approvals,
    )
