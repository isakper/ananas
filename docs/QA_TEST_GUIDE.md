# QA Test Guide: Invoice to Journal Entry

Last reviewed: 2026-04-10

## Purpose

This guide is for onboarding junior QA testers. It describes exactly what to test in the current app, with concrete steps and expected results.

## Current Product Scope

User can:

- Navigate from `Home` to:
- `Invoice Management`
- `Company Setup`
- Upload multiple PDF invoices in one action.
- See pending and processed invoice lists.
- Open any invoice into `Invoice Review`.
- Generate suggestion for a selected invoice.
- Edit posting lines on pending journal entries (account, description, debit, credit).
- Save or reset line edits.
- Approve or decline pending entries.
- Manage chart of accounts (create, edit, remove/deactivate).
- View uploaded PDF via backend-served `GET /invoices/{id}/pdf`.

Important business rules visible in UI:

- Approval blocked if journal is unbalanced.
- Approval blocked if posting references missing/inactive account.
- Approval blocked if invoice is flagged as possible duplicate.
- Approval blocked until unsaved line edits are saved or reset.

## Test Setup

1. Start DB: `scripts/db-up`
2. Run migrations: `scripts/db-migrate`
3. Start backend: `poetry run uvicorn backend.app.main:app --reload`
4. Start frontend: `npm --prefix frontend run dev`
5. Open app URL from Vite terminal output.

Test files:

- Valid PDF: `/Users/perssonisak/Projects/private/ananas/docs/interview_guide/simple_invoice.pdf`
- Another valid PDF (copy with different filename): `cp docs/interview_guide/simple_invoice.pdf /tmp/simple_invoice_copy.pdf`
- Invalid file: any `.txt`
- Empty PDF: `touch /tmp/empty.pdf`
- Large PDF: any `.pdf` > 10 MB (or > `MAX_UPLOAD_BYTES`)

## Manual Test Cases

## TC-001 Home Navigation

Goal: verify top-level navigation.

Steps:

1. Open app.
2. Confirm `Home` shows two cards: `Invoice Management`, `Company Setup`.
3. Open `Invoice Management`.
4. Click `Home` button in top bar.
5. Open `Company Setup`.

Expected:

- No crashes.
- Navigation between these screens works.

## TC-002 Upload Multiple PDFs

Goal: verify multi-file upload and list population.

Steps:

1. Go to `Invoice Management`.
2. In `Invoice Upload`, choose two valid PDFs.
3. Click `Upload selected`.

Expected:

- Button shows `Uploading...` during request.
- Uploaded invoices appear in `Pending Review` list.
- Each row has filename, status pill, updated timestamp, flag column, and `Open` button.

## TC-003 Partial Upload Failure

Goal: verify mixed success/failure behavior.

Steps:

1. Select one valid PDF and one `.txt` file.
2. Click `Upload selected`.

Expected:

- Valid file is uploaded and appears in list.
- Error banner explains partial failure and includes failed filename.
- App remains usable.

## TC-004 Open Invoice Review And PDF Rendering

Goal: verify invoice open flow and backend PDF serving.

Steps:

1. In `Pending Review`, click `Open` for an invoice.
2. Confirm screen switches to `Invoice Review`.
3. Verify PDF renders in `Invoice Viewer`.
4. Use `Invoices` button to return to list.

Expected:

- Selected invoice opens correctly.
- Viewer shows PDF (served from backend endpoint).

## TC-005 Generate Suggestion

Goal: verify suggestion creation from review screen.

Precondition:

- Open an invoice that has no journal entry yet.

Steps:

1. Click `Generate suggestion`.

Expected:

- Button shows `Generating...` during request.
- Journal status shows `Pending review`.
- Posting table appears.
- Totals display in `SEK`.

## TC-006 Edit Posting Lines And Save

Goal: verify manual journal editing workflow.

Precondition:

- Invoice has pending journal entry.

Steps:

1. Change one posting description.
2. Change one posting account via dropdown.
3. Click `Save line edits`.

Expected:

- `Save line edits` becomes enabled only when there are unsaved changes.
- During save: button shows `Saving...`.
- Save succeeds and edited values persist in table.
- Unsaved-change warning disappears after save.

## TC-007 Reset Unsaved Edits

Goal: verify reset behavior.

Precondition:

- Pending entry with unsaved modifications.

Steps:

1. Modify at least one field.
2. Click `Reset edits`.

Expected:

- Draft values revert to last saved server state.
- Unsaved-change warning disappears.

## TC-008 Validation While Editing

Goal: verify edit validation messaging and save blocking.

Precondition:

- Pending entry.

Steps:

1. Set both debit and credit to positive on one line.
2. Observe warning.
3. Set both debit and credit to `0` on one line.
4. Observe warning.
5. Make totals unbalanced.

Expected:

- Warning panel `Cannot save edits` appears with specific line/total errors.
- `Save line edits` is disabled while violations exist.

## TC-009 Approval Blocked With Unsaved Changes

Goal: verify approval gate for unsaved drafts.

Precondition:

- Pending entry.

Steps:

1. Modify any posting field.
2. Without saving/resetting, try to approve.

Expected:

- Warning says to save edits before approving.
- `Approve` button remains disabled.

## TC-010 Approve Happy Path

Goal: verify approval and list transition.

Precondition:

- Pending entry, no edit violations, no unsaved changes, not duplicate-flagged.

Steps:

1. Click `Approve`.

Expected:

- Button shows `Approving...`.
- Entry status becomes approved.
- App navigates back to `Invoice Management`.
- Invoice appears in `Processed Invoices`.

## TC-011 Decline Happy Path

Goal: verify decline path.

Precondition:

- Pending entry.

Steps:

1. Enter optional decline reason.
2. Click `Decline`.

Expected:

- Button shows `Declining...`.
- Entry status becomes declined.
- App navigates back to `Invoice Management`.
- Invoice appears in `Processed Invoices`.

## TC-012 Duplicate Detection And Approval Block

Goal: verify duplicate flag logic.

Steps:

1. Upload `simple_invoice.pdf`.
2. Upload exact same file content again (same file or copied filename with same bytes).
3. Open the second invoice and generate suggestion if needed.

Expected:

- Second invoice row shows `Possible duplicate of <short-id>` in flag column.
- In review screen, warning panel shows duplicate warning.
- Approve is blocked for duplicate-flagged invoice.

## TC-013 Regenerate After Decision

Goal: verify regeneration resets decision status.

Precondition:

- Invoice previously approved or declined.

Steps:

1. Open processed invoice.
2. Click `Generate suggestion`.

Expected:

- Journal entry resets to pending.
- Decision reason/decision timestamp are cleared.
- Invoice returns to pending-review behavior.

## TC-014 Company Setup: Create Account

Goal: verify account creation.

Steps:

1. Open `Company Setup`.
2. Enter valid code/name.
3. Click `Add account`.

Expected:

- New account appears in table sorted by code.
- No error banner.

## TC-015 Company Setup: Client-Side Validation

Goal: verify local form validation.

Steps:

1. Try create with code `abc` or `0`.
2. Try create with empty name.

Expected:

- Local error shown:
- `Account code must be a positive number.`
- `Account name is required.`
- Request is not sent.

## TC-016 Company Setup: Edit Account

Goal: verify account edit workflow.

Steps:

1. Click `Edit` on an account.
2. Change code and/or name.
3. Click `Save`.

Expected:

- Updated values appear in table.
- `Cancel` exits edit mode without persisting.

## TC-017 Company Setup: Remove Account (Soft Delete)

Goal: verify removal/deactivation behavior.

Steps:

1. Click `Remove` on an account not used in approved entries.

Expected:

- Account is removed from current frontend list.
- No error shown.

## TC-018 Account Safeguard For Approved Entries

Goal: verify server safeguard against deactivating in-use approved account.

Precondition:

- At least one approved journal uses target account.

Steps:

1. In `Company Setup`, click `Remove` for that account.

Expected:

- Error banner shows conflict message similar to:
- `Account is used by an approved journal entry`
- Account remains available.

## TC-019 Upload Validation Errors

Goal: verify upload rejection rules.

Steps:

1. Upload `.txt` file.
2. Upload empty `.pdf`.
3. Upload too-large `.pdf`.

Expected:

- Error messages:
- `Only PDF uploads are supported`
- `Uploaded file is empty`
- `Uploaded file is too large`

## TC-020 Generate Failure Handling

Goal: verify generation failure UX.

Precondition:

- Configure backend so generate can fail (for example invalid upstream LLM setup).

Steps:

1. Upload valid invoice.
2. Click `Generate suggestion`.

Expected:

- Error banner appears with backend detail.
- App remains interactive and user can retry.

## TC-021 Refresh And Persistence

Goal: verify server persistence across browser refresh.

Steps:

1. Upload and generate invoice.
2. Refresh browser tab.
3. Return to `Invoice Management`.

Expected:

- Invoice still appears in list (fetched via `GET /invoices`).
- Opening invoice still loads current journal state via `GET /invoices/{id}`.

## Optional API Sanity Cases (Postman/cURL)

1. `GET /health` returns `{"status":"ok"}`.
2. `GET /invoices` returns list ordered by newest first.
3. `GET /invoices/{id}/pdf` returns inline PDF.
4. `PATCH /journal-entries/{id}` with non-pending entry returns `400`.
5. `POST /accounts` duplicate `code` returns `409`.
6. `PATCH /accounts/{id}` with no fields returns `400`.
7. `DELETE /accounts/{unknown-id}` returns `404`.

## Recommended Execution Order

1. TC-001 to TC-005
2. TC-006 to TC-013
3. TC-014 to TC-018
4. TC-019 to TC-021
