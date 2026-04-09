"""Invoice API routes."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from backend.app.api.deps import (
    get_journal_generation_workflow,
    get_repository,
    get_settings,
)
from backend.app.api.schemas import InvoiceBundleResponse, InvoiceResponse
from backend.app.core.repository import AppRepository
from backend.app.core.settings import Settings
from backend.app.workflows.journal_generation import (
    InvoiceNotFoundError,
    JournalGenerationWorkflow,
)

router = APIRouter(tags=["invoices"])


@router.post(
    "/invoices",
    response_model=InvoiceBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice(
    file: UploadFile = File(...),
    repository: AppRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> InvoiceBundleResponse:
    """Upload an invoice PDF without generating a suggestion yet."""
    _validate_upload(file)
    payload = await file.read()
    if len(payload) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(payload) > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is too large")

    upload_path = _persist_file(payload, file.filename or "invoice.pdf", settings)
    invoice = repository.create_invoice(
        original_filename=file.filename or "invoice.pdf",
        mime_type=file.content_type or "application/pdf",
        file_path=str(upload_path),
    )
    bundle = repository.get_invoice_bundle(invoice.id)
    if bundle is None:
        raise HTTPException(status_code=500, detail="Failed to load created invoice")
    return InvoiceBundleResponse.from_record(bundle)


@router.get("/invoices/{invoice_id}", response_model=InvoiceBundleResponse)
def get_invoice(
    invoice_id: UUID, repository: AppRepository = Depends(get_repository)
) -> InvoiceBundleResponse:
    """Fetch invoice and associated journal suggestion."""
    bundle = repository.get_invoice_bundle(invoice_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceBundleResponse.from_record(bundle)


@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices(
    repository: AppRepository = Depends(get_repository),
) -> list[InvoiceResponse]:
    """List uploaded invoices for history and navigation."""
    records = repository.list_invoices()
    return [InvoiceResponse.from_record(record) for record in records]


@router.get("/invoices/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: UUID,
    repository: AppRepository = Depends(get_repository),
) -> FileResponse:
    """Serve the original uploaded invoice PDF."""
    invoice = repository.get_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    file_path = Path(invoice.file_path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Invoice PDF not found")
    return FileResponse(
        path=file_path,
        media_type=invoice.mime_type,
        filename=invoice.original_filename,
    )


@router.post(
    "/invoices/{invoice_id}/generate",
    response_model=InvoiceBundleResponse,
)
def generate_invoice_journal_entry(
    invoice_id: UUID,
    workflow: JournalGenerationWorkflow = Depends(get_journal_generation_workflow),
) -> InvoiceBundleResponse:
    """Generate or regenerate a suggested journal entry for an invoice."""
    try:
        bundle = workflow.run(invoice_id=invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return InvoiceBundleResponse.from_record(bundle)


def _validate_upload(file: UploadFile) -> None:
    content_type = file.content_type or ""
    file_name = file.filename or ""
    is_pdf = content_type == "application/pdf" or file_name.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")


def _persist_file(content: bytes, file_name: str, settings: Settings) -> Path:
    safe_name = f"{uuid4()}-{Path(file_name).name}"
    upload_dir = settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_path = upload_dir / safe_name
    output_path.write_bytes(content)
    return output_path
