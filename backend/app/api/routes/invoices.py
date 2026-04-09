"""Invoice API routes."""
from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.app.api.deps import get_repository, get_settings
from backend.app.api.schemas import InvoiceBundleResponse
from backend.app.core.repository import AppRepository
from backend.app.core.settings import Settings

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
    """Upload an invoice PDF and create a pending suggestion."""
    _validate_upload(file)
    payload = await file.read()
    if len(payload) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(payload) > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is too large")

    upload_path = _persist_file(payload, file.filename or "invoice.pdf", settings)
    extracted_text = (
        f"Stub parsed content for {file.filename}" if file.filename is not None else None
    )
    bundle = repository.create_invoice_with_stub_entry(
        original_filename=file.filename or "invoice.pdf",
        mime_type=file.content_type or "application/pdf",
        file_path=str(upload_path),
        extracted_text=extracted_text,
    )
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
