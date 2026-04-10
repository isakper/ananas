# Execution Plan: Chart of Accounts CRUD and Safeguards

Updated: 2026-04-10

## Objective
Implement full chart-of-accounts management so accountants can add, edit, and disable accounts from the UI, with server-side validation and safe behavior for entries that reference those accounts.

Success criteria:
- Accountant can create, edit, and disable accounts from the `Chart of Accounts` screen.
- Validation rules are enforced in backend and surfaced clearly in UI (numeric unique code, required name).
- Approval behavior remains correct when a posting references an inactive account.
- API and docs are updated to match implemented behavior.

## Non-goals
- Importing/exporting account lists from external systems.
- Role-based permissions or multi-tenant account sets.
- Advanced accounting policy checks beyond required validation.

## Milestones
1. Completed: finalize account lifecycle and API contract.
   - `GET/POST/PATCH/DELETE /accounts` is documented in `docs/API.md`.
   - Deactivation is implemented as soft-delete behavior.
2. Completed: implement backend account write endpoints.
   - Create/update/deactivate routes and repository flows are implemented.
   - Duplicate code and invalid payload paths return clear 4xx responses.
3. In progress: add repository + route tests.
   - Some repository validation tests exist.
   - Route-level and end-to-end CRUD test coverage is still missing.
4. Completed: implement frontend account management UX.
   - Add/edit/remove flows are available in `AccountsPanel`.
   - Client-side validation and backend error surfacing are in place.
5. Completed: align review-flow behavior.
   - Approval checks still block when posting accounts are inactive or missing.

## Remaining Work
- Add API-route tests for account create/update/deactivate and conflict handling.
- Add integration tests around account deactivation and approval blocking.
- Align UI wording (`Remove`) with backend semantics (`Deactivate`) to reduce confusion.

## Validation
- `python3 scripts/doc_lint.py`
- `scripts/lint-plan`
- `poetry run pytest` (or equivalent local test runner)
- `npm --prefix frontend run build`
- Manual checks:
- Create account with valid data.
- Attempt duplicate code and verify useful error.
- Edit name/code and confirm persisted update.
- Deactivate account used by suggestion and verify approval-block messaging.

## Rollout
- Land missing backend/API tests first.
- Land any UX wording and behavior polish in a follow-up diff.
- Keep docs updates in the same PR as behavior changes.

## Risks
- Missing route-level tests can hide API regressions.
- Deactivate/remove wording mismatch can mislead users.
- Inactive-account behavior could drift between frontend checks and backend validation.
