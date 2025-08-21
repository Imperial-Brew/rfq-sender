# core/secrets.py
from typing import Dict, Any
import os
from pathlib import Path

# Attempt to load .streamlit/secrets.toml directly when Streamlit isn't available
# or when running outside a Streamlit app context.

def _load_file_secrets() -> Dict[str, Any]:
    """Load secrets from .streamlit/secrets.toml if present.
    Uses tomllib (Py>=3.11) or falls back to toml if installed.
    Returns an empty dict on any error.
    """
    try:
        # Determine project root relative to this file (core/ -> project root)
        root = Path(__file__).parent.parent
        secrets_path = root / ".streamlit" / "secrets.toml"
        if not secrets_path.exists():
            return {}
        # Try tomllib first (Python 3.11+)
        try:
            import tomllib  # type: ignore
            with open(secrets_path, "rb") as f:
                return dict(tomllib.load(f) or {})
        except Exception:
            # Fallback to external toml package if available
            try:
                import toml  # type: ignore
                with open(secrets_path, "r", encoding="utf-8") as f:
                    return dict(toml.load(f) or {})
            except Exception:
                return {}
    except Exception:
        return {}


def get_section(name: str) -> Dict[str, Any]:
    # Prefer Streamlit secrets if available and populated
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            return dict(st.secrets.get(name, {}))
    except Exception:
        pass
    # Fallback to reading from the .streamlit/secrets.toml file
    file_secrets = _load_file_secrets()
    section = file_secrets.get(name, {}) if isinstance(file_secrets, dict) else {}
    # Ensure we always return a plain dict
    return dict(section) if isinstance(section, dict) else {}


def get_exchange_settings(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    s = get_section("exchange")
    s.update(overrides or {})
    return s


def get_company_info(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    s = get_section("company")
    s.update(overrides or {})
    return s
