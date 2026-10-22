from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
import logging
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import UploadFile
from fastapi.exceptions import ResponseValidationError
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pypdf.errors import PdfReadError
from starlette.datastructures import Headers, UploadFile as StarletteUploadFile

from pdf.exceptions import (
    PDFInvalidFilenameError, PDFEmptyUploadError, PDFUnsupportedMediaTypeError,
    PDFUploadTooLargeError, PDFInvalidError, PDFEncryptedError, PDFNotFoundError,
    PDFDatabaseUnavailableError, PDFPersistenceError,
)


@pytest.fixture
def context(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    from main import app
    from pdf.dependencies import get_pdf_service
    from pdf.schemas import PDFDocumentRead, PDFLinkRead
    from pdf.service import PDFService

    response = PDFDocumentRead(
        id=uuid4(), filename="cv.pdf", content="Developer",
        created_at=datetime.now(timezone.utc),
        links=[PDFLinkRead(id=uuid4(), platform="github.com", url="https://github.com/Alice")],
    )
    service = Mock(spec=PDFService)
    service.create_document.return_value = response
    service.get_document.return_value = response
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_pdf_service] = lambda: service
    uploads = []
    original_init = StarletteUploadFile.__init__

    def track_upload(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        uploads.append(self)

    monkeypatch.setattr(StarletteUploadFile, "__init__", track_upload)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield SimpleNamespace(
                app=app, client=client, service=service, response=response, uploads=uploads,
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.mark.parametrize("content_type", [
    "application/pdf", "application/octet-stream", "binary/octet-stream", "application/pdf; version=1.7",
])
def test_upload_success(context, content_type):
    response = context.client.post("/api/upload-pdf", files={"pdf": ("cv.pdf", b"pdf bytes", content_type)})
    assert response.status_code == 201
    assert response.json() == context.response.model_dump(mode="json")
    context.service.create_document.assert_called_once_with("cv.pdf", b"pdf bytes")
    assert context.uploads and all(upload.file.closed for upload in context.uploads)


@pytest.mark.parametrize("filename, data, content_type, expected", [
    (" ", b"pdf", "application/pdf", 422),
    ("cv.pdf", b"", "application/pdf", 422),
    ("cv.pdf", b"pdf", "image/png", 415),
    ("cv.pdf", b"pdf", "text/plain", 415),
    ("cv.pdf", b"x" * (10 * 1024 * 1024 + 1), "application/pdf", 413),
], ids=["blank-filename", "empty-input", "image", "text", "too-large"])
def test_rejected_uploads_skip_service_and_close_files(context, filename, data, content_type, expected):
    response = context.client.post("/api/upload-pdf", files={"pdf": (filename, data, content_type)})
    assert response.status_code == expected
    assert set(response.json()["error"]) == {"code", "message", "details"}
    context.service.create_document.assert_not_called()
    assert context.uploads and all(upload.file.closed for upload in context.uploads)


def test_missing_file(context):
    assert context.client.post("/api/upload-pdf").status_code == 422
    context.service.create_document.assert_not_called()


def test_upload_at_limit_is_accepted(context):
    data = b"x" * (10 * 1024 * 1024)
    response = context.client.post("/api/upload-pdf", files={"pdf": ("cv.pdf", data, "application/pdf")})
    assert response.status_code == 201
    context.service.create_document.assert_called_once_with("cv.pdf", data)


@pytest.mark.parametrize("actual_size, reported_size, expected", [
    (10 * 1024 * 1024 + 100, 1, 413),
    (8, 999999999, 201),
])
def test_read_is_bounded_and_reported_size_is_ignored(context, actual_size, reported_size, expected):
    from pdf.router import MAX_UPLOAD_BYTES, upload_pdf

    class TrackedStream(BytesIO):
        def read(self, size=-1):
            self.requested_size = size
            return super().read(size)

    stream = TrackedStream(b"x" * actual_size)
    upload = UploadFile(
        file=stream, filename="cv.pdf", size=reported_size,
        headers=Headers({"content-type": "application/pdf"}),
    )
    if expected == 413:
        with pytest.raises(PDFUploadTooLargeError) as caught:
            upload_pdf(upload, context.service)
        context.service.create_document.assert_not_called()
    else:
        assert upload_pdf(upload, context.service) == context.response
    assert stream.requested_size == MAX_UPLOAD_BYTES + 1
    assert stream.closed


@pytest.mark.parametrize("encrypted", [False, True])
def test_malformed_and_encrypted_pdfs(context, make_pdf, encrypted):
    from pdf.parser import PDFParser

    def parse(filename, data):
        PDFParser(BytesIO(data)).parse()

    context.service.create_document.side_effect = parse
    data = make_pdf(encrypted=True) if encrypted else b"not a PDF"
    response = context.client.post("/api/upload-pdf", files={"pdf": ("cv.pdf", data, "application/pdf")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == ("PDF_ENCRYPTED" if encrypted else "PDF_INVALID")
    assert all(upload.file.closed for upload in context.uploads)


def test_successful_and_missing_lookup(context):
    document_id = context.response.id
    response = context.client.get(f"/api/pdf/{document_id}")
    assert response.status_code == 200
    assert response.json() == context.response.model_dump(mode="json")
    context.service.get_document.assert_called_once_with(document_id)
    context.service.get_document.return_value = None
    assert context.client.get(f"/api/pdf/{uuid4()}").status_code == 404


def test_invalid_and_missing_uuid(context):
    assert context.client.get("/api/pdf/not-a-uuid").status_code == 422
    assert context.client.get("/api/pdf/").status_code == 404
    context.service.get_document.assert_not_called()


def validation_error():
    from pdf.schemas import PDFDocumentRead

    try:
        PDFDocumentRead.model_validate({"id": "private-document-text"})
    except ValidationError as error:
        return error


@pytest.mark.parametrize("error_factory, expected, code", [
    (PDFInvalidFilenameError, 422, "PDF_INVALID_FILENAME"),
    (PDFEmptyUploadError, 422, "PDF_EMPTY_UPLOAD"),
    (PDFUnsupportedMediaTypeError, 415, "PDF_UNSUPPORTED_MEDIA_TYPE"),
    (PDFUploadTooLargeError, 413, "PDF_UPLOAD_TOO_LARGE"),
    (PDFInvalidError, 422, "PDF_INVALID"),
    (PDFEncryptedError, 422, "PDF_ENCRYPTED"),
    (PDFNotFoundError, 404, "PDF_NOT_FOUND"),
    (PDFDatabaseUnavailableError, 503, "PDF_DATABASE_UNAVAILABLE"),
    (PDFPersistenceError, 500, "PDF_PERSISTENCE_FAILED"),
    (lambda: ValueError("private-document-text"), 500, "INTERNAL_ERROR"),
    (lambda: PdfReadError("private-document-text"), 500, "INTERNAL_ERROR"),
    (validation_error, 500, "INTERNAL_ERROR"),
    (lambda: ResponseValidationError([{"input": "private-document-text"}]), 500, "INTERNAL_ERROR"),
    (lambda: RuntimeError("private-document-text"), 500, "INTERNAL_ERROR"),
])
@pytest.mark.parametrize("operation", ["upload", "lookup"])
def test_safe_error_mapping(context, caplog, error_factory, expected, code, operation):
    with caplog.at_level(logging.ERROR, logger="core.exception_handlers"):
        if operation == "upload":
            context.service.create_document.side_effect = error_factory()
            response = context.client.post("/api/upload-pdf", files={"pdf": ("cv.pdf", b"pdf", "application/pdf")})
            assert all(upload.file.closed for upload in context.uploads)
        else:
            context.service.get_document.side_effect = error_factory()
            response = context.client.get(f"/api/pdf/{uuid4()}")
    assert response.status_code == expected
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == []
    for sensitive in ("private-document-text", "private-credential", "SELECT secret", "INSERT secret"):
        assert sensitive not in response.text
        assert sensitive not in caplog.text
    if expected >= 500:
        assert "Request failed" in caplog.text
        assert all(record.exc_info is None for record in caplog.records if record.name == "core.exception_handlers")


@pytest.mark.parametrize("operation", ["upload", "lookup"])
def test_invalid_service_response_is_internal_failure(context, operation):
    if operation == "upload":
        context.service.create_document.return_value = {"id": "bad"}
        response = context.client.post("/api/upload-pdf", files={"pdf": ("cv.pdf", b"pdf", "application/pdf")})
    else:
        context.service.get_document.return_value = {"id": "bad"}
        response = context.client.get(f"/api/pdf/{uuid4()}")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


def test_registration_and_health(context):
    def endpoints(router):
        for route in router.routes:
            if hasattr(route, "original_router"):
                yield from endpoints(route.original_router)
            elif hasattr(route, "methods"):
                for method in route.methods:
                    yield method, route.path

    counts = Counter(endpoints(context.app))
    assert counts["POST", "/upload-pdf"] + counts["POST", "/api/upload-pdf"] == 1
    assert counts["GET", "/pdf/{document_id}"] + counts["GET", "/api/pdf/{document_id}"] == 1
    assert counts["GET", "/health"] + counts["GET", "/api/health"] == 1
    assert context.client.get("/api/health").json() == {"status": "OK"}
    assert set(context.app.openapi()["paths"]) >= {
        "/api/upload-pdf", "/api/pdf/{document_id}", "/api/health",
    }


def test_real_dependency_chain_uses_injected_session(context, monkeypatch):
    from core.database import get_db
    from pdf.dependencies import get_pdf_service
    from pdf.service import PDFService

    session = Mock()
    context.app.dependency_overrides.pop(get_pdf_service)
    context.app.dependency_overrides[get_db] = lambda: session

    def create(service, filename, data):
        assert service.repository.session is session
        return context.response

    monkeypatch.setattr(PDFService, "create_document", create)
    assert context.client.post("/api/upload-pdf", files={"pdf": ("cv.pdf", b"pdf", "application/pdf")}).status_code == 201
    session.commit.assert_not_called()
    session.close.assert_not_called()


def test_file_read_failure_propagates_and_upload_is_closed(context):
    from pdf.router import upload_pdf

    stream = Mock()
    stream.read.side_effect = OSError("private-document-text")
    upload = UploadFile(file=stream, filename="cv.pdf", headers=Headers({"content-type": "application/pdf"}))
    with pytest.raises(OSError):
        upload_pdf(upload, context.service)
    stream.close.assert_called_once()
    context.service.create_document.assert_not_called()


def test_real_request_validation_details_are_safe(context):
    response = context.client.get("/api/pdf/private-document-text")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"
    assert response.json()["error"]["details"] == [{
        "location": ["path", "document_id"], "message": "Must be a valid UUID.",
    }]
    assert "private-document-text" not in response.text
    missing = context.client.post("/api/upload-pdf")
    assert missing.json()["error"]["details"] == [{
        "location": ["body", "pdf"], "message": "Field required.",
    }]


def test_openapi_documents_error_contract_and_all_pdf_codes(context):
    document = context.app.openapi()
    upload = document["paths"]["/api/upload-pdf"]["post"]["responses"]
    lookup = document["paths"]["/api/pdf/{document_id}"]["get"]["responses"]
    codes = set()
    for response in [*upload.values(), *lookup.values()]:
        content = response.get("content", {}).get("application/json", {})
        for example in content.get("examples", {}).values():
            codes.add(example["value"]["error"]["code"])
    assert codes == {
        "PDF_INVALID_FILENAME", "PDF_EMPTY_UPLOAD", "PDF_UNSUPPORTED_MEDIA_TYPE",
        "PDF_UPLOAD_TOO_LARGE", "PDF_INVALID", "PDF_ENCRYPTED", "PDF_NOT_FOUND",
        "PDF_DATABASE_UNAVAILABLE", "PDF_PERSISTENCE_FAILED", "INTERNAL_ERROR",
        "REQUEST_VALIDATION_FAILED",
    }
    schemas = document["components"]["schemas"]
    assert "error" in schemas["ErrorResponse"]["properties"]
    assert set(schemas["ErrorBody"]["properties"]) == {"code", "message", "details"}
    assert upload["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")
