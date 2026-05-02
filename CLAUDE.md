# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RFQ Sender is a manufacturing Request for Quote (RFQ) management system. It handles vendor communication, secure file sharing via Box, and quote tracking. The app is in active migration from a Streamlit UI to a FastAPI + React stack.

## Commands

### Backend (Python)

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-api.txt   # FastAPI-specific

# Run legacy Streamlit UI
streamlit run streamlit_app\app.py

# Run FastAPI backend
uvicorn api.main:app --reload          # http://localhost:8000, docs at /docs

# Run tests
pytest -q                              # all tests
pytest tests/email -v                  # single directory
pytest tests/email/test_graph.py -v   # single file

# Lint / format
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
npm run build
npm run lint
```

## Architecture

### Stack

| Layer | Technology |
|-------|-----------|
| Legacy UI | Streamlit (production, maintained) |
| New UI | React 18 + TypeScript + Vite |
| API | FastAPI + Uvicorn |
| Data fetching | TanStack React Query |
| Auth (API) | JWT via `python-jose` + bcrypt |
| Email | Microsoft Graph API (creates Outlook drafts) |
| File storage | Box SDK (JWT auth) |
| Database | SQLite (dev); CSV files for queue/specs/responses |

### Directory Layout

```
api/             FastAPI app (new backend)
  main.py        App entry point
  deps.py        JWT auth dependency (get_current_user)
  routers/       auth, queue, specs, vendors
  models/        Pydantic schemas
core/            Shared business logic used by both Streamlit and FastAPI
  config.py      Centralized config and logging setup
  email/         Microsoft Graph client, email composition
  auth/          User YAML management
  queue/         Queue CRUD
  specs/         Specifications logic
  vendors/       Vendor management
frontend/src/
  api/           Axios API client functions
  context/       AuthContext (JWT storage)
  pages/         Page-level components
  components/    Shared UI components
streamlit_app/   Legacy UI (still active in production)
utils/           Thin helpers used by Streamlit pages
templates/       Jinja2 email templates
tests/           Mirrors core/ structure
```

### Request Flow (FastAPI + React)

```
React component
  → frontend/src/api/*.ts  (axios, Bearer token)
  → Vite proxy strips /api prefix
  → FastAPI router (api/routers/*.py)
  → get_current_user() JWT check (api/deps.py)
  → core/* business logic
  → SQLite / Box / Microsoft Graph
```

### Authentication

- Users stored in `users.yaml`; passwords hashed with bcrypt (`utils/auth.py`)
- FastAPI login (`api/routers/auth.py`) returns a signed JWT (8-hour expiry)
- Frontend stores token in memory/sessionStorage; sends as `Authorization: Bearer <token>`
- `get_current_user()` in `api/deps.py` decodes and validates on every protected route

### Email

Email is sent exclusively through Microsoft Graph (creates an Outlook draft, no direct SMTP). Credentials come from `.streamlit/secrets.toml` under `[azure]`. The Graph client is at `core/email/graph_client.py`.

## Configuration

### `.streamlit/secrets.toml` (required)

Contains Azure OAuth credentials (`[azure]`), company branding (`[company]`), Box config (`[box]`), and email settings (`[exchange]`, `[app]`). This file is the single source of truth for all runtime secrets.

### `.env` (optional, API mode)

```
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
USERS_FILE=users.yaml
```

## Code Conventions

- **Python line limit**: 100 characters (`.flake8`)
- **Type hints**: required on all function signatures
- **Commit format**: `<scope>(<module>): <summary>` — e.g. `feat(email): add graph retry logic`
- **Frontend state**: TanStack React Query for server state; React Context for auth
- Pre-commit hooks enforce flake8, black, isort, and mypy
