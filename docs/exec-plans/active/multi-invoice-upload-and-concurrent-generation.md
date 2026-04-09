# Execution Plan: Multi-Invoice Upload and Concurrent Generation

Updated: 2026-04-09

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
1. Decide batch strategy and API shape:
   - MVP default: keep existing single `POST /invoices` and run parallel uploads client-side.
   - Optional phase 2: add bulk upload endpoint if client orchestration proves too noisy.
   - Define frontend concurrency limits (for example, max 3-5 in-flight generation requests).
2. Implement frontend multi-upload UX:
   - Enable multi-file selection in upload input.
   - Add per-file rows with status, retry, and open-in-review actions.
   - Preserve individual errors without collapsing to a single global error.
3. Implement concurrent generation controls:
   - Add “Generate all ready” and per-invoice generate buttons.
   - Queue generation with bounded parallelism.
   - Keep review panel tied to selected invoice while background generation continues.
4. Add backend safety and observability improvements:
   - Ensure status updates are idempotent and stable under repeated generate requests.
   - Improve generation error messages for queue-style UX.
   - Add logs keyed by invoice id to trace concurrent runs.
5. Add tests and docs:
   - Frontend tests for queue state transitions (if test harness exists) or documented manual matrix.
   - Backend tests for repeated generation calls on same invoice.
   - Update `docs/API.md`, `docs/product-spec.md`, and `docs/FRONTEND.md` with multi-upload behavior.

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
- Ship frontend multi-upload list first using existing single-upload API.
- Add bounded concurrency generation in follow-up.
- Only add backend bulk endpoint if user friction remains high after client-side batching.
- Keep feature behind straightforward UX controls (no hidden toggles).

## Risks
- Aggressive parallel requests can overwhelm local backend/LLM limits.
- Poor per-item error handling can make batch failures hard to recover from.
- Race conditions may confuse status if repeated generate requests overlap.
