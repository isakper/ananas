# Execution Plan: Invoice History, Reopen, and PDF Serving

Updated: 2026-04-10

## Objective
Enable accountants to revisit prior invoices and continue review work by adding invoice history, persistent invoice loading, and backend-served PDF rendering.

Success criteria:
- Accountant can view a list of previously uploaded invoices with generation and decision status.
- Accountant can select any invoice and load its invoice+journal bundle in the review UI.
- Invoice PDF preview works after page reload and for historical invoices.
- Generation errors and statuses are visible per invoice and persist across sessions.

## Non-goals
- Full-text invoice search or complex filtering.
- Pagination optimization for very large datasets.
- Document storage migration to cloud object storage.

## Milestones
1. Completed: define listing and file-access API contract.
   - `GET /invoices` and file serving are implemented.
   - File endpoint is implemented as `GET /invoices/{invoice_id}/pdf`.
2. In progress: implement backend endpoints and repository methods.
   - Invoice listing and PDF serving are implemented.
   - Additional path-safety hardening and edge-case handling should be tightened.
3. Not started: add backend tests.
   - No dedicated route-level tests cover invoice list/PDF paths yet.
4. Completed: implement frontend history UX.
   - Invoice management screen lists pending/processed invoices.
   - Users can reopen invoices and render persisted PDFs in review.
5. In progress: surface status/error state clearly.
   - Basic load/reopen flow works.
   - Generation status/error details are not yet surfaced per invoice in a clear persistent way.

## Remaining Work
- Add backend tests for list ordering and PDF endpoint edge cases.
- Expose and render `generation_status` and `generation_error` prominently per invoice.
- Add stronger file-path safety checks for stored invoice paths.

## Validation
- `python3 scripts/doc_lint.py`
- `scripts/lint-plan`
- `poetry run pytest` (or equivalent local test runner)
- `npm --prefix frontend run build`
- Manual checks:
- Upload invoice, generate suggestion, refresh page, reopen invoice, and view PDF.
- Upload multiple invoices and switch between them.
- Trigger generation failure and confirm persistent error visibility.

## Rollout
- Land backend tests and path-safety hardening first.
- Land per-invoice generation status/error UI improvements next.
- Keep endpoint naming stable (`/pdf`) unless there is a deliberate API-versioning decision.

## Risks
- Insufficient file-path guardrails can create security risk.
- Missing per-invoice status visibility can make failures hard to recover from.
- State synchronization bugs may show stale invoice/journal bundles after switching.
