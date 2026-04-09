# Standard Template With Agents

Template repo for a docs-first, agent-friendly workflow.

## Chosen Stack

- Backend: Python 3.11 + FastAPI
- Frontend: React + TypeScript
- Frontend tooling: Node.js + Vite
- Database: SQLite when the exercise needs persistence
- Integration style: simple JSON API between frontend and backend

This setup is optimized for interview speed and clarity. Python keeps PDF extraction fast to implement, while React + TypeScript keeps the UI conventional and easy for an agent to scaffold.

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

## Recorded decisions

- Backend framework: FastAPI
- Frontend framework: React
- Frontend language: TypeScript
- Frontend build tool: Vite
- Repo layout: split `backend/` and `frontend/`
- Python package manager: Poetry
- Frontend package manager: npm
- Database: SQLite for local persistence when needed

Where to record these:
- `ARCHITECTURE.md` for repo layout, components, and invariants.
- `docs/FRONTEND.md` for frontend conventions.
- `docs/CHECKS.md` for canonical commands (format/lint/typecheck/test/build/run).

Optional: Playwright MCP for agent UI testing
This is a per-user setting (lives in `~/.codex/config.toml`), so each developer adds it locally:
```bash
codex mcp add playwright npx "@playwright/mcp@latest"
```
Or add to `~/.codex/config.toml`:
```toml
[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest"]
```
Or use the helper script:
```bash
./scripts/setup_mcp_playwright.sh
```

## What else to think about

Docs are the source of truth. Start with `AGENTS.md` and `docs/` before coding.
Checks and local validation are defined in `docs/CHECKS.md`.
Code standards and layering rules are in `docs/CODE_STANDARDS.md`.

## How this repo works for agents

This template is designed so agents can rely on explicit, stable guidance instead of tribal knowledge.

System of record:
`AGENTS.md` and `docs/` define how to work, what standards apply, and where to update decisions.

Pre-commit automation:
Hooks are defined in `.pre-commit-config.yaml` and enforced locally via `pre-commit install`.

Pre-commit hooks currently configured:
- `pre-commit-hooks` for conflict checks, file hygiene, and secret detection
- `black` for formatting
- `isort` for import ordering
- `pydocstyle` for docstring style
- `darglint` for docstring completeness
- `mypy` for static typing
- `repo: local` hooks for architecture/plan linting and pre-push test validation

Custom hooks:
Repo-local hooks are already used (for example `lint-architecture`, `lint-plan`, and `ci-test-local`). When you add more, define them under `repo: local` in `.pre-commit-config.yaml`, point each one at a script in this repo, and document them in this section.

Unit tests:
Pytest is the default backend test runner. Frontend tests can be added later if they buy us confidence without slowing down delivery.

Validation loop:
Expected local checks and manual verification live in `docs/CHECKS.md`.

## Repo map

`ARCHITECTURE.md`: system shape and invariants.
`docs/`: deeper guides and templates.
`docs/exec-plans/`: execution plans.

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

If you want me to tailor this to your specific stack (web, CLI, data, etc.), tell me what you’re building.
