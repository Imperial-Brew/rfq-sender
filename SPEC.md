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
5. Mark queue items sent, per part+process+vendor.
6. Log each vendor response manually: status (Sent / Quoted / No-bid / No response), price, lead time,
   vendor quote #, valid-until, notes; attach the vendor's quote PDF to the part's Box folder.
7. "Awaiting response" view: open RFQs sorted by days since sent, so you know who to chase.
8. Compare view per part+process: all vendor responses side by side ($, lead time, valid-until).

## Data model note
Responses live in one table keyed by part + process + vendor (one row per RFQ sent).
Manual entry writes to it in v1; automated intake (backlog) will write to the SAME table later.

## Definition of done (v1.0)
- [ ] An estimator who isn't Dustin can run steps 1–8 from the React UI without help, 5 real RFQs in a row
      (sent → responses logged → winner picked from compare view).
- [ ] `pytest -q` green, with tests covering queue CRUD, send_rfq, CUI/ITAR password split, vendor lookup,
      response logging, and the awaiting/compare views.
- [ ] CI runs on every push to the canonical branch.
- [ ] One canonical copy of the repo (see PLAN M0).
- [ ] README + CLAUDE.md describe the app as it actually is.

## Non-goals for v1 (Backlog, not now)
- Auto-adding parts from Paperless Parts (poll/webhook) → v1.1, likely via PaperlessReporting
- Automated response intake: reading the reply mailbox via Graph, matching replies to RFQs,
  extracting price/lead time (fills the v1 response table — no new data model)
- Pushing quotes back into Paperless Parts
- Material and Hardware RFQs
- Vendor performance analytics across RFQs (response rate, win rate, avg lead time)
- Multi-user roles beyond current JWT login
