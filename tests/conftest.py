# tests/conftest.py
import os
from pathlib import Path
import tomllib  # py3.11+

def pytest_sessionstart(session):
    p = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
    if not p.exists():
        return
    data = tomllib.loads(p.read_text(encoding="utf-8"))

    ex = data.get("exchange", {})
    os.environ.setdefault("EXCHANGE_USERNAME", ex.get("username", ""))
    os.environ.setdefault("EXCHANGE_PASSWORD", ex.get("password", ""))
    os.environ.setdefault("EXCHANGE_SERVER",   ex.get("server", "outlook.office365.com"))

    az = data.get("azure", {})
    os.environ.setdefault("AZURE_TENANT_ID", az.get("tenant_id", ""))
    os.environ.setdefault("AZURE_CLIENT_ID", az.get("client_id", ""))
    os.environ.setdefault("AZURE_CLIENT_SECRET", az.get("client_secret", ""))
