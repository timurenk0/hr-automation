from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from core.exception_handlers import error_responses
from pdf.dependencies import get_pdf_service
from pdf.exceptions import (
    PDFDatabaseUnavailableError, PDFEmptyUploadError, PDFEncryptedError,
    PDFInvalidError, PDFInvalidFilenameError, PDFNotFoundError,
    PDFPersistenceError, PDFUnsupportedMediaTypeError, PDFUploadTooLargeError,
)
from pdf.schemas import PDFDocumentRead
from pdf.service import PDFService


router = APIRouter(tags=["PDF"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream", "binary/octet-stream"}


@router.post(
    "/upload-pdf", response_model=PDFDocumentRead, status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        PDFInvalidFilenameError, PDFEmptyUploadError, PDFUnsupportedMediaTypeError,
        PDFUploadTooLargeError, PDFInvalidError, PDFEncryptedError,
        PDFDatabaseUnavailableError, PDFPersistenceError,
    ),
)
def upload_pdf(
    pdf: Annotated[UploadFile, File()],
    service: Annotated[PDFService, Depends(get_pdf_service)],
) -> PDFDocumentRead:
    try:
        if not pdf.filename or not pdf.filename.strip():
            raise PDFInvalidFilenameError()
        media_type = (pdf.content_type or "").split(";", 1)[0].strip().lower()
        if media_type and media_type not in PDF_CONTENT_TYPES:
            raise PDFUnsupportedMediaTypeError()
        pdf_bytes = pdf.file.read(MAX_UPLOAD_BYTES + 1)
        if len(pdf_bytes) > MAX_UPLOAD_BYTES:
            raise PDFUploadTooLargeError()
        if not pdf_bytes:
            raise PDFEmptyUploadError()
        return PDFDocumentRead.model_validate(service.create_document(pdf.filename, pdf_bytes))
    finally:
        pdf.file.close()


@router.get(
    "/pdf/{document_id}", response_model=PDFDocumentRead,
    responses=error_responses(PDFNotFoundError, PDFDatabaseUnavailableError, PDFPersistenceError),
)
def get_pdf(
    document_id: UUID,
    service: Annotated[PDFService, Depends(get_pdf_service)],
) -> PDFDocumentRead:
    document = service.get_document(document_id)
    if document is None:
        raise PDFNotFoundError()
    return PDFDocumentRead.model_validate(document)
