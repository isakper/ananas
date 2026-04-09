"""Journal entry decision routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.deps import get_repository
from backend.app.api.schemas import (
    DeclineRequest,
    JournalEntryResponse,
    JournalEntryUpdateRequest,
)
from backend.app.core.repository import AppRepository, PostingUpdate

router = APIRouter(tags=["journal-entries"])


@router.post(
    "/journal-entries/{journal_entry_id}/approve", response_model=JournalEntryResponse
)
def approve_journal_entry(
    journal_entry_id: UUID, repository: AppRepository = Depends(get_repository)
) -> JournalEntryResponse:
    """Approve a suggested journal entry if validation passes."""
    try:
        record = repository.decide_journal_entry(
            journal_entry_id=journal_entry_id,
            status="approved",
            reason=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if record is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return JournalEntryResponse.from_record(record)


@router.post(
    "/journal-entries/{journal_entry_id}/decline", response_model=JournalEntryResponse
)
def decline_journal_entry(
    journal_entry_id: UUID,
    payload: DeclineRequest,
    repository: AppRepository = Depends(get_repository),
) -> JournalEntryResponse:
    """Decline a suggested journal entry."""
    try:
        record = repository.decide_journal_entry(
            journal_entry_id=journal_entry_id,
            status="declined",
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if record is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return JournalEntryResponse.from_record(record)


@router.patch(
    "/journal-entries/{journal_entry_id}", response_model=JournalEntryResponse
)
def update_journal_entry(
    journal_entry_id: UUID,
    payload: JournalEntryUpdateRequest,
    repository: AppRepository = Depends(get_repository),
) -> JournalEntryResponse:
    """Replace posting lines for a pending journal entry."""
    updates = [
        PostingUpdate(
            account_id=posting.account_id,
            description=(
                posting.description.strip()
                if posting.description is not None and posting.description.strip() != ""
                else None
            ),
            debit_amount=posting.debit_amount,
            credit_amount=posting.credit_amount,
        )
        for posting in payload.postings
    ]
    try:
        record = repository.update_pending_journal_entry(journal_entry_id, updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if record is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return JournalEntryResponse.from_record(record)
