"""
RFQ Master routes.

GET  /rfq-master/              — list all entries (filterable by status/search)
PUT  /rfq-master/{rfq_id}      — update status, notes, or received date
DELETE /rfq-master/{rfq_id}    — remove an entry (admin only)
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
import pandas as pd
from pathlib import Path

from api.deps import get_current_user, require_role
from utils.rfq_tracking import get_tracker

router = APIRouter()


class MasterEntry(BaseModel):
    rfq_id: str
    qt_so: str = ""
    part_number: str = ""
    vendor: str = ""
    vendor_contact: str = ""
    rfq_folder: str = ""
    status: str = ""
    sent: str = ""
    received: str = ""
    notes: str = ""


class MasterUpdate(BaseModel):
    status: Optional[str] = None
    received: Optional[str] = None
    notes: Optional[str] = None


def _load_df() -> pd.DataFrame:
    tracker = get_tracker()
    try:
        if getattr(tracker, "master_store", None) is not None:
            df = tracker.master_store.load_df()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
    except Exception:
        pass
    p = getattr(tracker, "master_path", None)
    if p and Path(p).exists():
        try:
            return pd.read_csv(p, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(p, encoding="cp1252")
    return pd.DataFrame()


def _save_df(df: pd.DataFrame) -> None:
    tracker = get_tracker()
    try:
        if getattr(tracker, "master_store", None) is not None:
            tracker.master_store.save_df(df)
            return
    except Exception:
        pass
    p = getattr(tracker, "master_path", None)
    if not p:
        raise RuntimeError("master_path not configured")
    df.to_csv(p, index=False, encoding="utf-8")


def _find_col(df: pd.DataFrame, *aliases: str) -> Optional[str]:
    low = {c.lower().strip(): c for c in df.columns}
    for a in aliases:
        if a.lower() in low:
            return low[a.lower()]
    return None


def _row_to_entry(row: dict, col_map: dict) -> MasterEntry:
    def g(key: str) -> str:
        col = col_map.get(key)
        return str(row.get(col, "") or "") if col else ""
    return MasterEntry(
        rfq_id=g("rfq_id"),
        qt_so=g("qt_so"),
        part_number=g("part_number"),
        vendor=g("vendor"),
        vendor_contact=g("vendor_contact"),
        rfq_folder=g("rfq_folder"),
        status=g("status"),
        sent=g("sent"),
        received=g("received"),
        notes=g("notes"),
    )


def _build_col_map(df: pd.DataFrame) -> dict:
    return {
        "rfq_id":         _find_col(df, "rfq#", "rfq #", "rfqno"),
        "qt_so":          _find_col(df, "qt/so #", "qt/so#", "qt", "so #"),
        "part_number":    _find_col(df, "part_number", "part number", "part"),
        "vendor":         _find_col(df, "vendor", "vendor name", "vendor_name"),
        "vendor_contact": _find_col(df, "vendor_contact", "contact", "contact email", "email"),
        "rfq_folder":     _find_col(df, "rfq_folder", "rfq folder", "box_rfq_folder"),
        "status":         _find_col(df, "status"),
        "sent":           _find_col(df, "sent"),
        "received":       _find_col(df, "received"),
        "notes":          _find_col(df, "notes"),
    }


@router.get("/", response_model=list[MasterEntry])
def list_master(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    df = _load_df()
    if df.empty:
        return []

    col_map = _build_col_map(df)

    if status_filter and col_map["status"]:
        df = df[df[col_map["status"]].astype(str).str.lower() == status_filter.lower()]

    if search:
        mask = df.apply(
            lambda row: row.astype(str).str.contains(search, case=False, na=False).any(),
            axis=1,
        )
        df = df[mask]

    return [_row_to_entry(row, col_map) for row in df.to_dict(orient="records")]


@router.put("/{rfq_id}", response_model=MasterEntry)
def update_entry(
    rfq_id: str,
    body: MasterUpdate,
    user: dict = Depends(get_current_user),
):
    df = _load_df()
    if df.empty:
        raise HTTPException(status_code=404, detail="RFQ master is empty.")

    col_map = _build_col_map(df)
    id_col = col_map.get("rfq_id")
    if not id_col:
        raise HTTPException(status_code=500, detail="rfq# column not found in master.")

    mask = df[id_col].astype(str).str.strip() == rfq_id.strip()
    if not mask.any():
        raise HTTPException(status_code=404, detail=f"RFQ '{rfq_id}' not found.")

    idx = df[mask].index[0]
    if body.status is not None and col_map["status"]:
        df.loc[idx, col_map["status"]] = body.status
    if body.received is not None and col_map["received"]:
        df.loc[idx, col_map["received"]] = body.received
    if body.notes is not None and col_map["notes"]:
        df.loc[idx, col_map["notes"]] = body.notes

    _save_df(df)
    return _row_to_entry(df.loc[idx].to_dict(), col_map)


@router.delete("/{rfq_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    rfq_id: str,
    user: dict = Depends(require_role("admin")),
):
    df = _load_df()
    if df.empty:
        raise HTTPException(status_code=404, detail="RFQ master is empty.")

    col_map = _build_col_map(df)
    id_col = col_map.get("rfq_id")
    if not id_col:
        raise HTTPException(status_code=500, detail="rfq# column not found in master.")

    mask = df[id_col].astype(str).str.strip() == rfq_id.strip()
    if not mask.any():
        raise HTTPException(status_code=404, detail=f"RFQ '{rfq_id}' not found.")

    _save_df(df[~mask].reset_index(drop=True))
