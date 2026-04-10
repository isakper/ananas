# Execution Plan: Manual Journal Edit Before Decision

Updated: 2026-04-10

## Objective
Allow accountants to edit LLM-suggested postings before approving or declining, so near-correct suggestions can be fixed instead of always rejected.

Success criteria:
- Accountant can edit posting rows (account, description, debit/credit), add lines, and remove lines while status is `pending`.
- Backend validates and persists edits, recalculates totals, and enforces balanced-entry rules.
- Approval uses the latest edited postings and remains blocked for invalid entries.
- UI clearly distinguishes AI-suggested state from manually edited state.

## Non-goals
- Full accounting engine coverage (VAT automation, accrual scheduling, period locking).
- Collaborative multi-user editing.
- Undo/redo history beyond simple in-session reset.

## Milestones
1. Completed (scope adjusted): define edit model and API contract.
   - Implemented as `PATCH /journal-entries/{id}` with full postings payload.
   - Concurrency control (optimistic lock/version check) is not yet implemented.
2. Completed: implement backend edit flow.
   - Pending-only edit enforcement, account validation, amount validation, and balance checks are in place.
3. In progress: add backend tests.
   - Validation regression tests exist.
   - Happy-path persistence and non-pending edit route tests are still missing.
4. Completed: implement frontend editable journal table.
   - Pending entries support inline edits, save, and reset.
   - Validation feedback and save/approve gating are implemented.
5. In progress: clarify audit/traceability UX.
   - Unsaved-change warnings exist.
   - Explicit “Edited” markers and editor rationale notes are still missing.

## Remaining Work
- Add route/integration tests for successful patch save and non-pending edit rejection.
- Decide and implement simple concurrency protection for conflicting edits.
- Add explicit edited-state indicator and optional edit note metadata.

## Validation
- `python3 scripts/doc_lint.py`
- `scripts/lint-plan`
- `poetry run pytest` (or equivalent local test runner)
- `npm --prefix frontend run build`
- Manual checks:
- Edit one posting and save.
- Add/remove posting and verify totals update.
- Try saving unbalanced edits and verify clear blocking errors.
- Approve edited posting set and verify persisted status.

## Rollout
- Land missing backend/API tests first.
- Add audit-traceability UI/API enhancements in a follow-up diff.
- Keep approve/decline endpoints unchanged but validated against updated postings.

## Risks
- Without explicit edited-state cues, users may not trust what is being approved.
- Concurrent edits from multiple tabs can overwrite each other.
- Validation mismatch between frontend and backend can create confusing save failures.
