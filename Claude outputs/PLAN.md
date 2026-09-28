# PLAN — rfq-sender v1.0

One task per session. Each has an acceptance check. Don't start M(n+1) until M(n) is checked off.

## M0 — Clean the shop floor (you + Claude, ~1 evening)
- [ ] T0.1 Pick ONE canonical repo (C:\PycharmProjects, P:\WORK\APPS, GitHub). Retire the others.
      Accept: other copies archived/read-only; no more .bundle shuttling.
- [ ] T0.2 Move `.junie/` → `docs/archive/junie/` (or delete). Delete stale PROJECT_STATUS / ROADMAP.
      Accept: no doc in repo claims Streamlit is live.
- [ ] T0.3 Remove scratch from repo root: scratch.json, test.py, sql_testing.py, pw_gen.py, rfq-fixes.bundle,
      logs.csv, dist/, *.egg-info. Add to .gitignore. Accept: `git status` clean, root has only real project files.
- [ ] T0.4 Install new CLAUDE.md / SPEC.md / PLAN.md / PROGRESS.md.
- [ ] T0.5 Fix CI: workflow targets `main` but branch is `master`; Python matrix 3.8–3.10 vs local 3.13.
      Accept: CI runs and reports on push (or decide no CI if repo leaves GitHub — then a local pre-push hook).

## M1 — Test harness on the money path
- [ ] T1.1 Delete/quarantine Streamlit-era tests (tests/fixes, anything importing streamlit_app).
      Accept: `pytest -q` collects without import errors.
- [ ] T1.2 Fixtures: fake queue CSV, fake vendors, mocked Graph client, mocked Box helpers.
- [ ] T1.3 Tests for `api/routers/queue.py`: CRUD + the dtype-coercion bugs from Jul/Sep commits.
- [ ] T1.4 Tests for `api/routers/send_rfq.py`: one draft per vendor, part+process matching,
      CUI/ITAR → separate password draft, missing password auto-generated.
- [ ] T1.5 Tests for vendor lookup by process/spec (process_master.json).
      Accept (M1): all green; deliberately breaking the password split makes a test fail.

## M2 — Close v1
- [ ] T2.1 Walk the SPEC loop end-to-end in the UI; log every friction point as a task here.
- [ ] T2.2 Fix those tasks (each with a test).
- [ ] T2.3 Hand to a teammate for 5 real RFQs. Accept: SPEC "Definition of done" all checked.
- [ ] T2.4 Tag v1.0. Update README to match reality.

## Backlog (do not build until v1.0 is tagged)
- Paperless Parts → queue auto-add (poll for OS operations; hub = PaperlessReporting)
- Vendor response parsing (scripts/utils/response_parser.py exists — evaluate)
- Material RFQs, Hardware RFQs
- Push quotes back to Paperless Parts
