# core/secrets.py
from typing import Dict, Any

def get_section(name: str) -> Dict[str, Any]:
    try:
        import streamlit as st
        return dict(st.secrets.get(name, {}))
    except Exception:
        return {}

def get_exchange_settings(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    s = get_section("exchange")
    s.update(overrides or {})
    return s

def get_company_info(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    s = get_section("company")
    s.update(overrides or {})
    return s
