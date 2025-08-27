# Release Checklist

This checklist helps ensure a clean, repeatable release process. Adapt to your workflow as needed.

## 1. Pre-flight
- [ ] Confirm the app runs via Streamlit: `streamlit run streamlit_app\app.py`
- [ ] Confirm key scripts run (if used):
  - [ ] `python scripts\mail\email_from_list.py --help`
  - [ ] `python scripts\smoke_graph.py` (creates Draft via Microsoft Graph)
- [ ] Ensure secrets are not committed: `.env`, `.streamlit/secrets.toml`, Box config JSON, etc.

## 2. Versioning
- [ ] Decide the next version (Semantic Versioning): MAJOR.MINOR.PATCH
- [ ] Update version in `pyproject.toml` → `[project].version`

## 3. Changelog
- [ ] Collect changes into `CHANGELOG.md` under `## [Unreleased]`
- [ ] Create a new release section, e.g. `## [0.x.y] - YYYY-MM-DD`
- [ ] Move items from Unreleased to the new section
- [ ] Keep Unreleased at the top for future changes

## 4. Quality gates
- [ ] Run unit tests: `pytest -q`
- [ ] Optional: run linters/formatters:
  - [ ] `flake8`
  - [ ] `black --check .`
  - [ ] `isort --check-only .`
  - [ ] `mypy` (if types enforced)
- [ ] Review `logs/` to ensure no sensitive data is being written by default

## 5. Packaging sanity
- [ ] Verify `pyproject.toml` metadata (name, description, license, classifiers)
- [ ] Verify `MANIFEST.in` includes required resources (docs, templates, config)
- [ ] Build source and wheel distributions:
  - [ ] `python -m build` (requires `pip install build`)
- [ ] Inspect the built artifacts in `dist/` (confirm templates/config are present)

## 6. Tag and release
- [ ] Commit all changes: `git commit -m "chore(release): prepare v0.x.y"`
- [ ] Create an annotated tag: `git tag -a v0.x.y -m "Release v0.x.y"`
- [ ] Push commits and tags: `git push && git push --tags`
- [ ] Create a GitHub release using the tag; paste notes from `CHANGELOG.md`

## 7. Post-release
- [ ] Bump `CHANGELOG.md` with a fresh `## [Unreleased]` header (if not present)
- [ ] Open issues for any follow-up tasks discovered during release

## Notes
- The application uses Microsoft Graph for email Draft creation (configure via `.streamlit/secrets.toml`).
- Templates used by email flows reside in `docs/templates/`.
- Vendor and email configuration YAML files are in `config/`.
