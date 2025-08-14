# tests/email/test_graph_token.py
import os, pytest
from core.email.graph_client import _get_token  # ok for tests

@pytest.mark.skipif(
    not (os.getenv("AZURE_TENANT_ID") and os.getenv("AZURE_CLIENT_ID") and os.getenv("AZURE_CLIENT_SECRET")),
    reason="Azure app creds not set"
)
def test_graph_token_fetch():
    tok = _get_token()
    assert isinstance(tok, str) and len(tok) > 100
