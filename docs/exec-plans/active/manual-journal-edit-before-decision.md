# Execution Plan: Manual Journal Edit Before Decision

Updated: 2026-04-09

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
1. Define edit model and API contract:
   - Add update endpoint for pending entries (recommended `PUT /journal-entries/{id}` with full postings payload).
   - Define immutable fields and editable fields.
   - Define concurrency strategy (simple optimistic lock via `updated_at` check, or last-write-wins for MVP).
2. Implement backend edit flow:
   - Validate account existence/active status.
   - Validate positive numeric amounts and exactly-one-side debit/credit rule.
   - Validate debit/credit balance and update entry totals atomically.
   - Block edits when entry status is not `pending`.
3. Add backend tests:
   - Happy-path edit with total recalculation.
   - Invalid account/amount/unbalanced payload cases.
   - Attempt edit on approved/declined entry.
4. Implement frontend editable journal table:
   - Make rows editable in `pending` state.
   - Add add/remove row controls and inline validation feedback.
   - Add save action with disabled states while saving.
   - Add “reset to last generated suggestion” affordance.
5. Clarify audit/traceability UX:
   - Show “Edited” marker after successful manual save.
   - Persist optional editor note for rationale (if scope allows).
   - Ensure approve/decline messages reflect latest saved version.

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
- Ship backend edit API and validation first.
- Ship frontend editing UX in a second step.
- Keep approve/decline endpoints unchanged but ensure they read updated postings.
- Update API/product docs in same PR as behavior changes.

## Risks
- Without clear edit-state UX, users may not trust what is being approved.
- Concurrency conflicts can overwrite edits if reopening the same entry in multiple tabs.
- Validation mismatch between frontend and backend can create confusing save failures.
