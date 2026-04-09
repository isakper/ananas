# Standard Template With Agents

Starter repo for a Python backend and React frontend with a docs-first workflow.

## Chosen Stack

- Backend: Python 3.11 + FastAPI
- Frontend: React + TypeScript
- Frontend tooling: Node.js + Vite
- Database: PostgreSQL
- Integration style: simple JSON API between frontend and backend

This setup keeps PDF extraction straightforward on the backend, supports reliable persistence, and keeps the UI conventional on the frontend.

## Required Product Features

- Upload an invoice PDF from the frontend.
- Generate a suggested journal entry with an LLM using the provided chart of accounts.
- Persist the generated journal entry in PostgreSQL.
- Show the bill and suggested journal entry in the UI.
- Let the accountant approve or decline the suggested journal entry.
- Ensure debits and credits are balanced before approval.

## Quick start

### 1) Create and activate a virtual environment

Use whichever tool you prefer. Two common options:

Poetry-managed env:
```bash
poetry env use 3.11
poetry install
```

Python venv:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install poetry
poetry install
```

### 2) Install pre-commit hooks

```bash
poetry run pre-commit install
```

Optional: run all hooks once:
```bash
poetry run pre-commit run --all-files
```

### 3) Run tests

```bash
poetry run pytest
```

## Project Layout

- `backend/`: FastAPI app, extraction logic, and persistence
- `frontend/`: React + TypeScript app
- `docs/`: architecture, checks, and planning docs
- `tests/`: backend-focused automated tests

## Key Docs

- `AGENTS.md`: working agreements for agents
- `ARCHITECTURE.md`: folder structure and responsibilities
- `docs/product-spec.md`: required product behavior and acceptance criteria
- `docs/FRONTEND.md`: frontend stack and conventions
- `docs/CHECKS.md`: target local commands and manual verification
- `docs/CODE_STANDARDS.md`: coding rules and change hygiene

## Common tasks

Format:
```bash
poetry run black .
```

Sort imports:
```bash
poetry run isort .
```

Typecheck:
```bash
poetry run mypy .
```
