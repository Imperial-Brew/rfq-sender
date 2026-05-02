"""
Specs / process lookup routes.

GET /specs/processes              — list all process names
GET /specs/processes/{name}/specs — list specs available for a process

These power the dropdowns in the Add to Queue form on the frontend,
replacing the hardcoded list and keeping it in sync with FamiliarSpecs.csv.
"""

from fastapi import APIRouter, Depends
from api.deps import get_current_user
from utils.specs import load_process_list, load_specs_for_process

router = APIRouter()


@router.get("/processes", response_model=list[str])
def get_processes(user: dict = Depends(get_current_user)):
    return sorted(load_process_list() or [])


@router.get("/processes/{process_name}/specs", response_model=list[str])
def get_specs(process_name: str, user: dict = Depends(get_current_user)):
    """
    Returns specs for a process. The React form calls this whenever the
    user picks a process — so the spec dropdown is always accurate.
    This is the "dependent select" pattern: one dropdown drives another.
    """
    return load_specs_for_process(process_name) or []
