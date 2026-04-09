# Standard Template With Agents

Starter repo for a Python backend and React frontend with a docs-first workflow.

## Chosen Stack

- Backend: Python 3.11 + FastAPI
- Frontend: React + TypeScript + Vite
- Database: PostgreSQL
- Integration style: simple JSON API between frontend and backend

## Quick Start (Recommended)

### 1) Prerequisites

- Docker + Docker Compose

### 2) Configure environment

```bash
cp .env.example .env
```

Set `ANTHROPIC_API_KEY` in `.env` (required).

### 3) Start everything

```bash
scripts/dev-up
```

Open:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`

## Day-to-day commands

Stop stack:
```bash
scripts/dev-down
```

Reset stack + fresh DB volume:
```bash
scripts/dev-reset
```

Quick health smoke check:
```bash
scripts/dev-smoke
```

## Alternative local run (without full Docker stack)

You can still run services directly:

```bash
scripts/db-up
scripts/db-migrate
poetry install
npm --prefix frontend install
poetry run uvicorn backend.app.main:app --reload
npm --prefix frontend run dev
```

## Project Layout

- `backend/`: FastAPI app, extraction logic, and persistence
- `frontend/`: React + TypeScript app
- `docs/`: architecture, checks, plans, and specs
- `tests/`: backend-focused automated tests
- `scripts/`: local developer entrypoints

## Key Docs

- `AGENTS.md`: working agreements for agents
- `ARCHITECTURE.md`: folder structure and responsibilities
- `docs/product-spec.md`: required product behavior and acceptance criteria
- `docs/FRONTEND.md`: frontend stack and conventions
- `docs/CHECKS.md`: validation/manual checks before PR
- `docs/CODE_STANDARDS.md`: coding rules and change hygiene
