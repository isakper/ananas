"""Account API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.deps import get_repository
from backend.app.api.schemas import (
    AccountBulkSaveRequest,
    AccountCreateRequest,
    AccountSnapshotItemRequest,
    AccountResponse,
    AccountUpdateRequest,
)
from backend.app.core.repository import (
    AccountConflictError,
    AccountInUseError,
    AccountSnapshotItem,
    AppRepository,
)

router = APIRouter(tags=["accounts"])


@router.get("/accounts", response_model=list[AccountResponse])
def list_accounts(
    repository: AppRepository = Depends(get_repository),
) -> list[AccountResponse]:
    """List chart-of-accounts entries."""
    records = repository.list_accounts()
    return [AccountResponse.from_record(record) for record in records]


@router.post("/accounts", response_model=AccountResponse, status_code=201)
def create_account(
    payload: AccountCreateRequest,
    repository: AppRepository = Depends(get_repository),
) -> AccountResponse:
    """Create a chart-of-accounts entry."""
    name = _normalized_name(payload.name)
    if payload.code <= 0:
        raise HTTPException(status_code=400, detail="Account code must be positive")
    if name is None:
        raise HTTPException(status_code=400, detail="Account name is required")

    try:
        record = repository.create_account(code=payload.code, name=name)
    except AccountConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AccountResponse.from_record(record)


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: str,
    payload: AccountUpdateRequest,
    repository: AppRepository = Depends(get_repository),
) -> AccountResponse:
    """Update account attributes and activation status."""
    code = payload.code
    if code is not None and code <= 0:
        raise HTTPException(status_code=400, detail="Account code must be positive")
    normalized_name = _normalized_name(payload.name)
    if payload.name is not None and normalized_name is None:
        raise HTTPException(status_code=400, detail="Account name is required")
    if code is None and normalized_name is None and payload.is_active is None:
        raise HTTPException(status_code=400, detail="No account fields to update")

    account_uuid = _parse_uuid(account_id)
    try:
        record = repository.update_account(
            account_id=account_uuid,
            code=code,
            name=normalized_name,
            is_active=payload.is_active,
        )
    except AccountInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AccountConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if record is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountResponse.from_record(record)


@router.delete("/accounts/{account_id}", response_model=AccountResponse)
def deactivate_account(
    account_id: str,
    repository: AppRepository = Depends(get_repository),
) -> AccountResponse:
    """Deactivate an account (soft delete)."""
    account_uuid = _parse_uuid(account_id)
    try:
        record = repository.deactivate_account(account_uuid)
    except AccountInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountResponse.from_record(record)


@router.put("/accounts/bulk", response_model=list[AccountResponse])
def save_accounts_bulk(
    payload: AccountBulkSaveRequest,
    repository: AppRepository = Depends(get_repository),
) -> list[AccountResponse]:
    """Atomically replace the active chart of accounts with a provided snapshot."""
    items = _validated_snapshot_items(payload.accounts)
    try:
        records = repository.save_accounts_snapshot(items)
    except AccountInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AccountConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [AccountResponse.from_record(record) for record in records]


def _normalized_name(value: str | None) -> str | None:
    if value is None:
        return None
    name = value.strip()
    if name == "":
        return None
    return name


def _parse_uuid(value: str):
    from uuid import UUID

    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid account id") from exc


def _validated_snapshot_items(
    items: list[AccountSnapshotItemRequest],
) -> list[AccountSnapshotItem]:
    if len(items) == 0:
        raise HTTPException(status_code=400, detail="At least one account is required")

    validated: list[AccountSnapshotItem] = []
    for item in items:
        if item.code <= 0:
            raise HTTPException(status_code=400, detail="Account code must be positive")
        name = _normalized_name(item.name)
        if name is None:
            raise HTTPException(status_code=400, detail="Account name is required")
        validated.append(AccountSnapshotItem(code=item.code, name=name))
    return validated
