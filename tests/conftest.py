# tests/conftest.py
import os
from pathlib import Path

# Python 3.12 has tomllib built-in
import tomllib  # noqa: F401

def pytest_sessionstart(session):
    proj_root = Path(__file__).resolve().parents[1]
    secrets_path = proj_root / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        # Optional: skip secret-dependent tests when file not present
        return

    data = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
    ex = data.get("exchange", {})
    comp = data.get("company", {})
    app = data.get("app", {})

    # Exchange creds → env so ews_client can read them without Streamlit
    os.environ.setdefault("EXCHANGE_USERNAME", ex.get("username", ""))
    os.environ.setdefault("EXCHANGE_PASSWORD", ex.get("password", ""))
    os.environ.setdefault("EXCHANGE_SERVER",   ex.get("server", "outlook.office365.com"))
    if "cc" in ex:
        os.environ.setdefault("EXCHANGE_CC", ex["cc"])

    # Optional: company/app to env if your tests/templates expect them
    os.environ.setdefault("COMPANY_NAME", comp.get("name", ""))
    os.environ.setdefault("APP_SUBJECT_PREFIX", app.get("subject_prefix", ""))
