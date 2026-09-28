# PROGRESS — append-only session log (newest at bottom, 3–5 lines each)

## 2026-09-28 — triage (Claude, Cowork)
- Reviewed C:\PycharmProjects\rfq-sender. App is live and in use, not abandoned: 183 commits, mostly bug-driven fixes.
- Found: 3 copies of repo, CLAUDE.md still describes deleted Streamlit app, ~60 AI summary docs in .junie/,
  CI never runs (targets `main`, branch is `master`), no tests on api/routers (send_rfq, queue).
- Next: M0 (cleanup + pick canonical copy).

## 2026-09-28 — cleanup manifest (Claude, Cowork)
- Wrote CLEANUP.md from git index + live-code grep. Sections A–D safe; E (untrack users.yaml, data_raw/) needs Dustin.
- Found users.yaml, vendor reply emails, vendor quotes, contacts committed to GitHub history.
- Live code imports scripts/box/* — production code in scripts/; queued as T0.6 after tests.
