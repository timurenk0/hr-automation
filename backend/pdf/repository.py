from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from pdf.exceptions import translate_database_error
from pdf.models import PDFDocument, PDFLink


class PDFRepository:
    """PDF persistence using a caller-owned session and transaction."""

    # A session here tracks database operations and
    # the Python model objects involved in them.

    # We supply the session from outside so the repository doesn't create its
    # own connection or control its lifetime. Serveral operations
    # can therefore participate in the same transaction

    # the function-based alternative would pass session into every function (i hate it)
    # it works equally well, but repeats the parameter.

    def __init__(self, session: Session):
        self.session = session

    # session.add tells sqlalchemy to track it for persistence
    # while flush is basically pushing new inserts to db. but the
    # transaction is still uncommited and can be rolled back.

    def create(self, document: PDFDocument) -> PDFDocument:
        """Insert a document and its attached links without committing.

        Flush assigns IDs and database defaults and checks constraints. The
        caller must commit on success or roll back if persistence fails.
        """
        try:
            self.session.add(document)
            self.session.flush()

            return document
        except SQLAlchemyError as error:
            raise translate_database_error(error) from error

    def get_by_id(self, document_id: UUID) -> PDFDocument | None:
        """Fetch a document with its links loaded, or None if it is absent."""
        statement = (
            select(PDFDocument)
            .where(PDFDocument.id == document_id)
            .options(selectinload(PDFDocument.links))
        )

        try:
            return self.session.scalars(statement).one_or_none()
        except SQLAlchemyError as error:
            raise translate_database_error(error) from error

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

        try:
            return list(self.session.scalars(statement))
        except SQLAlchemyError as error:
            raise translate_database_error(error) from error
