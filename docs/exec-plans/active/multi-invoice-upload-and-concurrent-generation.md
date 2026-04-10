# Execution Plan: Multi-Invoice Upload and Concurrent Generation

Updated: 2026-04-10

## Objective
Enable accountants to upload multiple invoices in one action and process them concurrently with clear per-invoice progress, errors, and decision readiness.

Success criteria:
- User can select and upload multiple PDF invoices in a single interaction.
- Each invoice shows independent upload and generation status (`uploaded`, `generating`, `ready`, `failed`).
- User can start generation for many invoices and monitor progress without losing context.
- Failures in one invoice do not block other invoices from completing.

## Non-goals
- Distributed job queue infrastructure.
- Batch accounting approval in one click.
- Throughput tuning for production-scale workloads.

## Milestones
1. In progress: decide batch strategy and API shape.
   - Multi-file client upload path is in place.
   - Explicit concurrency policy and limits are not yet implemented.
2. In progress: implement frontend multi-upload UX.
   - Multi-file selection and upload are implemented.
   - Per-file retry controls and clearer per-item progress states are still missing.
3. Not started: implement concurrent generation controls.
   - No `Generate all ready` flow or bounded generation queue yet.
4. Not started: add backend safety and observability improvements.
   - No dedicated idempotency/overlap safeguards or invoice-keyed generation logs yet.
5. In progress: add tests and docs.
   - Core docs and UI have moved toward multi-invoice management.
   - Test coverage and explicit multi-upload behavior docs are incomplete.

## Remaining Work
- Add per-invoice generation controls (`Generate all`, retry failed, queue visibility).
- Implement bounded parallel generation strategy in frontend.
- Add backend safeguards for overlapping generate requests on same invoice.
- Add dedicated test coverage for multi-upload and concurrent generation behavior.

## Validation
- `python3 scripts/doc_lint.py`
- `scripts/lint-plan`
- `poetry run pytest` (or equivalent local test runner)
- `npm --prefix frontend run build`
- Manual checks:
- Upload 3-5 PDFs at once and verify each item transitions correctly.
- Generate concurrently and verify one failure does not block others.
- Retry failed invoice and confirm recovery.
- Approve one ready invoice while others still generate.

## Rollout
- Finish upload-side UX polish first (status + retry clarity).
- Add bounded concurrency generation in a focused follow-up.
- Only add backend bulk endpoint if client-side orchestration remains too noisy.

## Risks
- Parallel requests can overwhelm local backend/LLM limits.
- Weak per-item error handling makes batch failures hard to recover from.
- Race conditions can confuse status when repeated generate requests overlap.
