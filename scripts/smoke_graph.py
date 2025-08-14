# scripts/smoke_graph.py
import time, os, json, requests
from pathlib import Path

# Python 3.12: tomllib is built-in
import tomllib

def load_secrets():
    p = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    az = data["azure"]
    ex = data["exchange"]
    return az, ex

def fetch_token(tenant_id, client_id, client_secret):
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    form = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    t0 = time.time()
    r = requests.post(url, data=form, timeout=12)
    print("TOKEN status:", r.status_code, "elapsed:", round(time.time() - t0, 2), "s")
    print("TOKEN body:", r.text[:400], "...")
    r.raise_for_status()
    return r.json()["access_token"]

def create_draft(token, user_upn):
    url = f"https://graph.microsoft.com/v1.0/users/{user_upn}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "subject": "RFQ Smoke Test (Graph)",
        "body": {"contentType": "HTML", "content": "<p>If this shows up, Graph works.</p>"},
        "toRecipients": [{"emailAddress": {"address": user_upn}}],
    }
    t0 = time.time()
    r = requests.post(url, headers=headers, json=body, timeout=12)
    print("DRAFT status:", r.status_code, "elapsed:", round(time.time() - t0, 2), "s")
    print("DRAFT body:", r.text[:400], "...")
    r.raise_for_status()
    return r.json()["id"]

if __name__ == "__main__":
    # Don’t inherit corporate proxies for this quick test
    requests.sessions.Session.trust_env = False

    az, ex = load_secrets()
    print("Tenant:", az["tenant_id"][:8] + "...", "Client:", az["client_id"][:8] + "...", "User:", ex["username"])

    token = fetch_token(az["tenant_id"], az["client_id"], az["client_secret"])
    print("Token length:", len(token))

    draft_id = create_draft(token, ex["username"])
    print("Draft ID:", draft_id)
    print("✅ Check Outlook → Drafts.")

