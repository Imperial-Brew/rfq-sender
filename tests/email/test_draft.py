# tests/email/test_draft.py
import os, sys
from pathlib import Path

# Make project root importable
sys.path.append(str(Path(__file__).resolve().parents[2]))

from core.email.email_manager import EmailManager  # adjust if your path differs

def test_ews_draft_creation():
    mgr = EmailManager(
        template_path="docs/email_templates/rfq.html",  # adjust path
        exchange_settings={"cc": None},
        company_info={
            "name": "Athena",
            "sender_name": "Dustin Drab",
            "sender_title": "Estimating Manager",
            "sender_email": os.environ.get("EXCHANGE_USERNAME", ""),
            "sender_phone": "555-555-5555",
            "address": "123 Main St",
        },
    )
    mgr.initialize_exchange()
    ok = mgr.create_draft_email(
        recipient=os.environ.get("EXCHANGE_USERNAME", ""),
        subject="RFQ Smoke Test",
        body="<p>If you see this in Drafts, TLS + EWS is happy.</p>",
        attachments=None,
    )
    assert ok is True
