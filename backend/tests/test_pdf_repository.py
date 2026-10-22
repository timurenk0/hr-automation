from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pdf.exceptions import PDFPersistenceError


@pytest.fixture
def session(monkeypatch):
    # Model imports initialize the application engine; no Postgres connection
    # is opened. Repository operations below use only the isolated test engine.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    from core.database import Base
    from pdf.models import PDFDocument, PDFLink

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine, autoflush=False) as session:
            yield session
    finally:
        engine.dispose()


def test_create_flushes_document_and_links_but_allows_rollback(session):
    from pdf.models import PDFDocument, PDFLink
    from pdf.repository import PDFRepository

    repository = PDFRepository(session)
    document = PDFDocument(
        filename="cv.pdf", content="Developer",
        links=[PDFLink(platform="github", url="https://github.com/example")],
    )

    saved = repository.create(document)
    document_id = saved.id
    assert saved.created_at is not None
    assert saved.links[0].id is not None
    assert saved.links[0].document_id == document_id

    session.rollback()
    assert repository.get_by_id(document_id) is None
    assert repository.get_links_by_document_id(document_id) == []


def test_read_loads_nested_links_for_serialization_after_session_closes(session):
    from pdf.models import PDFDocument, PDFLink
    from pdf.repository import PDFRepository
    from pdf.schemas import PDFDocumentRead

    repository = PDFRepository(session)
    document = repository.create(PDFDocument(
        filename="cv.pdf", content="Developer",
        links=[PDFLink(platform="github", url="https://github.com/example")],
    ))
    document_id = document.id
    session.commit()
    session.expunge_all()

    fetched = repository.get_by_id(document_id)
    session.close()

    response = PDFDocumentRead.model_validate(fetched)
    assert response.id == document_id
    assert response.links[0].url == "https://github.com/example"


def test_link_queries_are_scoped_to_the_document(session):
    from pdf.models import PDFDocument, PDFLink
    from pdf.repository import PDFRepository

    repository = PDFRepository(session)
    first = repository.create(PDFDocument(
        filename="first.pdf", content="",
        links=[PDFLink(platform="github", url="https://github.com/first")],
    ))
    repository.create(PDFDocument(
        filename="second.pdf", content="",
        links=[PDFLink(platform="github", url="https://github.com/second")],
    ))
    empty = repository.create(PDFDocument(filename="empty.pdf", content="", links=[]))

    links = repository.get_links_by_document_id(first.id)
    assert [link.url for link in links] == ["https://github.com/first"]
    assert repository.get_by_id(empty.id).links == []
    assert repository.get_links_by_document_id(empty.id) == []
    assert repository.get_by_id(uuid4()) is None
    assert repository.get_links_by_document_id(uuid4()) == []


def test_duplicate_link_failure_can_be_rolled_back_by_the_caller(session):
    from pdf.models import PDFDocument, PDFLink
    from pdf.repository import PDFRepository

    repository = PDFRepository(session)
    document = PDFDocument(
        filename="cv.pdf", content="",
        links=[
            PDFLink(platform="github", url="https://github.com/example"),
            PDFLink(platform="github", url="https://github.com/example"),
        ],
    )
    with pytest.raises(PDFPersistenceError) as caught:
        repository.create(document)
    assert isinstance(caught.value.__cause__, IntegrityError)
    session.rollback()

    assert repository.get_by_id(document.id) is None
    assert repository.get_links_by_document_id(document.id) == []
