from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import (
    DBAPIError, DisconnectionError, IntegrityError, InterfaceError, OperationalError,
    SQLAlchemyError, TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.orm import Session

from pdf.exceptions import PDFDatabaseUnavailableError, PDFPersistenceError


class DriverError(Exception):
    def __init__(self, sqlstate):
        self.sqlstate = sqlstate
        super().__init__("private-credential")


def db_error(kind, sqlstate=None, invalidated=False):
    return kind(
        "SELECT private-document-text",
        {"secret": "private-credential"},
        DriverError(sqlstate),
        connection_invalidated=invalidated,
    )


@pytest.mark.parametrize("error_factory, expected", [
    (lambda: db_error(OperationalError), PDFDatabaseUnavailableError),
    (lambda: db_error(InterfaceError), PDFDatabaseUnavailableError),
    (lambda: db_error(OperationalError, "08006"), PDFDatabaseUnavailableError),
    (lambda: db_error(OperationalError, "57P01"), PDFDatabaseUnavailableError),
    (lambda: db_error(OperationalError, "53300"), PDFDatabaseUnavailableError),
    (lambda: db_error(DBAPIError, invalidated=True), PDFDatabaseUnavailableError),
    (lambda: DisconnectionError("private-credential"), PDFDatabaseUnavailableError),
    (lambda: SQLAlchemyTimeoutError("private-credential"), PDFDatabaseUnavailableError),
    (lambda: db_error(OperationalError, "40001"), PDFPersistenceError),
    (lambda: db_error(IntegrityError, "23505"), PDFPersistenceError),
    (lambda: db_error(IntegrityError, invalidated=True), PDFPersistenceError),
    (lambda: SQLAlchemyError("private-document-text"), PDFPersistenceError),
])
@pytest.mark.parametrize(
    "operation",
    ["create", "get_by_id", "get_links_by_document_id"],
)
def test_repository_translates_operations_and_preserves_causes(
    monkeypatch,
    error_factory,
    expected,
    operation,
):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    from pdf.models import PDFDocument
    from pdf.repository import PDFRepository

    session = Mock(spec=Session)
    original = error_factory()
    if operation == "create":
        session.flush.side_effect = original
        argument = PDFDocument(filename="cv.pdf", content="", links=[])
    else:
        session.scalars.side_effect = original
        argument = uuid4()

    with pytest.raises(expected) as caught:
        getattr(PDFRepository(session), operation)(argument)

    assert caught.value.__cause__ is original
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
