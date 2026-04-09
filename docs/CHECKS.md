# Checks

Last reviewed: 2026-04-09


This doc defines the standard local validation loop before opening a PR.

## Chosen Toolchain

- Backend: Python 3.11 + FastAPI
- Frontend: React + TypeScript + Vite
- Frontend runtime/tooling: Node.js + npm
- Local persistence: PostgreSQL

These commands reflect the current repository layout.

## Target canonical commands

- Format: `poetry run black .`
- Lint: `scripts/lint-architecture`
- Typecheck: backend via `poetry run mypy .`; frontend via `npm --prefix frontend run build`
- Frontend lint: `npm --prefix frontend run lint`
- Unit tests: `poetry run pytest`
- Build: frontend via `npm --prefix frontend run build`
- Run locally: backend via `poetry run uvicorn backend.app.main:app --reload`; frontend via `npm --prefix frontend run dev`

## Suggested sequence (before commit / PR)
1. Format
2. Lint + typecheck
3. Unit tests
4. Build
5. Run locally + manual checks (below)

## Run locally
Standard local workflow:

- Database:
- `scripts/db-up` to start Postgres via Docker Compose
- `scripts/db-migrate` to apply schema + account seed data
- `scripts/db-down` to stop Postgres
- Frontend setup:
- `npm --prefix frontend install`
- Backend command: `poetry run uvicorn backend.app.main:app --reload`
- Frontend command: `npm --prefix frontend run dev`
- Required env: `ANTHROPIC_API_KEY` and `DATABASE_URL`
- Seed data: optional sample PDFs for fast manual verification
- Common troubleshooting: check backend logs first, then browser console/network tab

## Manual checks (examples)
Keep this short and focused on high-signal flows.

- App starts cleanly (no obvious errors in logs/console)
- Uploading a valid PDF reaches the backend and returns a result
- Suggested journal entry renders clearly in the UI
- Invalid or unsupported files produce a useful error message
- Journal entry uses accounts from the provided chart of accounts
- Approve action updates status and persists it
- Decline action updates status and persists it
- Approval is blocked if debits and credits are unbalanced
- No backend traceback or browser console error appears on the happy path

## Optional: single entrypoint script
If you want a one-liner, keep it as a convenience (not the source of truth) and ensure it matches this doc.
