# Architecture

Last reviewed: 2026-04-09


This document is the system-of-record for how the codebase is structured.

## Chosen Stack

- Backend: Python 3.11 + FastAPI
- Frontend: React + TypeScript
- Frontend tooling: Node.js + Vite
- Persistence: SQLite when the task needs saved uploads or extracted results
- Integration boundary: REST-style JSON API between frontend and backend

## Planned Repo Layout

- `backend/`: FastAPI application, extraction logic, persistence, and service wiring
- `frontend/`: React application, API client, upload flow, and result rendering
- `docs/`: project decisions, checks, and execution plans
- `tests/`: backend-focused automated tests

## Implementation Bias

- Prefer a simple split between frontend and backend over a full-stack framework.
- Keep the happy path synchronous unless the task clearly requires background jobs.
- Start with SQLite or in-memory storage before introducing heavier infrastructure.

## Goals
- Keep the architecture legible to both humans and agents.
- Encode invariants as checks (tests, linters, CI) when possible.
- Preserve flexibility across downstream repos by using a config-driven structure linter.

## Architecture Linting
This repo ships with a structural linter that enforces layer and domain boundaries.

- Config: `architecture-lint.toml`
- Entrypoint: `scripts/lint-architecture`
- Hook: runs via pre-commit (local) and can be wired to CI.

## How To Use
- Start here for a 5-minute overview.
- Put long-form details in `docs/` and link from here.

## Domain Layering Model

### Terminology
- Business domain: a user-facing area of the product (e.g. “App Settings”, “Billing”, “Onboarding”).
- Layer: a conceptual slice within a domain with clear responsibility and dependency rules.
- Providers: the explicit boundary for cross-cutting concerns (auth, connectors, telemetry, feature flags, etc.).

### The rule (v1)
Within a business domain, code may only depend “forward” through this fixed sequence:

`Types → Config → Repo → Service → Runtime → UI`

Cross-cutting concerns enter through a single explicit interface:

`Providers → Service → Runtime → UI`

Everything else is disallowed.

### Layer responsibilities (quick)
- Types: data shapes + pure helpers. No IO.
- Config: domain configuration derived from env/flags/defaults. No DB/network.
- Repo: data access boundary (DB/remote). Returns Types.
- Service: use-cases and business rules. Orchestrates Repo + Providers.
- Runtime: wiring/composition (construct implementations, inject Providers).
- UI: presentation layer (calls Service or API; no direct Repo).

### Allowed edges (examples)
- Service imports Types/Config/Repo/Providers interfaces.
- Repo imports Types/Config (not Service/UI).
- UI imports Service (or API client) and Types.
- Runtime imports Service/Repo/Providers implementations and wires them together.

### Disallowed edges (examples)
- UI importing Repo directly.
- Repo importing Service.
- Service importing UI.
- Domain code importing cross-cutting singletons directly (must go through Providers).

## Providers (Cross-Cutting Boundary)
Providers are the *only* permitted entry point for cross-cutting concerns inside domain code.

- Providers are interfaces only (types + contracts), not concrete implementations.
- Implementations live in Runtime (or infra packages) and are injected into Services.
- Domain code must never reach for global singletons, environment globals, or system clients directly.

## Taste Invariants (v1)
These are deliberately small. If the list grows, move it to a dedicated doc under `docs/` and link here.

- Layering rule enforced (no backward edges across `Types → Config → Repo → Service → Runtime → UI`).
- Providers are the only cross-cutting boundary; no hidden globals in domain code.
- Boundary data is parsed/validated at entry points (API, job, queue, CLI, webhook).
- Structured logging is used (fields + correlation), with a baseline format documented.

## Adding A New Domain (Checklist)
This repo keeps the layering model, and the working layout is:

- `backend/app/<domain>/types/`
- `backend/app/<domain>/config/`
- `backend/app/<domain>/repo/`
- `backend/app/<domain>/service/`
- `backend/app/<domain>/runtime/`
- `frontend/src/features/<domain>/`

Checklist:
1. Create the domain folder and layer directories.
2. Define Types first (avoid IO dependencies).
3. Add Config and Repo boundaries next.
4. Implement Services that orchestrate Repo + Providers.
5. Wire implementations in Runtime and expose UI usage points.
6. Add Providers interfaces for cross-cutting needs.
7. Update the architecture lint config to map your layout (see below).

## Architecture Lint
This repo ships with a stub architecture linter entrypoint:

- `scripts/lint-architecture`

By default it *does not* enforce rules until configured. This repo should either:
- Replace the script with a stack-specific linter, or
- Add a config file and an adapter that enforces edges per the contract.

See `docs/references/architecture-lint.md` for the contract, config file location, and remediation guidance.

## Runtime Environments
- Local dev is the primary target.
- Backend runs as a FastAPI app with local environment variables.
- Frontend runs through the Vite dev server and calls the local backend API.

## Observability
- Start with structured backend logs and clear browser/network errors.
- Avoid adding dedicated observability infrastructure unless the exercise explicitly needs it.
