# Execution Plan: Chart of Accounts CRUD and Safeguards

Updated: 2026-04-09

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
1. Finalize account lifecycle and API contract:
   - Confirm behavior for disable vs delete (default: soft-disable only).
   - Define error semantics for duplicate account code and invalid payloads.
   - Document API shapes in `docs/API.md` and `docs/product-spec.md`.
2. Implement backend account write endpoints:
   - Add `POST /accounts`, `PATCH /accounts/{id}`, and deactivate endpoint (`DELETE` or status patch).
   - Enforce DB-level and service-level validation for uniqueness and required fields.
   - Return clear, stable 4xx messages for validation failures.
3. Add repository + route tests:
   - Test create/edit/disable happy path.
   - Test duplicate code, non-numeric code, empty name, missing account id.
   - Test interaction with approve flow when postings reference inactive accounts.
4. Implement frontend account management UX:
   - Add create form, inline or modal edit, and disable action.
   - Show field-level validation and backend error feedback.
   - Refresh account list and preserve user context after mutations.
5. Align review-flow behavior:
   - Ensure review screen clearly indicates inactive-account blocking.
   - Ensure approve action remains blocked until account issues are resolved.

## Validation
- `python3 scripts/doc_lint.py`
- `scripts/lint-plan`
- `poetry run pytest` (or equivalent local test runner)
- `npm --prefix frontend run build`
- Manual checks:
- Create account with valid data.
- Attempt duplicate code and verify useful error.
- Edit name/code and confirm persisted update.
- Disable account used by suggestion and verify approval-block messaging.

## Rollout
- Land backend API + tests first.
- Land frontend account management in a follow-up diff.
- Update docs in the same PR as each behavior change to avoid drift.
- Keep deactivate behavior feature-flag free for MVP simplicity.

## Risks
- Ambiguity around delete vs disable causes data-integrity issues.
- Inactive-account behavior may be inconsistent between frontend pre-check and backend validation.
- Missing error mapping can make validation failures opaque to users.
