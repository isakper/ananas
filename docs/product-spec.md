# Product Spec: Invoice to Journal Entry

Updated: 2026-04-09

## Objective

Build a web app where an accountant can upload an invoice PDF, review an LLM-suggested journal entry, and approve or decline it.

## Users

- Primary user: accountant

## Core Screens

- `Review` screen
- `Chart of Accounts` screen

## Review Screen

### Layout

- Left panel: rendered invoice PDF viewer.
- Right panel: suggested journal entry with postings.

### Required Actions

- Upload PDF invoice.
- Generate suggested journal entry.
- Approve suggested journal entry.
- Decline suggested journal entry.

### Required States

- `pending`: suggestion exists but not decided.
- `approved`: accountant accepted entry.
- `declined`: accountant rejected entry.

### Required Validation

- Total debit must equal total credit before approval.
- Every posting account must exist in the active chart of accounts.
- Amounts must be numeric and positive.

### Required UX Behavior

- Show loading state during extraction/generation.
- Show clear error message if parsing or LLM call fails.
- Prevent approval when validation fails.
- Persist status changes immediately.

## Chart of Accounts Screen

### Required Actions

- List all chart-of-accounts entries.
- Add account.
- Edit account.
- Disable or remove account.

### Required Validation

- Account number must be unique.
- Account number must be numeric.
- Account name is required.

## Backend Requirements

- Accept PDF upload.
- Extract invoice text/content from PDF.
- Call LLM to map invoice content into journal postings.
- Persist invoice, journal entry, postings, and approval status in PostgreSQL.
- Expose endpoints for approve/decline.
- Enforce debit/credit balance validation server-side.

## Suggested API Surface

- `POST /invoices`: upload invoice and create suggestion.
- `GET /invoices/:id`: fetch invoice and suggested journal entry.
- `POST /journal-entries/:id/approve`: approve entry.
- `POST /journal-entries/:id/decline`: decline entry.
- `GET /accounts`: list chart of accounts.
- `POST /accounts`: create account.
- `PATCH /accounts/:id`: update account.
- `DELETE /accounts/:id`: remove or disable account.

## Data Model (MVP)

- `invoices`
- `journal_entries`
- `journal_postings`
- `accounts`

## Acceptance Criteria

- Accountant can upload a PDF and see it rendered in the UI.
- System generates a suggested journal entry using the LLM.
- Suggested entry is stored in PostgreSQL.
- Accountant can approve or decline in the UI.
- Approval is blocked if debits and credits are unbalanced.
- Accountant can manage chart of accounts from a dedicated screen.
