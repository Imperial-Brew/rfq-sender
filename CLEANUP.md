# CLEANUP — rfq-sender repo pass (2026-09-28)

Built from the working folder + git index (258 tracked files) + grepping `api/`, `core/`, `utils/` for what
live code actually reads. Executor (Claude Code): follow the rules below exactly.

## Rules for the executor
- Use `git mv` / `git rm` for tracked files so history follows. Plain delete only for untracked files.
- One commit per section (A–F), message `chore(cleanup): section X — <summary>`.
- After EACH section: `python -c "import api.main"` and `pytest -q` must not get worse than baseline.
  Record the baseline before starting (pass/fail counts) in PROGRESS.md.
- Touch nothing not listed here. Anything that surprises you → stop and add a note under "Questions".
- Items marked **[DUSTIN]** need his OK before acting.

---

## A. Delete — tool leftovers, build output, logs
| Path | Tracked | Why |
|---|---|---|
| `CLAUDE-1.md` | no | Identical copy of CLAUDE.md (desktop-app save artifact) |
| `Claude outputs/` | no | Desktop-app save folder. **[DUSTIN]** glance inside first |
| `rfq-fixes.bundle` | yes | Manual commit shuttle from Sep 24. First verify: `git bundle list-heads rfq-fixes.bundle`, confirm those SHAs are in `master` (`git branch --contains <sha>`) |
| `commit_message.txt` | yes | Stale one-off commit message from Aug 2025 |
| `logs.csv` | yes | Runtime log |
| `logs/*.log` | no | Runtime logs; add `logs/` to .gitignore (keep dir via `.gitkeep`) |
| `.junie/errors/` | yes | ~900 KB of Streamlit-era error dumps |
| `data_cleaned/streamlit_app.db` | yes | Streamlit is gone |
| `dist/`, `rfq_sender.egg-info/`, `.pytest_cache/` | no | Build/cache output; add to .gitignore |
| `runtime.txt` | yes | Render/Heroku leftover (says 3.11; you run 3.13) |
| `config/exceptions.yml`, `config/processes.yml` | yes | 0-byte files |

## B. Move to `scratch/` (gitignored, kept locally — not part of the app)
| Path | Why |
|---|---|
| `scratch.json` (526 KB) | Scratch |
| `test.py` | Ad-hoc M2M vendor pull (pyodbc). Not a test — pytest may try to collect it |
| `sql_testing.py` | Reads `config/vendors.consolidated-.json`, prints. One-off |
| `vendors.consolidated.json` (root) | Not read by live code |
| `config/vendors.consolidated-.json` | Trailing-dash stray copy; not read by live code |

Add `scratch/` to .gitignore.

## C. Move to the right place
| From | To | Why |
|---|---|---|
| `pw_gen.py` | `scripts/create_user_hash.py` | Real tool (hash a password for users.yaml), wrong place |
| `.junie/mds/goals.md` | `docs/goals.md` | Original vision doc — worth keeping, SPEC.md references it |

## D. Archive AI/agent docs
| From | To |
|---|---|
| `.junie/mds/*` (~60 files) | `docs/archive/junie/` |
| `.junie/guidelines.md`, `.junie/user requests.txt` | `docs/archive/junie/` |

Then remove the empty `.junie/`. Add one line to `docs/archive/README.md`: "Historical Junie/AI session notes.
Not current. Do not use as reference." Update README.md links that point into `.junie/`.

## E. Stop tracking sensitive / runtime data  **[DUSTIN — read the note below first]**
`git rm --cached` (keeps local file), then add to .gitignore:
| Path | What it is | Read by live code? |
|---|---|---|
| `users.yaml` | App users + bcrypt hashes | yes → commit `users.example.yaml` with a dummy user |
| `data_raw/` (whole dir) | Real vendor reply emails (.eml/.msg), vendor quotes CSV, old queues | no |
| `data_cleaned/rfq_log.db` | Runtime DB | check with grep before untracking |

**Note:** untracking removes these from future commits, NOT from git history. Everything above is already
in the Imperial-Brew GitHub history. Given the no-GitHub-for-Athena-apps policy, the clean fix is PLAN T0.1:
make the P: share-drive repo canonical, start it fresh (or `git filter-repo` these paths), and delete/privatize
the GitHub repo. Same question applies to `docs/OS/contacts.csv` and `config/contacts.yml` (vendor contacts) —
live code reads contacts.csv, so moving it is a code change (see F).

## F. NOT this pass — code changes (become PLAN tasks, each with tests)
- `scripts/box/box_integration.py`, `box_queue_store.py`, `box_csv_store.py` are imported by live code
  (send_rfq, rfq_queue, rfq_tracking, spec_manager) → move to `core/box/`, fix imports.
- Runtime data lives in `docs/` (`queue.csv`, `rfq_master.csv`, `rfq_responses.csv`, `docs/OS/*`) → move to
  `data/`, update paths in `core/config.py`, `utils/rfq_tracking.py`, `core/vendors/vendor_manager.py`.
- Three template dirs (`templates/`, `config/templates/`, `docs/templates/`) with duplicate files → one `templates/`,
  remove fallback discovery in `send_rfq.py` and `core/config.py`.
- `core/config.py` still tries `import streamlit` → remove.
- `scripts/mail/*` (incl. 86 KB `email_from_list.py`), `cli/`, `config/contacts.yml`, `config/email.yml`,
  `config/vendor-processes.yml`: not referenced by api/core/utils → confirm unused, then archive.
- Root-level `tests` for Streamlit era handled in PLAN T1.1.

## Questions (executor adds here)
