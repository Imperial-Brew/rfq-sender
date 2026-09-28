# CLAUDE.md — rfq-sender

Outside-processing (OS) RFQ tool for Athena estimating. Queue parts → share files via Box
(password-protected for CUI/ITAR) → create Outlook drafts per vendor via Microsoft Graph → track sent.

**Read `SPEC.md` for what v1 is and is NOT. Read `PLAN.md` + `PROGRESS.md` before starting work.**

## Stack (current — Streamlit was removed June 2026, do not reference or restore it)
- Backend: FastAPI (`api/`), business logic in `core/` and `utils/`
- Frontend: React 18 + TS + Vite (`frontend/`), TanStack Query, JWT auth in context
- Email: Microsoft Graph, drafts only — never send directly
- Files: Box SDK (JWT app)
- Data: CSV/JSON in `config/` and `docs/OS/`; SQLite in `data_cleaned/`

## Commands
- Backend: `uvicorn api.main:app --reload` (http://localhost:8000/docs)
- Frontend: `cd frontend && npm run dev` (http://localhost:5173, proxies /api)
- Tests: `pytest -q`
- Lint: `flake8` · Frontend build check: `cd frontend && npm run build`
- TODO(Dustin): confirm where secrets live now (.env vs .streamlit/secrets.toml) and fix this line

## Rules
- A task is done only when `pytest -q` passes AND `npm run build` passes (if frontend touched).
- Work only on the current task in PLAN.md. New ideas → PLAN.md "Backlog". Do not build them.
- Every bug fix gets a regression test first (fail → fix → pass).
- Never call real Graph or Box in tests — mock `core/email/graph_client.py` and `utils/box_helpers.py`.
- CUI/ITAR: the Box password is ALWAYS sent in a separate draft, never inline. Do not change this.
- Never edit or print: `.env`, `users.yaml`, `scripts/box/*config*.json`, anything in `data_raw/`.
- No new dependencies without asking.
- Do not write summary/status .md files. Progress goes in PROGRESS.md only (append, 3–5 lines).
- After each task: check the box in PLAN.md, append to PROGRESS.md, commit.

## Conventions
- Python: type hints on signatures, 100-char lines
- Commits: `<type>(<module>): <summary>` e.g. `fix(queue): coerce dtypes in _standardize_df`
- Queue rows are identified by part number + process (a part can have multiple finishes)
