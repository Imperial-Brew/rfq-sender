"""Convenience wrapper for :mod:`scripts.mail.rfq_sender`.

The original RFQ sender implementation lives in ``scripts/email/rfq_sender.py``.
Historically tests and other tooling imported it as ``scripts/rfq_sender``.  At
some point the file was moved into the ``email`` package which left the old
import path broken.  This lightweight module loads the real implementation and
re-exports the functions that are relied upon by the tests and other modules.
"""

from __future__ import annotations

import importlib.util
import os
from types import ModuleType

# Locate the real rfq_sender implementation
_module_path = os.path.join(os.path.dirname(__file__), "mail", "rfq_sender.py")
_spec = importlib.util.spec_from_file_location("_rfq_sender", _module_path)
_rfq: ModuleType = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader  # for type checkers
_spec.loader.exec_module(_rfq)

# Re-export commonly used attributes
logger = _rfq.logger
parse_args = _rfq.parse_args
validate_args = _rfq.validate_args
get_attachments = _rfq.get_attachments
render_template = _rfq.render_template
validate_email = _rfq.validate_email
check_attachments = _rfq.check_attachments

__all__ = [
    "logger",
    "parse_args",
    "validate_args",
    "get_attachments",
    "render_template",
    "validate_email",
    "check_attachments",
]
