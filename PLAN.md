# PLAN — rfq-sender v1.0

One task per session. Each has an acceptance check. Don't start M(n+1) until M(n) is checked off.

## M0 — Clean the shop floor (you + Claude, ~1 evening)
- [ ] T0.1 Pick ONE canonical repo (C:\PycharmProjects, P:\WORK\APPS, GitHub). Retire the others.
      Accept: other copies archived/read-only; no more .bundle shuttling.
- [ ] T0.2 Execute CLEANUP.md sections A–D (one commit each). Accept: root has only real project files;
      no doc outside docs/archive claims Streamlit is live; import check + pytest no worse than baseline.
- [ ] T0.3 CLEANUP.md section E after Dustin's OK (tied to T0.1 decision on GitHub history).
- [ ] T0.4 Install new CLAUDE.md / SPEC.md / PLAN.md / PROGRESS.md.
- [ ] T0.5 Fix CI: workflow targets `main` but branch is `master`; Python matrix 3.8–3.10 vs local 3.13.
      Accept: CI runs and reports on push (or decide no CI if repo leaves GitHub — then a local pre-push hook).
- [ ] T0.6 CLEANUP.md section F code moves — do these AFTER M1 tests exist, one move per task:
      box modules → core/box/; runtime CSVs docs/ → data/; one templates/ dir; drop streamlit import;
      archive unused scripts/mail, cli, legacy config yml.

## M1 — Test harness on the money path
- [ ] T1.1 Delete/quarantine Streamlit-era tests (tests/fixes, anything importing streamlit_app).
      Accept: `pytest -q` collects without import errors.
- [ ] T1.2 Fixtures: fake queue CSV, fake vendors, mocked Graph client, mocked Box helpers.
- [ ] T1.3 Tests for `api/routers/queue.py`: CRUD + the dtype-coercion bugs from Jul/Sep commits.
- [ ] T1.4 Tests for `api/routers/send_rfq.py`: one draft per vendor, part+process matching,
      CUI/ITAR → separate password draft, missing password auto-generated.
- [ ] T1.5 Tests for vendor lookup by process/spec (process_master.json).
      Accept (M1): all green; deliberately breaking the password split makes a test fail.

## M2 — Receive quotes (manual)
- [ ] T2.1 Evaluate existing pieces: docs/rfq_responses*.csv, docs/vendor_quote_tracker.csv, data_raw/Vendor_Quotes.csv,
      utils/rfq_tracking.py. Propose ONE response schema (part, process, vendor, sent_at, status, price, lead_time_days,
      vendor_quote_no, valid_until, box_file_link, notes). Accept: Dustin approves schema before any code.
- [ ] T2.2 Storage + core functions: create row on send (status=Sent), update response, list by part/process.
      Accept: unit tests; send_rfq creates one row per vendor draft.
- [ ] T2.3 API: `api/routers/responses.py` — GET by part/process, PATCH one response, GET awaiting (days since sent).
      Accept: router tests with mocked storage.
- [ ] T2.4 UI: log-response form on the queue part row (status, $, LT, quote #, valid-until, notes).
      Accept: `npm run build` passes; manual check logs a response end-to-end.
- [ ] T2.5 Attach vendor quote PDF to the part's existing Box folder; store link on the response row.
      Accept: Box mocked in tests; one real upload verified by hand.
- [ ] T2.6 Awaiting-response view (sorted by days since sent) + per-part compare view ($, LT, valid-until).
      Accept: tests on the sort/filter logic; manual check in UI.

## M3 — Close v1
- [ ] T3.1 Walk the SPEC loop (steps 1–8) end-to-end in the UI; log every friction point as a task here.
- [ ] T3.2 Fix those tasks (each with a test).
- [ ] T3.3 Hand to a teammate for 5 real RFQs. Accept: SPEC "Definition of done" all checked.
- [ ] T3.4 Tag v1.0. Update README to match reality.

## Backlog (do not build until v1.0 is tagged)
- Paperless Parts → queue auto-add (poll for OS operations; hub = PaperlessReporting)
- Automated response intake via Graph mailbox → writes to M2 response table
  (scripts/utils/response_parser.py exists — evaluate then)
- Material RFQs, Hardware RFQs
- Push quotes back to Paperless Parts
