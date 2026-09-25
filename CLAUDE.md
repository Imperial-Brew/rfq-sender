# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RFQ Sender is a manufacturing Request for Quote (RFQ) tool: queue parts, share files
securely via Box, and create Outlook drafts to approved vendors via Microsoft Graph.
It is a FastAPI backend + React frontend deployed as one Render web service. The old
Streamlit UI has been removed (commit `d0f06e9`); don't reintroduce Streamlit code.

## Commands

### Backend (Python 3.11)

```bash
pip install -r requirements.txt -r requirements-api.txt

uvicorn api.main:app --reload          # http://localhost:8000, docs at /docs
                                       # needs JWT_SECRET_KEY in .env (see .env.example)

pytest -q                              # all tests (conftest sets a test JWT secret)
pytest tests/api_routes -v             # FastAPI route tests
pytest tests/mail/test_utils.py -v     # single file

flake8
black --check .
isort --check-only .
mypy
```

### Frontend (React + TypeScript)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api → localhost:8000)
npm run build      # tsc type-check + vite build → frontend/dist (served by FastAPI)
```

There is no frontend lint script; `npm run build` is the type check.

## Architecture

### Stack

| Layer | Technology |
|-------|-----------|
| UI | React 18 + TypeScript + Vite |
| API | FastAPI + Uvicorn (also serves `frontend/dist` in production) |
| Data fetching | TanStack React Query |
| Auth | JWT via `python-jose`; bcrypt hashes in `users.yaml` |
| Email | Microsoft Graph — creates Outlook drafts, never sends |
| File storage | Box SDK (JWT auth) |
| Data | CSV files (queue, specs, RFQ master, responses) stored in Box, with local CSV fallback under `docs/` when Box IDs aren't configured |

### Directory Layout

```
api/
  main.py        App entry; mounts routers under /api/*, serves the SPA
  deps.py        get_current_user / require_role; loads JWT_SECRET_KEY (fails fast if unset)
  routers/       auth, queue, specs, vendors, rfq_master, send_rfq
  models/        Pydantic schemas
core/
  config.py      Config + logging; loads .env, maps [box] secrets to env vars
  secrets.py     get_section(): reads .streamlit/secrets.toml or STREAMLIT_SECRETS_TOML
  email/         Graph client (graph_client.py), EmailManager (templates + drafts)
  specs/         SpecManager
  vendors/       VendorManager (config/vendors.json, docs/OS/*)
utils/
  auth.py        users.yaml loading, bcrypt
  rfq_queue.py   Queue load/save (Box-first, local fallback)
  rfq_tracking.py RFQ Master / responses CSVs (get_tracker(), add_master_entry)
  box_helpers.py Box folder/share/password helpers used by send_rfq
scripts/box/     BoxIntegration + Box-backed CSV stores
frontend/src/
  api/           Axios API client functions
  context/       AuthContext (JWT storage)
  pages/         SendRfqsPage (the /queue page), VendorsPage, SpecsPage, RfqMasterPage, LoginPage
  components/    Nav, AddToQueueForm, QueueEditSidebar, BoxUploadModal
templates/       Jinja2 email templates
tests/           pytest; tests/api_routes covers the FastAPI layer
docs/archive/    Historical notes — do not treat as current
```

`core/auth/` and `core/queue/` are empty packages; the real code is in `utils/`.

### Request Flow

```
React component
  → frontend/src/api/*.ts  (axios, Bearer token, baseURL /api)
  → FastAPI router (api/routers/*.py, mounted at /api/...)
  → get_current_user() / require_role() (api/deps.py)
  → utils/* and core/* business logic
  → Box CSVs / Microsoft Graph
```

### Queue identity

A queue row is identified by **part_number + process** (one part can need several
finishes). Routes that act on one row take the process in the body or a query param;
don't match on part_number alone.

### Drafting flow (`POST /api/send-rfq/email/{part_number}`)

Finds vendors for process/spec → one Graph draft per vendor in the logged-in user's
mailbox → for CUI/ITAR a second draft with the Box password → stamps the queue row's
`sent` → logs one RFQ Master row per successful vendor (`_log_to_rfq_master`), keyed on
qt/so # + part + process + vendor + contact so re-drafts update rather than duplicate.
Never log Box passwords.

### Roles

`viewer` < `buyer` = `engineer` < `estimator` < `admin`, defined in `api/deps.py`
(`_ROLE_RANK`, `normalize_role`, `require_role`) and mirrored in
`frontend/src/api/auth.ts` (`hasRole`). Keep the two in sync. Box/draft/RFQ Master
edit routes require `buyer`; queue add/edit and vendor approvals `estimator`;
deletes and spec creation `admin`.

## Configuration

Two places only (templates are checked in):

- **`.env`** (local) / Render env var: `JWT_SECRET_KEY` (required), optional
  `USERS_FILE`, `FRONTEND_ORIGIN`. Template: `.env.example`.
- **`.streamlit/secrets.toml`** (local) / Render env var `STREAMLIT_SECRETS_TOML`
  (whole file): `[azure]`, `[box]`, `[company]`, `[exchange]`, `[app]`.
  Template: `.streamlit/secrets.toml.example`. The folder name is historical.

See the README's "Configuration" section for the full key list.

## Code Conventions

- **Python line limit**: 100 characters (`.flake8`)
- **Type hints**: required on all function signatures
- **Commit format**: `<scope>(<module>): <summary>` — e.g. `feat(email): add graph retry logic`
- **Frontend state**: TanStack React Query for server state; React Context for auth
- Default branch is `master`; CI runs pytest + frontend build on push/PR
- Pre-commit hooks enforce flake8, black, isort, and mypy
