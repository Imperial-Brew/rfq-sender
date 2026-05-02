"""
Specs / process lookup routes.

GET  /specs/                          — list all specs (filterable)
GET  /specs/processes                 — list all process names
GET  /specs/processes/{name}/specs    — list specs for a process
GET  /specs/issuers                   — list all issuers
POST /specs/                          — add a new spec entry (admin only)
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from api.deps import get_current_user, require_role
from utils.specs import (
    load_process_list,
    load_specs_for_process,
    load_familiar_specs,
    load_issuers,
    spec_exists,
    add_spec_entry,
)

router = APIRouter()


class SpecEntry(BaseModel):
    process: str
    spec: str
    issuer: str = ""
    notes: str = ""


class SpecCreate(BaseModel):
    process: str
    spec: str
    issuer: str = ""
    notes: str = ""


@router.get("/", response_model=list[SpecEntry])
def list_specs(
    process: Optional[str] = Query(None),
    issuer: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    df = load_familiar_specs()
    if df.empty:
        return []

    # Normalise column names
    df.columns = [c.strip().lower() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str)

    if process:
        df = df[df["process"].str.lower() == process.lower()]
    if issuer:
        df = df[df["issuer"].str.lower() == issuer.lower()]
    if search:
        mask = df.apply(lambda row: row.str.contains(search, case=False, na=False).any(), axis=1)
        df = df[mask]

    df = df.sort_values(by=["process", "spec"])
    return [
        SpecEntry(
            process=row.get("process", ""),
            spec=row.get("spec", ""),
            issuer=row.get("issuer", ""),
            notes=row.get("notes", ""),
        )
        for row in df.to_dict(orient="records")
    ]


@router.get("/processes", response_model=list[str])
def get_processes(user: dict = Depends(get_current_user)):
    return sorted(load_process_list() or [])


@router.get("/issuers", response_model=list[str])
def get_issuers(user: dict = Depends(get_current_user)):
    return sorted(load_issuers() or [])


@router.get("/processes/{process_name}/specs", response_model=list[str])
def get_specs_for_process(process_name: str, user: dict = Depends(get_current_user)):
    """
    Returns specs for a process. The React form calls this whenever the
    user picks a process — so the spec dropdown is always accurate.
    This is the "dependent select" pattern: one dropdown drives another.
    """
    return load_specs_for_process(process_name) or []


@router.post("/", response_model=SpecEntry, status_code=status.HTTP_201_CREATED)
def create_spec(body: SpecCreate, user: dict = Depends(require_role("admin"))):
    if not body.process or not body.spec:
        raise HTTPException(status_code=400, detail="Process and spec are required.")
    if spec_exists(body.process, body.spec):
        raise HTTPException(
            status_code=409,
            detail=f"Spec '{body.spec}' already exists for process '{body.process}'.",
        )
    ok = add_spec_entry(body.process, body.spec, body.issuer, body.notes)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save spec. Check server logs.")
    return SpecEntry(process=body.process, spec=body.spec, issuer=body.issuer, notes=body.notes)
