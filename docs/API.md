# API Contract

Last reviewed: 2026-04-09

## Base

- Local base URL: `http://127.0.0.1:8000`

## Health

- `GET /health`

Response:

```json
{
  "status": "ok"
}
```

## Accounts

- `GET /accounts`
- `POST /accounts`
- `PATCH /accounts/{account_id}`
- `DELETE /accounts/{account_id}`

Response:

```json
[
  {
    "id": "uuid",
    "code": 6530,
    "name": "IT-tjanster",
    "is_active": true,
    "created_at": "2026-04-09T12:00:00Z",
    "updated_at": "2026-04-09T12:00:00Z"
  }
]
```

Create payload:

```json
{
  "code": 6541,
  "name": "Nytt konto"
}
```

Update payload (partial):

```json
{
  "name": "Nytt kontonamn",
  "is_active": true
}
```

Safeguards:

- `code` must be unique.
- `code` must be positive.
- `name` is required on create.
- Deactivation is blocked when an account is used in approved journal entries (`409`).

## Invoices

- `GET /invoices`

Behavior:

- Returns invoice history ordered by newest first.
- Includes generation status fields for UI polling/list rendering.

- `POST /invoices` (multipart form-data with `file`)

Behavior:

- Stores the PDF.
- Creates invoice row with `generation_status = uploaded`.
- Does not generate journal entry yet.

Response:

```json
{
  "invoice": {
    "id": "uuid",
    "original_filename": "invoice.pdf",
    "mime_type": "application/pdf",
    "file_path": "backend/data/uploads/....pdf",
    "extracted_text": null,
    "generation_status": "uploaded",
    "generation_error": null,
    "generated_at": null,
    "created_at": "2026-04-09T12:00:00Z",
    "updated_at": "2026-04-09T12:00:00Z"
  },
  "journal_entry": null
}
```

- `GET /invoices/{invoice_id}`

Response:

- Returns invoice and current suggestion (or `journal_entry = null` before generation).

- `GET /invoices/{invoice_id}/pdf`

Behavior:

- Returns the original uploaded PDF file.
- Useful for rendering inside the review screen.

- `POST /invoices/{invoice_id}/generate`

Behavior:

- Sets invoice status to `generating`.
- Runs extraction + LLM posting suggestion.
- On success: status `ready`, saves markdown + suggested journal entry.
- On failure: status `failed` with `generation_error`.

Response:

- Same shape as `GET /invoices/{invoice_id}` with updated invoice and journal entry.

## Journal Decisions

- `POST /journal-entries/{journal_entry_id}/approve`
- `POST /journal-entries/{journal_entry_id}/decline`

Decline payload:

```json
{
  "reason": "optional reason"
}
```

## Status Values

Invoice generation status:

- `uploaded`
- `generating`
- `ready`
- `failed`

Journal entry status:

- `pending`
- `approved`
- `declined`
