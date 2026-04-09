# Checks

Last reviewed: 2026-04-10

This doc defines the local validation loop before opening a PR.

## Chosen Toolchain

- Backend: Python 3.11 + FastAPI
- Frontend: React + TypeScript + Vite
- Frontend runtime/tooling: Node.js + npm
- Local persistence: PostgreSQL

## Canonical Commands

- Format: `poetry run black .`
- Lint (architecture/docs): `scripts/lint-architecture`
- Typecheck/build: `npm --prefix frontend run build`
- Frontend lint: `npm --prefix frontend run lint`
- Unit tests: `poetry run pytest`

## Preferred Local Run Path

Start full stack:

```bash
scripts/dev-up
```

Stop full stack:

```bash
scripts/dev-down
```

Reset stack + fresh DB:

```bash
scripts/dev-reset
```

Smoke check:

```bash
scripts/dev-smoke
```

## Suggested Sequence (Before Commit / PR)

1. Format
2. Lint + typecheck
3. Unit tests
4. Frontend build
5. Run locally + manual checks

## Manual Checks (High Signal)

- App starts cleanly (no obvious errors in logs/console)
- Uploading a valid PDF reaches backend and returns a result
- Suggested journal entry renders clearly in UI
- Invalid or unsupported files return useful errors
- Approve/decline update status and persist
- Approval is blocked for unbalanced entries
- Approval is blocked for duplicate-flagged entries
- Previously processed invoices can still render PDF in viewer
- No backend traceback or browser console error on happy path
