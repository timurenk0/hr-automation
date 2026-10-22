from collections.abc import Iterator
from contextlib import contextmanager
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.exceptions import ResponseValidationError
from pydantic import ValidationError
from pypdf.errors import PdfReadError
from sqlalchemy.exc import (
    DBAPIError, DisconnectionError, InterfaceError, OperationalError,
    TimeoutError as SQLAlchemyTimeoutError,
)

from pdf.dependencies import get_pdf_service
from pdf.schemas import PDFDocumentRead
from pdf.service import PDFService


router = APIRouter(tags=["PDF"])
logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream", "binary/octet-stream"}


def _internal_failure(error: Exception) -> HTTPException:
    # Exception messages/tracebacks can contain document data, SQL parameters,
    # or database credentials. Log only the exception class.
    logger.error("PDF operation failed: %s", type(error).__name__)
    unavailable = isinstance(error, (DisconnectionError, SQLAlchemyTimeoutError))
    if isinstance(error, DBAPIError):
        sqlstate = getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)
        unavailable = error.connection_invalidated or (
            isinstance(error, (OperationalError, InterfaceError))
            and (sqlstate is None or sqlstate.startswith("08") or sqlstate in {
                "57P01", "57P02", "57P03", "53300",
            })
        )
    if unavailable:
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Database unavailable")
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")


@contextmanager
def _service_errors() -> Iterator[None]:
    try:
        yield
    except HTTPException:
        raise
    except (ValidationError, ResponseValidationError) as error:
        # Pydantic ValidationError inherits ValueError; it must be caught first.
        raise _internal_failure(error) from None
    except (ValueError, PdfReadError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid PDF input") from None
    except Exception as error:
        raise _internal_failure(error) from None


@router.post("/upload-pdf", response_model=PDFDocumentRead, status_code=status.HTTP_201_CREATED)
def upload_pdf(
    pdf: Annotated[UploadFile, File()],
    service: Annotated[PDFService, Depends(get_pdf_service)],
) -> PDFDocumentRead:
    try:
        with _service_errors():
            if not pdf.filename or not pdf.filename.strip():
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Filename must not be blank")
            media_type = (pdf.content_type or "").split(";", 1)[0].strip().lower()
            if media_type and media_type not in PDF_CONTENT_TYPES:
                raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Expected a PDF upload")
            pdf_bytes = pdf.file.read(MAX_UPLOAD_BYTES + 1)
            if len(pdf_bytes) > MAX_UPLOAD_BYTES:
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "PDF exceeds the 10 MiB limit")
            if not pdf_bytes:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "PDF must not be empty")
            return PDFDocumentRead.model_validate(service.create_document(pdf.filename, pdf_bytes))
    finally:
        pdf.file.close()


@router.get("/pdf/{document_id}", response_model=PDFDocumentRead)
def get_pdf(
    document_id: UUID,
    service: Annotated[PDFService, Depends(get_pdf_service)],
) -> PDFDocumentRead:
    with _service_errors():
        document = service.get_document(document_id)
        response = PDFDocumentRead.model_validate(document) if document is not None else None
    if response is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF document not found")
    return response
