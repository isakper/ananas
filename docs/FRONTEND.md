# Frontend

Last reviewed: 2026-04-10

## Chosen Stack

- React for UI composition
- TypeScript for typed props, API responses, and safer refactors
- Vite for local development and production builds
- Node.js for package management and frontend tooling

## Why This Stack

- It is a safe mainstream option for a small product UI.
- React is common enough that contributors can follow it easily.
- TypeScript gives helpful guardrails without forcing a complex architecture.
- Vite keeps the setup light and fast.

## Local Runtime Scope

- Frontend support is local-only for this exercise.
- We only target running through the Vite dev server against a local backend.
- We do not maintain separate dev/prod frontend behavior in this repo.

## Setup

1. Verify tooling:
- Node.js `20.x`
- npm `10.x` or later

2. Frontend scaffold in this repo was created with:
```bash
npm create vite@latest frontend -- --template react-ts
```

3. Install dependencies:
```bash
npm --prefix frontend install
```

4. Run locally:
```bash
npm --prefix frontend run dev
```

## Scope

The frontend only needs to do a few things well:

- accept a PDF upload
- send the file to the backend
- show invoice context and suggested journal postings
- allow accountant actions to approve or decline the suggestion
- show loading, success, and error states clearly

Avoid adding complexity that does not directly help the demo.

## Planned Structure

- `frontend/src/main.tsx`: app bootstrap
- `frontend/src/App.tsx`: top-level screen layout
- `frontend/src/features/invoice-upload/`: upload form and ingestion status
- `frontend/src/features/journal-review/`: journal posting table and approve/decline actions
- `frontend/src/features/accounts/`: chart-of-accounts list and management actions
- `frontend/src/lib/api/`: typed API calls to the backend
- `frontend/src/components/`: small reusable UI pieces

## API Contract For Frontend (Current Backend)

Use the currently implemented endpoints in the backend:

- `POST /invoices`: upload PDF and create invoice record
- `POST /invoices/{invoice_id}/generate`: generate or regenerate suggested journal entry
- `GET /invoices/{invoice_id}`: fetch invoice and related journal entry
- `POST /journal-entries/{journal_entry_id}/approve`: approve pending entry
- `POST /journal-entries/{journal_entry_id}/decline`: decline entry (`{ "reason": "..." }`)
- `GET /accounts`: list chart-of-accounts entries
- `POST /accounts`: create account
- `PATCH /accounts/{account_id}`: update account
- `DELETE /accounts/{account_id}`: deactivate account

Notes:

- Amount fields in API responses are decimal-like JSON values and should be handled as strings in frontend types.

## Local Networking

- Keep frontend network calls in `frontend/src/lib/api/`.
- Prefer relative API paths (for example `/invoices`) and use a Vite proxy for local runs.
- Default proxy target is `http://127.0.0.1:8000`.
- In Docker Compose, set `VITE_PROXY_TARGET=http://backend:8000`.
- Avoid direct database or file-system coupling from the frontend.

## Conventions

- Prefer plain React state and effects before introducing extra state libraries.
- Keep network calls behind a small API helper instead of scattering `fetch` calls everywhere.
- Use TypeScript types for request and response shapes shared within the frontend.
- Keep approval and decline actions explicit and backed by persisted backend state.
- Keep styling simple and easy to tweak under time pressure.
