from io import BytesIO
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from pdf.exceptions import PDFEmptyUploadError, PDFInvalidFilenameError, translate_database_error
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
            raise PDFInvalidFilenameError()
        if not pdf_bytes:
            raise PDFEmptyUploadError()

        # Complete extraction before starting any database writes.
        parsed = PDFParser(BytesIO(pdf_bytes)).parse()
        document = PDFDocument(
            filename=filename,
            content=normalize_text(parsed.content),
            links=[PDFLink(platform=link.platform, url=link.url) for link in parsed.links],
        )
        try:
            saved = self.repository.create(document)
            # Copy generated values after flush, before commit expires ORM data.

            # model_validate validates an ordinary python object or dict against
            # a pydantic model and retuns a new, validated model instance 

            # response returns pydantic object containing document information
            # we could've make our own validation, but why if we have pydantic validation
            response = PDFDocumentRead.model_validate(saved) 
            try:
                self.repository.session.commit()
            except SQLAlchemyError as error:
                raise translate_database_error(error) from error
        except Exception:
            self.repository.session.rollback()
            raise
        return response

    def get_document(self, document_id: UUID) -> PDFDocumentRead | None:
        document = self.repository.get_by_id(document_id)
        if document is None:
            return None
        return PDFDocumentRead.model_validate(document)
