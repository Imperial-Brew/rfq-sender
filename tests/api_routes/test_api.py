"""Tests for the FastAPI layer: auth secret handling, queue delete, RFQ Master logging."""

from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api.deps as deps
from api.main import app
from api.routers import queue as queue_router
from api.routers import send_rfq


def _auth(role: str = "admin") -> dict:
    token = deps.jwt.encode(
        {"sub": "tester@example.com", "name": "Tester", "role": role},
        deps.SECRET_KEY,
        algorithm=deps.ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── JWT secret ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value", [None, "", "change-me-before-deploying"])
def test_missing_or_placeholder_jwt_secret_is_rejected(monkeypatch, value) -> None:
    if value is None:
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("JWT_SECRET_KEY", value)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        deps._load_secret_key()


def test_real_jwt_secret_is_accepted(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 64)
    assert deps._load_secret_key() == "a" * 64


def test_token_signed_with_other_key_is_rejected(client) -> None:
    forged = deps.jwt.encode({"sub": "x", "role": "admin"}, "change-me-before-deploying",
                             algorithm=deps.ALGORITHM)
    r = client.get("/api/queue/", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


# ── Queue delete ──────────────────────────────────────────────────────────────

@pytest.fixture
def fake_queue(monkeypatch) -> dict:
    state = {
        "df": pd.DataFrame(
            {
                "part_number": ["P-1", "P-1", "P-2"],
                "process": ["Anodize", "Chromate", "Anodize"],
            }
        )
    }
    monkeypatch.setattr(queue_router, "load_queue", lambda: state["df"].copy())
    monkeypatch.setattr(queue_router, "save_queue", lambda df: state.__setitem__("df", df))
    return state


def test_delete_with_process_removes_only_that_row(client, fake_queue) -> None:
    r = client.delete("/api/queue/P-1", params={"process": "Chromate"}, headers=_auth())
    assert r.status_code == 204
    remaining = fake_queue["df"][["part_number", "process"]].values.tolist()
    assert remaining == [["P-1", "Anodize"], ["P-2", "Anodize"]]


def test_delete_without_process_removes_all_rows_for_part(client, fake_queue) -> None:
    r = client.delete("/api/queue/P-1", headers=_auth())
    assert r.status_code == 204
    assert fake_queue["df"]["part_number"].tolist() == ["P-2"]


def test_delete_unknown_process_is_404(client, fake_queue) -> None:
    r = client.delete("/api/queue/P-1", params={"process": "Passivate"}, headers=_auth())
    assert r.status_code == 404
    assert len(fake_queue["df"]) == 3


def test_delete_unknown_part_message_omits_process(client, fake_queue) -> None:
    r = client.delete("/api/queue/P-404", headers=_auth())
    assert r.status_code == 404
    assert r.json()["detail"] == "'P-404' not found in queue."


def test_delete_with_process_fails_closed_without_process_column(client, monkeypatch) -> None:
    state = {"df": pd.DataFrame({"part_number": ["P-1", "P-1"]})}
    monkeypatch.setattr(queue_router, "load_queue", lambda: state["df"].copy())
    monkeypatch.setattr(queue_router, "save_queue", lambda df: state.__setitem__("df", df))
    r = client.delete("/api/queue/P-1", params={"process": "Anodize"}, headers=_auth())
    assert r.status_code == 500
    assert len(state["df"]) == 2  # nothing deleted


def test_delete_requires_admin(client, fake_queue) -> None:
    r = client.delete("/api/queue/P-1", headers=_auth("estimator"))
    assert r.status_code == 403


# ── Drafting logs to RFQ Master ───────────────────────────────────────────────

class _FakeTracker:
    def __init__(self) -> None:
        self.calls: list = []

    def add_master_entry(self, queue_row: dict, **kwargs) -> dict:
        self.calls.append((queue_row, kwargs))
        return {"rfq#": "1"}


def _patch_email_route(monkeypatch, draft_ok: dict) -> _FakeTracker:
    df = pd.DataFrame(
        {
            "part_number": ["P-1"],
            "process": ["Anodize"],
            "spec": ["MIL-A-8625"],
            "qt/so #": ["55149"],
            "box_share_link": ["https://box.example/s/abc"],
            "box_password": [""],
            "sent": [""],
        }
    )
    vendors = [SimpleNamespace(name="Good Co"), SimpleNamespace(name="Bad Co")]
    contacts = {
        "Good Co": SimpleNamespace(name="Gina", email="gina@good.example"),
        "Bad Co": SimpleNamespace(name="Bob", email="bob@bad.example"),
    }
    vm = SimpleNamespace(
        find_vendors_for_process_and_spec=lambda process, spec: vendors,
        get_primary_contact=lambda v: contacts[v.name],
    )
    em = SimpleNamespace(
        create_rfq_email=lambda **kw: (kw["contact"]["email"], "subj", "<p>body</p>"),
        create_draft_email=lambda recipient, **kw: draft_ok[recipient],
    )
    tracker = _FakeTracker()
    monkeypatch.setattr(send_rfq, "load_queue", lambda: df.copy())
    monkeypatch.setattr(send_rfq, "save_queue", lambda _df: None)
    monkeypatch.setattr(send_rfq, "detect_cui_itar", lambda row: False)
    monkeypatch.setattr(send_rfq, "_get_vendor_manager", lambda: vm)
    monkeypatch.setattr(send_rfq, "_get_email_manager", lambda: em)
    monkeypatch.setattr(send_rfq, "get_tracker", lambda: tracker)
    return tracker


def test_drafting_logs_one_master_row_per_successful_vendor(client, monkeypatch) -> None:
    tracker = _patch_email_route(
        monkeypatch, {"gina@good.example": True, "bob@bad.example": False}
    )
    r = client.post("/api/send-rfq/email/P-1", json={"process": "Anodize"}, headers=_auth())
    assert r.status_code == 200
    assert [x["success"] for x in r.json()] == [True, False]

    assert len(tracker.calls) == 1
    row, kwargs = tracker.calls[0]
    assert row["part_number"] == "P-1"
    assert row["qt/so #"] == "55149"
    assert kwargs["vendor_name"] == "Good Co"
    assert kwargs["contact_email"] == "gina@good.example"
    assert kwargs["rfq_folder_link"] == "https://box.example/s/abc"
    assert kwargs["dedupe"] is True


def test_no_master_rows_when_every_draft_fails(client, monkeypatch) -> None:
    tracker = _patch_email_route(
        monkeypatch, {"gina@good.example": False, "bob@bad.example": False}
    )
    r = client.post("/api/send-rfq/email/P-1", json={"process": "Anodize"}, headers=_auth())
    assert r.status_code == 200
    assert tracker.calls == []


def test_master_logging_failure_does_not_fail_request(client, monkeypatch) -> None:
    _patch_email_route(monkeypatch, {"gina@good.example": True, "bob@bad.example": True})

    def boom() -> None:
        raise RuntimeError("Box down")

    monkeypatch.setattr(send_rfq, "get_tracker", boom)
    r = client.post("/api/send-rfq/email/P-1", json={"process": "Anodize"}, headers=_auth())
    assert r.status_code == 200
    assert all(x["success"] for x in r.json())


def test_master_entry_records_sent_timestamp(tmp_path, monkeypatch) -> None:
    """add_master_entry fills the template's `sent` column (local CSV, no Box)."""
    import shutil
    from pathlib import Path

    import utils.rfq_tracking as rfq_tracking

    docs = Path(__file__).resolve().parents[2] / "docs"
    shutil.copy(docs / "rfq_master_template.csv", tmp_path / "rfq_master_template.csv")
    for var in ("BOX_RFQ_MASTER_FILE_ID", "BOX_RFQ_MASTER_FOLDER_ID",
                "BOX_RFQ_RESPONSES_FILE_ID", "BOX_RFQ_RESPONSES_FOLDER_ID"):
        monkeypatch.delenv(var, raising=False)
        monkeypatch.delenv(f"BOX_{var}", raising=False)
    monkeypatch.setattr("core.secrets.get_section", lambda name: {})

    tracker = rfq_tracking.RFQTracking(base_docs_dir=tmp_path)
    assert tracker.master_store is None
    tracker.add_master_entry(
        {"qt/so #": "60001", "part_number": "P-9", "process": "Anodize"},
        vendor_name="Good Co",
        contact_email="gina@good.example",
    )
    df = pd.read_csv(tmp_path / "rfq_master.csv", dtype=str)
    new = df[df["part_number"] == "P-9"].iloc[0]
    assert new["rfq#"] == "60001-1"
    assert new["vendor"] == "Good Co"
    assert new["status"] == "pending"
    assert str(new["sent"]).startswith("20")


@pytest.mark.parametrize("key", ["qt/so #", "qt_so_number"])
def test_box_folder_uses_quote_number_from_queue_row(key) -> None:
    from utils.box_helpers import upload_and_share_for_part

    seen = {}

    def create_rfq_structure(quote_id, part_numbers, vendors):
        seen["quote_id"] = quote_id
        return {"part_folders": {}}

    box = SimpleNamespace(create_rfq_structure=create_rfq_structure)
    upload_and_share_for_part(box, pd.Series({"part_number": "P-1", key: "55149"}), [])
    assert seen["quote_id"] == "55149"
