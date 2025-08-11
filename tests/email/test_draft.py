# tests/email/test_draft.py
import os, logging, pytest
from core.email.email_manager import EmailManager

# show errors from your code and exchangelib
logging.basicConfig(level=logging.INFO)
logging.getLogger("exchangelib").setLevel(logging.DEBUG)

@pytest.mark.skipif(
    not (os.getenv("EXCHANGE_USERNAME") and os.getenv("EXCHANGE_PASSWORD")),
    reason="Exchange creds not set"
)
def test_ews_draft_creation():
    mgr = EmailManager(
        template_path="docs/email_templates/rfq.html",
        exchange_settings={"cc": None},
        company_info={}
    )

    # 1) Initialize and do a *lightweight* EWS call to confirm auth
    mgr.initialize_exchange()
    try:
        _ = mgr.account.root.total_count   # triggers a simple EWS request
        logging.info("EWS auth OK; root.total_count fetched.")
    except Exception as e:
        pytest.fail(f"EWS auth failed: {e!r}")

    # 2) Try creating the draft, but fail with a helpful message if it returns False
    ok = mgr.create_draft_email(
        recipient=os.environ["EXCHANGE_USERNAME"],
        subject="RFQ Smoke Test",
        body="<p>If you see this in Drafts, TLS + EWS is happy.</p>",
        attachments=None,
    )
    assert ok, "create_draft_email() returned False – check the ERROR log line above for the exact reason."
