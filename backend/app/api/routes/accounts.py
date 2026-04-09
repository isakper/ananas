"""Account API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.deps import get_repository
from backend.app.api.schemas import AccountResponse
from backend.app.core.repository import AppRepository

router = APIRouter(tags=["accounts"])


@router.get("/accounts", response_model=list[AccountResponse])
def list_accounts(repository: AppRepository = Depends(get_repository)) -> list[AccountResponse]:
    """List chart-of-accounts entries."""
    records = repository.list_accounts()
    return [AccountResponse.from_record(record) for record in records]
