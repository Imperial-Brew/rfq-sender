# PROGRESS — append-only session log (newest at bottom, 3–5 lines each)

## 2026-09-28 — triage (Claude, Cowork)
- Reviewed C:\PycharmProjects\rfq-sender. App is live and in use, not abandoned: 183 commits, mostly bug-driven fixes.
- Found: 3 copies of repo, CLAUDE.md still describes deleted Streamlit app, ~60 AI summary docs in .junie/,
  CI never runs (targets `main`, branch is `master`), no tests on api/routers (send_rfq, queue).
- Next: M0 (cleanup + pick canonical copy).
