"""
Queue CRUD routes.

GET    /queue/        — list all items (any authenticated user)
POST   /queue/        — add an item (estimator or admin)
DELETE /queue/{part}  — remove an item (admin only)
"""

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user, require_role
from api.models.queue import QueueItem, QueueItemCreate
from utils.rfq_queue import load_queue, add_to_queue, save_queue

router = APIRouter()


@router.get("/", response_model=list[QueueItem])
def get_queue(user: dict = Depends(get_current_user)):
    """
    Returns all queue items. Box-backed if configured, otherwise local CSV.
    The existing load_queue() handles both — nothing changes there.

    response_model=list[QueueItem] tells FastAPI to:
    1. Validate that what we return matches the QueueItem shape
    2. Strip out any extra fields (like internal pandas metadata)
    3. Serialize it to JSON automatically
    """
    df = load_queue()
    if df.empty:
        return []

    # pandas DataFrame.to_dict("records") converts each row into a plain dict.
    # fillna("") replaces NaN (pandas "no value") with empty string,
    # because JSON doesn't have a NaN concept and it would cause a serialization error.
    records = df.fillna("").to_dict("records")

    # Rename the CSV column "qt/so #" to our model's field name.
    # The slash and space in "qt/so #" aren't valid Python identifiers.
    for r in records:
        r["qt_so_number"] = r.pop("qt/so #", r.get("qt_so_number", ""))

    return records


@router.post("/", response_model=QueueItem, status_code=201)
def add_item(
    item: QueueItemCreate,
    user: dict = Depends(require_role("estimator")),
):
    """
    Adds a new item to the queue.
    Requires 'estimator' or 'admin' role — viewers can look but not add.

    FastAPI automatically validates `item` against QueueItemCreate before
    this function runs. If required fields are missing or the wrong type,
    it returns a 422 error without ever reaching this code.
    """
    entry = item.model_dump()

    # The submitter is taken from the JWT, not from the request body.
    # This means a user can't claim someone else submitted something.
    entry["submitted_by"] = user["sub"]

    # Rename back to the CSV column name that the rest of the app expects
    entry["qt/so #"] = entry.pop("qt_so_number", "")

    add_to_queue(entry)

    # Return what was added (include submitted_by so the table updates immediately)
    entry["qt_so_number"] = entry.pop("qt/so #", "")
    return entry


@router.delete("/{part_number}", status_code=204)
def remove_item(
    part_number: str,
    user: dict = Depends(require_role("admin")),
):
    """
    Removes all queue entries matching part_number.
    Admin only — this is a destructive action.

    Status 204 = "success, nothing to return." The client doesn't need
    a response body; knowing the request succeeded is enough.
    """
    df = load_queue()

    # Find the part_number column regardless of capitalization
    col = next(
        (c for c in df.columns if c.lower().strip() == "part_number"),
        None,
    )
    if col is None:
        raise HTTPException(status_code=500, detail="Queue has no part_number column.")

    mask = df[col].astype(str).str.strip() == part_number.strip()
    if not mask.any():
        raise HTTPException(status_code=404, detail=f"'{part_number}' not found in queue.")

    save_queue(df[~mask])
    # 204 responses have no body — just return None (FastAPI handles it)
