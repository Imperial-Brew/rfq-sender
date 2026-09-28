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

## 2026-09-28 — T0.2 start (Claude)
- Baseline: `import api.main` OK; `pytest` fails pre-existing (tomllib missing in conftest, not introduced here).
- Skipped from A: `rfq-fixes.bundle` (SHA 7cde928 in branch claude/brave-fermi-vkypev, NOT master — needs Dustin);
  `Claude outputs/` (contains PLAN/PROGRESS/SPEC copies from desktop app — leave for Dustin to verify).
- Executing sections A–D on branch chore/T0.2-cleanup.

## 2026-09-28 — T0.2 complete (Claude)
- Section A: deleted 9 tracked files (stale logs, 0-byte configs, Streamlit DB, junie errors, runtime.txt).
  Skipped: rfq-fixes.bundle (SHA 7cde928 only in claude/brave-fermi-vkypev, not master); Claude outputs/ (has PLAN/SPEC/PROGRESS copies — Dustin to verify).
- Section B: moved 5 scratch files to scratch/ (gitignored). Added scratch/ to .gitignore.
- Section C: pw_gen.py → scripts/create_user_hash.py; goals.md → docs/goals.md.
- Section D: 63 Junie docs → docs/archive/junie/; archive README added; README.md links updated.
- All 4 commits on chore/T0.2-cleanup; import check green throughout.
