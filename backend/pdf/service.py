from io import BytesIO
from uuid import UUID

from pdf.models import PDFDocument, PDFLink
from pdf.parser import PDFParser
from pdf.repository import PDFRepository
from pdf.schemas import PDFDocumentRead
from utility.text_normalizer import normalize_text


class PDFService:
    """Coordinate extraction and persistence using a request-scoped repository."""

    def __init__(self, repository: PDFRepository):
        self.repository = repository

    def create_document(self, filename: str, pdf_bytes: bytes) -> PDFDocumentRead:
        if not filename.strip():
            raise ValueError("Filename must not be blank")
        if not pdf_bytes:
            raise ValueError("PDF bytes must not be empty")

        # Complete extraction before starting any database writes.
        parsed = PDFParser(BytesIO(pdf_bytes)).parse()
        document = PDFDocument(
            filename=filename,
            content=normalize_text(parsed.content),
            links=[
                PDFLink(platform=link.platform, url=link.url) for link in parsed.links
            ],
        )
        try:
            saved = self.repository.create(document)
            # Copy generated values after flush, before commit expires ORM data.
            response = PDFDocumentRead.model_validate(saved)
            self.repository.session.commit()
        except Exception:
            self.repository.session.rollback()
            raise
        return response

    def get_document(self, document_id: UUID) -> PDFDocumentRead | None:
        document = self.repository.get_by_id(document_id)
        if document is None:
            return None
        return PDFDocumentRead.model_validate(document)
