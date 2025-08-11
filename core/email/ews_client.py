# core/email/ews_client.py
from __future__ import annotations
import os, logging
from typing import Any, Mapping, Union, Dict
import pandas as pd
import certifi
from exchangelib import Credentials, Account, Configuration, DELEGATE
from core.secrets import get_section  # <- your tiny helper

log = logging.getLogger(__name__)

def _ensure_requests_uses_certifi() -> str:
    ca = certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", ca)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", ca)
    log.info(f"Using CA bundle: {ca}")
    return ca

def get_exchange_account(overrides=None) -> Account:
    overrides = overrides or {}

    # 1) Try Streamlit secrets ([exchange])…
    ex = dict(get_section("exchange"))

    # 2) …fallback to environment variables (EXCHANGE_*)
    if not ex:
        ex = {
            "username": os.getenv("EXCHANGE_USERNAME", ""),
            "password": os.getenv("EXCHANGE_PASSWORD", ""),
            "server":   os.getenv("EXCHANGE_SERVER", "outlook.office365.com"),
            "cc":       os.getenv("EXCHANGE_CC", ""),
        }

    # 3) Apply any explicit overrides (tests, CLI)
    ex.update(overrides)

    username, password, server = ex.get("username", ""), ex.get("password", ""), ex.get("server", "")
    if not username or not password:
        raise RuntimeError("Missing Exchange credentials (username/password)")

    _ensure_requests_uses_certifi()
    creds  = Credentials(username=username, password=password)
    config = Configuration(server=server, credentials=creds)
    return Account(primary_smtp_address=username, config=config, autodiscover=False, access_type=DELEGATE)

def extract_rfq_fields(item: Union[pd.Series, Mapping[str, Any]]) -> Dict[str, str]:
    d = item.to_dict() if isinstance(item, pd.Series) else dict(item)
    return {
        "process":     (d.get("process", "") or "").strip(),
        "part_number": (d.get("part_number", "") or "").strip(),
        "quantities":  (d.get("quantities", "") or "").strip(),
        "spec":        (d.get("spec", "") or "").strip(),
        "material":    (d.get("material", "") or "").strip(),
    }
