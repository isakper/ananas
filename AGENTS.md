# AGENTS.md

<INSTRUCTIONS>
## Project overview
- Purpose: This repo is a template for starting new projects with a docs-first, agent-friendly workflow.
- Operating principle: The repository is the system of record. Prefer updating docs/checks over repeating tribal knowledge in chat.
- Default branch: `main`
- Branch prefix (agent work): Prefer `codex/` for branches created primarily by an agent.

## How to create a PR (high level)
1. Always create a new worktree, then a branch:
   - Branch naming: `codex/<short-kebab-case>` (agent) or `feature|fix|chore/<short-kebab-case>`
   - Example: `git worktree add ../wt-signup-flow -b codex/signup-flow`
2. Add or update tests when feasible for the change you are making.
3. Write code (standards + invariants): see [docs/CODE_STANDARDS.md](docs/CODE_STANDARDS.md)
4. Update any relevant documents under `docs/` when behavior, workflows, or plans change.
5. Before committing, run local checks:
   - Format/lint/typecheck/tests/build: see [docs/CHECKS.md](docs/CHECKS.md)
   - Build + run + manual checks: see [docs/CHECKS.md](docs/CHECKS.md)
6. Make a commit.
7. Self-review, then open a PR.
8. After merge, remove the worktree: `git worktree remove ../wt-signup-flow`

## Docs directory map
- `ARCHITECTURE.md`: High-level system shape, boundaries, and invariants; link out to deeper docs.
- `docs/product-spec.md`: Product requirements and acceptance criteria for the current build.
- `docs/FRONTEND.md`: Frontend conventions (structure, state, performance, testing).
- `docs/PLANS.md`: How to write and track execution plans.
- `docs/CODE_STANDARDS.md`: Code standards, layering, error-handling, and “taste” rules.
- `docs/CHECKS.md`: How to build/run the code and the local validation/manual checks before PR.
- `docs/exec-plans/tech-debt-tracker.md`: Lightweight list of tech-debt items and cleanup candidates.
- `docs/exec-plans/active/`: Active execution plans (one file per initiative).
- `docs/exec-plans/completed/`: Completed execution plans (move here on done).
- `docs/generated/db-schema.md`: Generated artifacts; keep human-written notes elsewhere.
- `docs/references/`: Long-lived reference notes aimed at agents (deployment/tooling/design system).

## House rules (defaults)
- Ask when requirements are ambiguous; prefer clarifying in docs once.
- Add tests for new behavior when feasible; avoid untested “drive-by” changes.
- Do not add dependencies without explicit approval in the PR description.
- Keep diffs small and scoped; avoid reformatting unrelated code.
</INSTRUCTIONS>
