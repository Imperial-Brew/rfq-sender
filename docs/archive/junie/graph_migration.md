# Graph Migration Summary (EWS Removed)

This project has completed migration to a single, secure Microsoft Graph mail backend. All EWS code paths, insecure TLS overrides, and ExchangeConfig-based settings have been removed or deprecated.

## What changed
- Microsoft Graph is now the only mail backend.
- EWS and insecure TLS overrides are removed from runtime code.
- Configuration is simplified and centralized in .streamlit/secrets.toml.
- ExchangeConfig is deprecated; do not use it for new code.

## Required Azure app permissions
Your Azure App Registration must have Application permissions with admin consent:
- Mail.ReadWrite (required to create Drafts in a user mailbox)
- Optional: Mail.Send (if you later send messages via API)

Grant admin consent after assigning permissions.

## Configure secrets
Place your configuration in .streamlit/secrets.toml:

[exchange]
username = "user@yourdomain.com"     # mailbox UPN used for drafts
cc       = "quotes@yourdomain.com"   # optional default CC

[azure]
tenant_id     = "<tenant-guid>"
client_id     = "<app-client-id>"
client_secret = "<app-client-secret>"

[company]
name         = "Your Company"
sender_name  = "Your Name"
sender_email = "user@yourdomain.com"
sender_title = "Estimating Manager"
sender_phone = "555-555-5555"

[app]
subject_prefix = "[RFQ-]"

Notes:
- Only [exchange].username (the mailbox UPN) is required to target the mailbox for drafts.
- Use [exchange].cc to set a default CC address (optional).

## Quick verification (smoke test)
Use the included script to validate your Graph setup:

PowerShell:

python .\scripts\smoke_graph.py

Expected results:
- Token request returns HTTP 200.
- Draft creation returns HTTP 201 and a Draft appears in Outlook for the configured [exchange].username.

## In-app behavior
- Draft emails are created via Graph only.
- streamlit_app/pages/03_send_rfq_emails.py and EmailManager use [exchange] and [company] secrets.
- Attachments are supported (small direct upload and large via upload session).

## Deprecated/legacy
- EWS code paths and insecure TLS overrides are removed from runtime.
- ExchangeConfig is kept only as a deprecated stub in core/config.py for compatibility but should not be referenced.
- Legacy docs referring to Exchange or SMTP remain for historical context and are marked as legacy.

## Troubleshooting
- 401/403 on Graph calls: ensure the Azure app has the correct Application permissions and admin consent.
- 404 on users/{upn}/messages: verify [exchange].username is correct and exists.
- Attachments >3MB: rely on the upload session path (already implemented).