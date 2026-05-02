# core/secrets.py
from typing import Dict, Any
import os
from pathlib import Path

# Attempt to load .streamlit/secrets.toml directly when Streamlit isn't available
# or when running outside a Streamlit app context.

def _load_file_secrets() -> Dict[str, Any]:
    """Load secrets from .streamlit/secrets.toml if present, or from the
    STREAMLIT_SECRETS_TOML environment variable (used in cloud deployments
    where the file cannot be committed to the repo).
    """
    def _parse_toml(content: str | bytes) -> Dict[str, Any]:
        try:
            import tomllib  # type: ignore
            raw = content if isinstance(content, bytes) else content.encode()
            return dict(tomllib.loads(raw.decode()) or {})
        except Exception:
            try:
                import toml  # type: ignore
                text = content if isinstance(content, str) else content.decode()
                return dict(toml.loads(text) or {})
            except Exception:
                return {}

    try:
        # 1. Try reading from the file (local dev)
        root = Path(__file__).parent.parent
        secrets_path = root / ".streamlit" / "secrets.toml"
        if secrets_path.exists():
            with open(secrets_path, "rb") as f:
                return _parse_toml(f.read())

        # 2. Fall back to env var (Render / Railway / any cloud host).
        #    Set STREAMLIT_SECRETS_TOML to the full contents of secrets.toml.
        env_toml = os.environ.get("STREAMLIT_SECRETS_TOML", "").strip()
        if env_toml:
            return _parse_toml(env_toml)

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
