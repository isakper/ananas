# Execution Plan: Invoice Journal Entry Take-Home

Updated: 2026-04-09

## Objective
Flesh out the implementation design for the take-home so coding can proceed without ambiguity.

Success criteria:
- Parsing strategy, Postgres schema, and LLM integration shape are explicitly defined.
- API contracts and UI state transitions are written down for all required flows.
- Validation and edge-case behavior are documented for approval/decline and balancing rules.
- A contributor can start implementation directly from the documented decisions.

## Non-goals
- Implementing the full application in this plan.
- Optimizing for production-grade scalability in this phase.
- Finalizing every accounting edge case before MVP behavior is clear.

## Milestones
1. Flesh out document parsing:
   - Define upload constraints and accepted PDF characteristics.
   - Define normalized parsed-invoice payload (fields, types, required/optional).
   - Define error behavior for extraction failures and malformed PDFs.
2. Flesh out PostgreSQL schema:
   - Define table structure for invoices, journal entries, postings, and accounts.
   - Define status/state model (`pending`, `approved`, `declined`) and lifecycle fields.
   - Define key constraints and relations needed for correctness.
3. Flesh out LLM call architecture:
   - Define provider/client boundary for Anthropic calls.
   - Define prompt input format and strict expected output schema.
   - Define retry, timeout, and fallback behavior for unstable responses.
4. Flesh out accounting validation rules:
   - Define debit/credit balancing logic and failure handling.
   - Define account validation against chart of accounts.
   - Define what blocks approval and what can still be saved as `pending`.
5. Flesh out API contracts:
   - Define request/response payloads for upload, suggestion read, approve/decline, and account CRUD.
   - Define error codes/messages for all critical failure paths.
6. Flesh out frontend behavior:
   - Define Review screen states (idle/loading/suggested/error/approved/declined).
   - Define chart-of-accounts management interactions and validation UX.
   - Define optimistic vs server-confirmed state updates for approve/decline.

## Validation
- `python3 scripts/doc_lint.py` passes.
- `scripts/lint-plan` passes.
- Core decision docs (`README.md`, `ARCHITECTURE.md`, `docs/product-spec.md`) reflect the same behavior.
- Team can answer these without ambiguity:
- How invoices are parsed
- How data is modeled in Postgres
- Where LLM calls live and how output is validated
- How approve/decline and balancing rules work

## Rollout
- Land the design decisions first in docs.
- Start implementation only after milestone outputs are clear.
- Keep implementation PRs mapped back to these milestone decisions.
- Move this file to `docs/exec-plans/completed/` when design decisions are stable and implementation has started.

## Risks
- Design remains too vague and causes rework during coding.
- LLM output assumptions are underspecified and break downstream validation.
- Schema decisions are delayed and block API/frontend parallel work.
- Approval-state behavior is ambiguous and causes inconsistent UX/backend logic.
