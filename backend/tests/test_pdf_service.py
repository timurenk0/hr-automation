from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@pytest.fixture
def context(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    from core.database import Base
    from pdf.repository import PDFRepository
    from pdf.service import PDFService

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine, autoflush=False) as session:
            repository = PDFRepository(session)
            yield PDFService(repository), repository, session
    finally:
        engine.dispose()


def assert_no_records(session):
    from pdf.models import PDFDocument, PDFLink

    for model in (PDFDocument, PDFLink):
        assert session.scalar(select(func.count()).select_from(model)) == 0


def test_create_normalizes_and_commits_document_and_all_links(context, make_pdf):
    from pdf.models import PDFDocument, PDFLink

    service, _, session = context
    urls = (
        "https://GitHub.COM/Alice", "https://github.com/alice",
        "https://github.com/alice", "https://Portfolio.Example/Contact",
    )
    response = service.create_document("cv.pdf", make_pdf(
        texts=("  Python   developer  ", "  Projects  "), urls=urls,
    ))
    assert not session.in_transaction()
    assert response.content == "Python developer\n\nProjects"
    assert response.filename == "cv.pdf"
    assert response.created_at is not None
    assert [(link.platform, link.url) for link in response.links] == [
        ("github.com", urls[0]), ("github.com", urls[1]), ("portfolio.example", urls[3]),
    ]
    assert len({link.id for link in response.links}) == 3
    with Session(session.get_bind()) as other:
        assert other.get(PDFDocument, response.id).content == response.content
        assert {link.id for link in other.scalars(select(PDFLink))} == {
            link.id for link in response.links
        }
    session.close()
    assert response.model_dump(mode="json")["links"][0]["id"]


def test_unicode_normalization_and_category_is_unused(context, monkeypatch):
    from pdf.parser import ExtractData, ExtractedLink

    service, _, _ = context
    parsed = ExtractData(
        content="  Cafe\u0301\u00a0 developer\r\n Python\u200b  ",
        links=[ExtractedLink("https://example.com/Case", "example.com", "portfolio")],
    )
    parser = Mock()
    parser.parse.return_value = parsed
    monkeypatch.setattr("pdf.service.PDFParser", Mock(return_value=parser))
    response = service.create_document("cv.pdf", b"stubbed parser input")
    assert response.content == "Caf\u00e9 developer\nPython"
    assert set(response.links[0].model_dump()) == {"id", "platform", "url"}


def test_empty_content_and_links_are_allowed(context, make_pdf):
    service, _, _ = context
    response = service.create_document("blank.pdf", make_pdf(texts=("",)))
    assert response.content == ""
    assert response.links == []


@pytest.mark.parametrize("filename, data", [("", b"pdf"), (" \t", b"pdf"), ("cv.pdf", b"")])
def test_empty_input_never_reaches_parser_or_repository(context, monkeypatch, filename, data):
    service, repository, session = context
    parser, create = Mock(), Mock()
    monkeypatch.setattr("pdf.service.PDFParser", parser)
    monkeypatch.setattr(repository, "create", create)
    with pytest.raises(ValueError):
        service.create_document(filename, data)
    parser.assert_not_called()
    create.assert_not_called()
    assert_no_records(session)


@pytest.mark.parametrize("encrypted", [False, True])
def test_invalid_pdf_produces_no_writes(context, make_pdf, monkeypatch, encrypted):
    service, repository, session = context
    create = Mock()
    monkeypatch.setattr(repository, "create", create)
    data = make_pdf(encrypted=True) if encrypted else b"not a PDF"
    with pytest.raises(ValueError):
        service.create_document("cv.pdf", data)
    create.assert_not_called()
    assert_no_records(session)


@pytest.mark.parametrize("failure_point", ["write", "commit", "response"])
def test_failures_after_flush_are_rolled_back(context, make_pdf, monkeypatch, failure_point):
    service, repository, session = context
    failure = RuntimeError("injected failure")
    if failure_point == "write":
        create = repository.create

        def fail_after_flush(document):
            create(document)
            raise failure

        monkeypatch.setattr(repository, "create", fail_after_flush)
    elif failure_point == "commit":
        monkeypatch.setattr(session, "commit", Mock(side_effect=failure))
    else:
        monkeypatch.setattr("pdf.service.PDFDocumentRead.model_validate", Mock(side_effect=failure))
    with pytest.raises(RuntimeError) as caught:
        service.create_document("cv.pdf", make_pdf(urls=("https://github.com/example",)))
    assert caught.value is failure
    assert not session.in_transaction()
    assert_no_records(session)


def test_database_constraint_failure_rolls_back_partial_inserts(context, make_pdf):
    from pdf.models import PDFDocument, PDFLink

    service, _, session = context

    def duplicate_link(session, flush_context, instances):
        for document in session.new:
            if isinstance(document, PDFDocument) and document.links:
                first = document.links[0]
                document.links.append(PDFLink(platform=first.platform, url=first.url))

    event.listen(session, "before_flush", duplicate_link)
    try:
        with pytest.raises(IntegrityError):
            service.create_document("cv.pdf", make_pdf(urls=("https://github.com/example",)))
    finally:
        event.remove(session, "before_flush", duplicate_link)
    assert not session.in_transaction()
    assert_no_records(session)


def test_existing_and_missing_reads_and_closed_session(context, make_pdf):
    service, _, session = context
    created = service.create_document("cv.pdf", make_pdf(urls=("https://example.com/Profile",)))
    session.expunge_all()
    fetched = service.get_document(created.id)
    assert service.get_document(uuid4()) is None
    session.close()
    assert fetched.model_dump(mode="json") == created.model_dump(mode="json")


def test_repeated_uploads_create_new_documents(context, make_pdf):
    service, _, _ = context
    data = make_pdf()
    assert service.create_document("cv.pdf", data).id != service.create_document("cv.pdf", data).id
