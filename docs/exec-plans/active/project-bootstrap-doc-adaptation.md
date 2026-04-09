# Execution Plan: Project Bootstrap Doc Adaptation

Updated: 2026-03-29

## Objective
Make the template docs project-specific before feature work starts.

Success criteria:
- Placeholder sections are replaced with real project decisions.
- `README.md` and core docs describe the actual stack and workflow.
- New contributors can follow docs without guessing.

## Non-goals
- Building product features.
- Large refactors outside docs.

## Milestones
1. Update project basics in docs:
   - Fill stack, runtime, repo layout, package manager, database, and deployment decisions in `README.md` and `ARCHITECTURE.md`.
2. Update working docs with real commands and expectations:
   - Fill `docs/CHECKS.md` with actual commands.
   - Update `docs/TESTING.md`, `docs/SECURITY.md`, and `docs/RELIABILITY.md` with project-specific guidance.
3. Update optional docs as needed:
   - If frontend exists, update `docs/FRONTEND.md` and `docs/DESIGN.md`.
   - If no frontend yet, add a short note saying it is not applicable yet.
4. Validate docs:
   - Run doc checks and fix any broken links/placeholders.

## Validation
- `python3 scripts/doc_lint.py` passes.
- `scripts/lint-plan` passes.
- A teammate can follow `README.md` + `docs/CHECKS.md` to run the project locally.

## Rollout
- Land this plan first.
- Update docs in one small PR (or a few small PRs if preferred).
- Move this plan to `docs/exec-plans/completed/` when docs are project-specific and checks pass.

## Risks
- Placeholder text remains in important docs and causes confusion.
- Commands in docs drift from actual commands if not validated.
