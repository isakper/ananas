# Frontend

Last reviewed: 2026-04-09

## Chosen Stack

- React for UI composition
- TypeScript for typed props, API responses, and safer refactors
- Vite for local development and production builds
- Node.js for package management and frontend tooling

## Why This Stack

- It is a safe mainstream option for a small product UI.
- React is common enough that contributors can follow it easily.
- TypeScript gives helpful guardrails without forcing a complex architecture.
- Vite keeps the setup light and fast.

## Scope

The frontend only needs to do a few things well:

- accept a PDF upload
- send the file to the backend
- show extracted content or structured fields
- show loading, success, and error states clearly

Avoid adding complexity that does not directly help the demo.

## Planned Structure

- `frontend/src/main.tsx`: app bootstrap
- `frontend/src/App.tsx`: top-level screen layout
- `frontend/src/features/pdf-upload/`: upload form and result view
- `frontend/src/lib/api/`: typed API calls to the backend
- `frontend/src/components/`: small reusable UI pieces

## Conventions

- Prefer plain React state and effects before introducing extra state libraries.
- Keep network calls behind a small API helper instead of scattering `fetch` calls everywhere.
- Use TypeScript types for request and response shapes shared within the frontend.
- Keep styling simple and easy to tweak under time pressure.
