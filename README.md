# RFQ Sender

Internal tool for sending Requests for Quote (RFQs) to outside-processing vendors
(finishing, plating, heat treat, …): build a queue of parts, share the part files
securely through Box, and create personalized Outlook drafts for every approved
vendor.

**Stack:** React 18 + TypeScript (Vite) frontend · FastAPI backend · Microsoft Graph
for email drafts · Box for files and shared data. Deployed on Render.

## Contents
- [What it does today](#what-it-does-today)
- [Project structure](#project-structure)
- [Local setup](#local-setup)
- [Configuration: which secret goes where](#configuration-which-secret-goes-where)
- [Users and logins](#users-and-logins)
- [Deploying on Render](#deploying-on-render)
- [Testing and CI](#testing-and-ci)
- [Roadmap / not built yet](#roadmap--not-built-yet)

## What it does today

| Page | What you can do |
|------|-----------------|
| **Queue** (`/queue`) | Add parts (one row per part + process), edit them, create a Box folder and share link per part (password-protected automatically for CUI/ITAR), and create Outlook drafts for every vendor approved for that process/spec. Drafts are never sent automatically. |
| **Vendors** (`/vendors`) | Search vendors, see contacts and process/spec approvals, add approvals. |
| **Specs** (`/specs`) | Browse and add "familiar specs" per process and issuer. |
| **RFQ Master** (`/rfq-master`) | One row per RFQ sent to a vendor. A row is added automatically each time a draft is created; update status, received date and notes by hand. |

For CUI/ITAR parts the Box password is sent in a **second, separate** draft so it
never travels with the link.

## Project structure

```
api/              FastAPI app — main.py, deps.py (JWT auth), routers/, models/
core/             Business logic: config, secrets loader, email (Graph), specs, vendors
utils/            Queue, auth, Box helpers, RFQ tracking — used by the API
scripts/box/      Box SDK integration (BoxIntegration, CSV stores)
frontend/         React app (Vite + TypeScript); `npm run build` → frontend/dist/
config/           vendors.json, process master, email templates
docs/             Working CSVs (local fallback when Box isn't configured), OS vendor data
docs/archive/     Old notes — historical only
templates/        Jinja2 email templates
tests/            pytest suite (tests/api_routes covers the FastAPI layer)
users.yaml        Login accounts (bcrypt hashes)
```

## Local setup

**Prerequisites:** Python 3.11, Node 20.

```bash
# 1. Python environment
python -m venv venv
venv\Scripts\activate            # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt -r requirements-api.txt

# 2. Configuration — see the next section for what goes in each file
copy .env.example .env                                   # macOS/Linux: cp
copy .streamlit\secrets.toml.example .streamlit\secrets.toml

# 3. Run the API  →  http://localhost:8000  (interactive docs at /docs)
uvicorn api.main:app --reload

# 4. Run the frontend (second terminal)  →  http://localhost:5173
cd frontend
npm install
npm run dev                       # proxies /api → localhost:8000
```

Check the Graph connection any time with `python scripts/smoke_graph.py`.

## Configuration: which secret goes where

There are exactly **two places** configuration lives. Each has a checked-in
template listing every key with comments:

| What | Local machine | Render | Template |
|------|---------------|--------|----------|
| `JWT_SECRET_KEY` — signs logins. **Required**; the API won't start without it. | `.env` | Environment variable `JWT_SECRET_KEY` | [`.env.example`](.env.example) |
| Everything else: `[azure]` Graph credentials, `[box]` JWT config + file IDs, `[company]` branding, `[exchange]`, `[app]` | `.streamlit/secrets.toml` | Environment variable `STREAMLIT_SECRETS_TOML` containing the **entire** TOML file | [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) |

Notes:
- Both real files (`.env`, `.streamlit/secrets.toml`) are git-ignored. Never commit them.
- Locally, `.streamlit/secrets.toml` takes priority over `STREAMLIT_SECRETS_TOML`.
- The `.streamlit` folder name is historical; Streamlit itself is no longer used.
- **Use a different `JWT_SECRET_KEY` locally than on Render.** Changing it just logs
  everyone out; nothing else is affected.
- If the `[box]` file/folder IDs are empty, the app reads and writes the local CSVs
  under `docs/` instead of the shared Box copies. That's handy for local testing,
  but those changes won't be visible on Render.

### Keys at a glance

| Section | Keys | Used for |
|---------|------|----------|
| `[azure]` | `tenant_id`, `client_id`, `client_secret` | Creating Outlook drafts via Microsoft Graph. The Azure app needs the **application** permission `Mail.ReadWrite` with admin consent. |
| `[box]` | `BOX_JWT_JSON` | Box app auth (paste the full JSON from the Box Developer Console). |
| `[box]` | `BOX_QUEUE_FILE_ID` / `_FOLDER_ID` | Shared queue CSV. |
| `[box]` | `BOX_FAMILIAR_SPECS_FILE_ID` | Specs page data. |
| `[box]` | `BOX_RFQ_MASTER_FILE_ID` / `_FOLDER_ID` | RFQ Master log. |
| `[box]` | `BOX_RFQ_RESPONSES_FILE_ID` / `_FOLDER_ID` | Vendor responses (reserved for response tracking). |
| `[company]` | `name`, `logo_url`, `address`, `sender_name`, `sender_title`, `sender_email`, `sender_phone` | Email template branding and signature. |
| `[exchange]` | `username`, `cc` | Fallback mailbox for scripts; optional CC on every RFQ. |
| `[app]` | `subject_prefix` | Prefix for every email subject. |

Drafts are created in the mailbox of **whoever is logged in** (their `users.yaml`
email), so each user's email must be a real Microsoft 365 mailbox in the tenant.

## Users and logins

Accounts live in `users.yaml` (committed; passwords are bcrypt-hashed). The API
knows three roles; any other value (e.g. `engineer`, `Buyer`) is treated as `viewer`.

| Action | Minimum role |
|--------|--------------|
| View everything, create Box folders, create drafts, edit RFQ Master rows | any logged-in user |
| Add/edit queue items, add vendor approvals | `estimator` |
| Delete queue items or RFQ Master rows, add specs | `admin` |

To add a user or reset a password:
```bash
python pw_gen.py        # prompts for email + password, prints the hash
```
Paste the hash into `users.yaml` as `password_hash`, commit, and redeploy.
Logins last 8 hours.

## Deploying on Render

The service is a single Render **Web Service**: FastAPI serves the API and the
built React app from the same origin.

| Setting | Value |
|---------|-------|
| Runtime | Python 3.11 (`runtime.txt`) |
| Build command | `pip install -r requirements.txt -r requirements-api.txt && cd frontend && npm ci && npm run build` |
| Start command | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Environment variables | `JWT_SECRET_KEY` (random, 64 hex chars), `STREAMLIT_SECRETS_TOML` (full contents of your filled-in `secrets.toml`), `PYTHONUNBUFFERED=1` |

Health check: `GET /health`.

## Testing and CI

```bash
pytest -q                 # backend (JWT_SECRET_KEY is set automatically for tests)
cd frontend && npm run build   # type-check + build
```

GitHub Actions (`.github/workflows/python-tests.yml`) runs both on every push and
pull request to `master`.

## Roadmap / not built yet

- **Vendor response tracking.** Nothing reads replies or quotes yet. Sample
  `.eml`/`.msg` files are in `data_raw/RFQ responses/`, and `rfq_responses.csv`
  plus its Box IDs are reserved for this.
- Importing parts into the queue automatically (e.g. from Paperless Parts).
- Customer approved-vendor lists (AVLs); spec classes and exceptions.
- Material and hardware RFQs (only outside processing is supported today).

See [`CHANGELOG.md`](CHANGELOG.md) for history. Older design notes are in
[`docs/archive/`](docs/archive/). They're historical and don't describe the current app.

## License

MIT. See [LICENSE](LICENSE).
