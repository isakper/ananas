# Architecture

Last reviewed: 2026-04-09


This document is the system-of-record for how the codebase is structured.

## Chosen Stack

- Backend: Python 3.11 + FastAPI
- Frontend: React + TypeScript
- Frontend tooling: Node.js + Vite
- Persistence: PostgreSQL for journal entries, invoice metadata, and approval state
- Integration boundary: REST-style JSON API between frontend and backend

## Planned Repo Layout

- `backend/`: FastAPI application, extraction logic, persistence, and service wiring
- `frontend/`: React application, API client, upload flow, and result rendering
- `docs/`: project decisions, checks, and execution plans
- `tests/`: backend-focused automated tests

## Concrete Folder Map

```text
backend/
  app/
    main.py
    api/
    core/
    documents/
    accounting/
frontend/
  src/
    main.tsx
    App.tsx
    features/
    components/
    lib/
tests/
docs/
scripts/
```

### Top-Level Folders

- `backend/`: Python application code and local backend-only assets.
- `frontend/`: React/TypeScript application code and frontend build config.
- `tests/`: automated backend tests. Frontend tests can be added later if they become worth the cost.
- `docs/`: architecture, workflow, and planning docs.
- `scripts/`: lightweight repo-local automation and lint helpers.

### Backend Folders

- `backend/app/main.py`: FastAPI entrypoint and top-level app wiring.
- `backend/app/api/`: HTTP routes, request parsing, response shaping, and dependency injection.
- `backend/app/core/`: cross-cutting backend setup such as config loading, logging, and database/session wiring.
- `backend/app/documents/`: upload, PDF extraction, and normalized invoice data.
- `backend/app/accounting/`: journal entry generation, balancing validation, and approval state transitions.

### Backend Domain Layout

`backend/app/documents/` should follow this shape:

- `backend/app/documents/types/`: document models, extraction result shapes, and pure helpers.
- `backend/app/documents/config/`: domain-specific settings and defaults.
- `backend/app/documents/repo/`: persistence boundaries and document retrieval.
- `backend/app/documents/service/`: extraction orchestration, validation, and business rules.
- `backend/app/documents/runtime/`: concrete wiring of repo and provider implementations.
- `backend/app/documents/providers/`: interfaces for external processing dependencies such as LLM-backed extraction.

`backend/app/accounting/` should follow the same layered shape and contain:

- account-mapping logic against the provided chart of accounts
- journal entry creation and debit/credit balancing checks
- approve/decline state transitions

### Frontend Folders

- `frontend/src/main.tsx`: React bootstrap.
- `frontend/src/App.tsx`: top-level screen composition.
- `frontend/src/features/invoice-upload/`: upload flow and ingestion state.
- `frontend/src/features/journal-review/`: posting review and approve/decline actions.
- `frontend/src/components/`: small reusable presentational components.
- `frontend/src/lib/api/`: typed API client code for backend calls.
- `frontend/src/lib/types/`: shared frontend-only TypeScript types if they do not belong to a single feature.

### Data And Persistence

- Default local persistence is PostgreSQL.
- Use a configurable `DATABASE_URL`, with local development pointing to a local Postgres instance.
- Keep schema and persistence logic in backend repo/runtime layers rather than scattering SQL in route handlers.
- Do not commit database dumps or uploaded invoice artifacts.

## Implementation Bias

- Prefer a simple split between frontend and backend over a full-stack framework.
- Keep the happy path synchronous unless the task clearly requires background jobs.
- Keep a single Postgres database with simple tables rather than adding extra infrastructure.
- Keep routes thin and move extraction logic into the `documents/service` layer quickly.

## Domain Layering Model

Within a business domain, code should mostly depend “forward” through this sequence:

`Types → Config → Repo → Service → Runtime → UI`

- Types: data shapes + pure helpers. No IO.
- Config: domain configuration derived from env/flags/defaults. No DB/network.
- Repo: data access boundary (DB/remote). Returns Types.
- Service: use-cases and business rules. Orchestrates Repo + Providers.
- Runtime: wiring/composition (construct implementations, inject Providers).
- UI: presentation layer (calls Service or API; no direct Repo).

### Examples

- Service imports Types/Config/Repo/Providers interfaces.
- Repo imports Types/Config (not Service/UI).
- UI imports Service (or API client) and Types.
- Runtime imports Service/Repo/Providers implementations and wires them together.
- UI importing Repo directly.
- Repo importing Service.
- Service importing UI.

## Current Architecture Rules

- Keep API routes thin.
- Keep extraction behavior in the `documents` domain.
- Keep journal creation, balancing, and approval behavior in the `accounting` domain.
- Keep database access out of route handlers.
- Keep frontend networking inside `frontend/src/lib/api/` or feature-local wrappers.
- Add more folders only when the code volume justifies them.

## Required Feature Scope

- Upload invoice PDF.
- Generate suggested journal entry with LLM account mapping.
- Persist suggested entry and approval status in Postgres.
- Render both invoice context and postings in the UI.
- Support explicit approve and decline actions.
- Prevent approval if total debits and credits are not balanced.

## Architecture Lint
There is a stub linter entrypoint at `scripts/lint-architecture`. We can tighten lint rules later when the real folder structure exists.

## Runtime Environments
- Local dev is the primary target.
- Backend runs as a FastAPI app with local environment variables.
- Frontend runs through the Vite dev server and calls the local backend API.

## Observability
- Start with structured backend logs and clear browser/network errors.
- Avoid adding dedicated observability infrastructure unless the exercise explicitly needs it.
