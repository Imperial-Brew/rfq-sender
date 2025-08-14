import os, pytest
from core.email.graph_client import create_draft

@pytest.mark.skipif(not os.getenv("EXCHANGE_USERNAME"), reason="Exchange UPN not set")
def test_graph_draft_creation():
    user = os.environ["EXCHANGE_USERNAME"]  # your conftest can load this from secrets.toml
    msg_id = create_draft(
        user_upn=user,
        subject="RFQ Smoke Test (Graph)",
        html_body="<p>If you see this in Drafts, Graph is working.</p>",
        to=[user],
    )
    assert isinstance(msg_id, str) and len(msg_id) > 0
