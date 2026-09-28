# SPEC — rfq-sender v1.0

> Draft by Claude from goals.md + commit history. Dustin: edit/cut, then freeze.

## Problem
Getting outside-processing (finish/plating/anodize/etc.) quotes means finding capable vendors per
process+spec, sharing controlled files securely, and emailing each vendor separately. Manual = slow,
error-prone, and risky on CUI/ITAR.

## User
Athena estimators (Dustin + team). Internal only.

## v1.0 does (the loop)
1. Add a part to the queue with process + spec (manual entry or CSV).
2. App suggests approved vendors for that process/spec.
3. Create a Box folder per part, upload files, generate share link; CUI/ITAR → password-protected.
4. Create one Outlook draft per vendor (no BCC), with link + spec table; CUI/ITAR password in a separate draft.
5. Mark queue items sent, per part+process.

## Definition of done (v1.0)
- [ ] An estimator who isn't Dustin can run steps 1–5 from the React UI without help, 5 real RFQs in a row.
- [ ] `pytest -q` green, with tests covering queue CRUD, send_rfq, CUI/ITAR password split, vendor lookup.
- [ ] CI runs on every push to the canonical branch.
- [ ] One canonical copy of the repo (see PLAN M0).
- [ ] README + CLAUDE.md describe the app as it actually is.

## Non-goals for v1 (Backlog, not now)
- Auto-adding parts from Paperless Parts (poll/webhook) → v1.1, likely via PaperlessReporting
- Parsing vendor responses / auto-filling quote tracker
- Pushing quotes back into Paperless Parts
- Material and Hardware RFQs
- Compare $/lead time dashboards
- Multi-user roles beyond current JWT login
