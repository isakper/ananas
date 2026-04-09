# QA Test Guide: Invoice to Journal Entry

Last reviewed: 2026-04-09

## Purpose

This guide is for manual QA of the current MVP. It explains exactly what to test, in what order, and what result should happen.

## Current Product Scope

User can:

- Upload a PDF invoice.
- Generate a journal suggestion.
- Review totals and postings.
- Approve or decline a pending suggestion.
- View and refresh chart of accounts.

Not in scope yet:

- Account create/edit/delete in UI.

## Test Setup

Run these before testing:

1. Start DB: `scripts/db-up`
2. Run migrations: `scripts/db-migrate`
3. Start backend: `poetry run uvicorn backend.app.main:app --reload`
4. Start frontend: `npm --prefix frontend run dev`
5. Open app URL from Vite output.

Test data:

- Valid sample PDF: `/Users/perssonisak/Projects/private/ananas/docs/interview_guide/simple_invoice.pdf`
- Invalid upload file: any `.txt` file
- Empty PDF file: create a 0-byte `.pdf`
- Large PDF file: any PDF over 10 MB (or current `MAX_UPLOAD_BYTES`)

## Test Cases (Manual)

## TC-001 App Loads Correctly

Goal: verify basic startup and navigation.

Preconditions:

- Backend and frontend are running.

Steps:

1. Open the app in browser.
2. Confirm `Review` tab is selected.
3. Click `Chart of Accounts`.
4. Click `Review` again.

Expected results:

- No crash or blank page.
- `Review` shows upload card, invoice viewer empty state, and journal review empty state.
- `Chart of Accounts` shows account table and `Refresh` button.

## TC-002 Upload Valid PDF

Goal: verify upload happy path.

Preconditions:

- On `Review` tab.

Steps:

1. Select `simple_invoice.pdf` in file input.
2. Click `Upload invoice`.

Expected results:

- Button shows `Uploading...` while request is in progress.
- Success banner appears: invoice uploaded.
- `Current invoice: ...` text shows filename.
- PDF renders in `Invoice Viewer`.
- `Generate suggestion` button is enabled.

## TC-003 Generate Suggestion

Goal: verify generation and rendering of suggestion.

Preconditions:

- A valid invoice is already uploaded.

Steps:

1. Click `Generate suggestion`.
2. Wait for response.

Expected results:

- Button shows `Generating...` while running.
- Success banner appears for generated suggestion.
- Journal status pill shows `Pending review`.
- Postings table is visible with at least two lines.
- Debit and Credit totals are shown.
- `Extracted Markdown` panel appears.

## TC-004 Approve Pending Suggestion

Goal: verify approve flow.

Preconditions:

- Journal entry status is `Pending review`.
- No approval violation warning shown.

Steps:

1. Click `Approve`.

Expected results:

- Button shows `Approving...` while request is in progress.
- Success banner appears for approval.
- Status changes to `Approved`.
- Approve and Decline controls become disabled.

## TC-005 Decline Pending Suggestion (No Reason)

Goal: verify decline with empty reason.

Preconditions:

- Journal entry status is `Pending review`.

Steps:

1. Leave decline reason input empty.
2. Click `Decline`.

Expected results:

- Button shows `Declining...` while request is in progress.
- Success banner appears for decline.
- Status changes to `Declined`.
- No decision note is displayed.

## TC-006 Decline Pending Suggestion (With Reason)

Goal: verify decline with reason persisted.

Preconditions:

- Journal entry status is `Pending review`.

Steps:

1. Type `Incorrect account mapping` in decline reason input.
2. Click `Decline`.

Expected results:

- Status changes to `Declined`.
- Decision note appears and contains `Incorrect account mapping`.

## TC-007 Regenerate After Decision

Goal: verify regenerate resets entry to pending state.

Preconditions:

- Invoice is uploaded.
- Entry is already `Approved` or `Declined`.

Steps:

1. Click `Generate suggestion` again.

Expected results:

- Status returns to `Pending review`.
- Previous decision reason is cleared.
- New suggestion is shown in table.

## TC-008 Accounts Screen Loads Seeded Data

Goal: verify accounts listing works.

Preconditions:

- DB migrations executed.

Steps:

1. Open `Chart of Accounts` tab.
2. Verify multiple accounts are listed.
3. Confirm examples like `1930`, `2440`, `6530` exist.
4. Click `Refresh`.

Expected results:

- Table loads with account code, name, and status.
- `Refresh` button shows `Refreshing...` during request, then returns to normal.

## TC-009 Upload Rejects Non-PDF

Goal: verify file type validation.

Preconditions:

- On `Review` tab.

Steps:

1. Select a `.txt` file.
2. Click `Upload invoice`.

Expected results:

- Error banner appears with message equivalent to `Only PDF uploads are supported`.
- App remains usable after error.

## TC-010 Upload Rejects Empty File

Goal: verify empty-file validation.

Preconditions:

- On `Review` tab.

Steps:

1. Select a 0-byte `.pdf`.
2. Click `Upload invoice`.

Expected results:

- Error banner appears with message equivalent to `Uploaded file is empty`.
- No invoice is set as current.

## TC-011 Upload Rejects Too-Large PDF

Goal: verify max upload size validation.

Preconditions:

- On `Review` tab.

Steps:

1. Select PDF larger than configured max (default 10 MB).
2. Click `Upload invoice`.

Expected results:

- Error banner appears with message equivalent to `Uploaded file is too large`.

## TC-012 Generate Failure Shows Error

Goal: verify generation error handling.

Preconditions:

- Invoice uploaded.
- Backend is configured so generate fails (for example broken LLM credentials/network when using Anthropic gateway).

Steps:

1. Click `Generate suggestion`.

Expected results:

- Error banner is shown with backend error detail.
- App does not freeze.
- User can retry generation.

## Edge Case Checks

1. Confirm `Generate suggestion` is disabled before any upload.
2. Confirm repeated rapid clicks on action buttons do not send uncontrolled duplicate requests (buttons disable during loading).
3. Confirm browser refresh clears local PDF preview, but backend data still exists when re-fetched by id.
4. Confirm app fails clearly when `ANTHROPIC_API_KEY` is missing.
5. Confirm approval is blocked if warning panel says totals/accounts are invalid.

## Optional API Sanity Cases (Postman/cURL)

1. `GET /health` returns `{"status":"ok"}`.
2. `GET /invoices/{random-uuid}` returns `404`.
3. `POST /invoices/{random-uuid}/generate` returns `404`.
4. `POST /journal-entries/{random-uuid}/approve` returns `404`.
5. `POST /journal-entries/{random-uuid}/decline` returns `404`.

## Recommended Execution Order For New QA

1. TC-001
2. TC-002
3. TC-003
4. TC-004
5. TC-006
6. TC-007
7. TC-008
8. TC-009
9. TC-010
10. TC-011
11. TC-012
