from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pdf.models import PDFDocument, PDFLink


class PDFRepository:
    """PDF persistence using a caller-owned session and transaction."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, document: PDFDocument) -> PDFDocument:
        """Insert a document and its attached links without committing.

        Flush assigns IDs and database defaults and checks constraints. The
        caller must commit on success or roll back if persistence fails.
        """
        self.session.add(document)
        self.session.flush()
        return document

    def get_by_id(self, document_id: UUID) -> PDFDocument | None:
        """Fetch a document with its links loaded, or None if it is absent."""
        statement = (
            select(PDFDocument)
            .where(PDFDocument.id == document_id)
            .options(selectinload(PDFDocument.links))
        )
        return self.session.scalars(statement).one_or_none()

    def get_links_by_document_id(self, document_id: UUID) -> list[PDFLink]:
        """Fetch scraper inputs without loading the document's text.

        An empty result can mean either no extracted links or no such document.
        Use get_by_id when the caller needs to distinguish those cases.
        """
        statement = (
            select(PDFLink)
            .where(PDFLink.document_id == document_id)
            .order_by(PDFLink.platform, PDFLink.id)
        )
        return list(self.session.scalars(statement))
