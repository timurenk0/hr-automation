from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
import pytest

from core.exception_handlers import error_responses, register_exception_handlers


@pytest.fixture
def client():
    app = FastAPI(responses=error_responses())
    register_exception_handlers(app)

    @app.get("/framework/{status}")
    def framework(status: int):
        raise HTTPException(
            status,
            detail="private-document-text",
            headers={"Retry-After": "30", "WWW-Authenticate": "Bearer"},
        )

    @app.post("/validation")
    def validation():
        raise RequestValidationError([{
            "type": "value_error", "loc": ("body", "filename"),
            "msg": "private-document-text", "input": "private-document-text",
            "ctx": {"error": ValueError("private-credential")},
        }])

    @app.get("/unexpected")
    def unexpected():
        raise ValueError("private-document-text")

    @app.get("/response-validation", response_model=dict[str, int])
    def response_validation():
        return {"count": "private-document-text"}

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.parametrize(
    "status, code",
    [(401, "HTTP_401"), (429, "HTTP_429"), (503, "INTERNAL_ERROR")],
)
def test_framework_errors_preserve_headers_and_hide_raw_details(client, status, code):
    response = client.get(f"/framework/{status}")

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.headers["Retry-After"] == "30"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert "private-document-text" not in response.text


def test_validation_details_have_only_location_and_safe_message(client):
    response = client.post("/validation")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"
    assert response.json()["error"]["details"] == [{
        "location": ["body", "filename"], "message": "Invalid value.",
    }]
    assert "private-" not in response.text


@pytest.mark.parametrize("url, method, code, status", [
    ("/missing", "get", "HTTP_404", 404),
    ("/unexpected", "post", "HTTP_405", 405),
    ("/unexpected", "get", "INTERNAL_ERROR", 500),
    ("/response-validation", "get", "INTERNAL_ERROR", 500),
])
def test_framework_and_internal_failures_use_envelope(
    client,
    caplog,
    url,
    method,
    code,
    status,
):
    response = getattr(client, method)(url)

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == []
    assert "private-" not in response.text
    assert "private-" not in caplog.text
    if status == 405:
        assert response.headers["allow"] == "GET"
