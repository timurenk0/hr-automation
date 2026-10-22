from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.database import get_db
from pdf.repository import PDFRepository
from pdf.service import PDFService


def get_pdf_repository(session: Annotated[Session, Depends(get_db)]) -> PDFRepository:
    return PDFRepository(session)


def get_pdf_service(
    repository: Annotated[PDFRepository, Depends(get_pdf_repository)],
) -> PDFService:
    return PDFService(repository)
