# Execution Plan: Invoice History, Reopen, and PDF Serving

Updated: 2026-04-09

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
1. Define listing and file-access API contract:
   - Add `GET /invoices` list endpoint with core metadata and status fields.
   - Add secure local `GET /invoices/{id}/file` streaming endpoint for PDF preview.
   - Document response contracts and error behavior.
2. Implement backend endpoints and repository methods:
   - Add invoice listing query sorted by newest first.
   - Add file-response guardrails (invoice existence, path safety, file existence handling).
   - Ensure invoice status fields (`uploaded/generating/ready/failed`) are returned consistently.
3. Add backend tests:
   - Invoice list shape and sorting.
   - File endpoint for valid invoice, missing invoice, and missing file edge cases.
   - Bundle reload regression checks via `GET /invoices/{id}`.
4. Implement frontend history UX:
   - Add invoice history panel/table with status pills and timestamps.
   - Allow selecting invoice to load full bundle into review panel.
   - Switch PDF viewer from blob-only URL to backend file URL for persisted viewing.
5. Surface status/error state clearly:
   - Show generation status and error details in the selected invoice context.
   - Preserve selected invoice after account-tab navigation when possible.

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
- Ship backend list/file APIs and tests first.
- Ship frontend history selection and PDF rendering next.
- Keep old blob-preview path as temporary fallback only during transition.
- Remove fallback once backend file serving is stable.

## Risks
- Unsafe file-path handling can introduce security issues.
- Large PDFs can degrade UI performance if rendering strategy is naive.
- State synchronization bugs may show stale invoice/journal bundles after switching.
