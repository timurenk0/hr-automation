from dataclasses import dataclass
from http import HTTPStatus
import logging
from typing import ClassVar, Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from starlette.exceptions import HTTPException


logger = logging.getLogger(__name__)


class ValidationIssue(BaseModel):
    location: list[str | int]
    message: str


class ErrorBody(BaseModel):
    code: str = Field(
        description="Stable identifier for frontend branching and localization."
    )
    message: str = Field(
        description="Safe default display message; never raw exception text."
    )
    details: list[ValidationIssue] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody


@dataclass(frozen=True)
class ErrorMapping:
    status: int
    code: str
    message: str


class ApplicationError(Exception):
    """Base for feature-owned errors with safe, public response metadata."""

    status_code: ClassVar[int] = 500
    code: ClassVar[str] = "INTERNAL_ERROR"
    message: ClassVar[str] = "An internal error occurred."


def _error_mapping(error_type: type[ApplicationError]) -> ErrorMapping:
    return ErrorMapping(error_type.status_code, error_type.code, error_type.message)


INTERNAL_ERROR = ErrorMapping(500, "INTERNAL_ERROR", "An internal error occurred.")
REQUEST_VALIDATION_ERROR = ErrorMapping(
    422, "REQUEST_VALIDATION_FAILED", "The request contains invalid fields."
)


def _response(
    mapping: ErrorMapping,
    details: list[ValidationIssue] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(
            code=mapping.code,
            message=mapping.message,
            details=details or [],
        )
    )

    return JSONResponse(
        status_code=mapping.status,
        content=payload.model_dump(),
        headers=headers,
    )


def _log_internal(error: Exception) -> None:
    # Do not log str(error), traceback locals, request bodies, URLs or SQL params.
    logger.error("Request failed: %s", type(error).__name__)


async def application_error_handler(
    request: Request, error: ApplicationError
) -> JSONResponse:
    mapping = _error_mapping(type(error))
    if mapping.status >= 500:
        _log_internal(error)

    return _response(mapping)


async def request_validation_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    messages = {
        "missing": "Field required.",
        "uuid_parsing": "Must be a valid UUID.",
        "uuid_type": "Must be a valid UUID.",
        "json_invalid": "Invalid JSON.",
    }

    # Raw Pydantic messages/contexts can include submitted values or validator
    # exception text. Only expose field locations and controlled messages.
    details = [
        ValidationIssue(
            location=list(issue.get("loc", ())),
            message=messages.get(issue.get("type"), "Invalid value."),
        )
        for issue in error.errors()
    ]

    return _response(REQUEST_VALIDATION_ERROR, details)


async def http_error_handler(request: Request, error: HTTPException) -> JSONResponse:
    if error.status_code >= 500:
        _log_internal(error)
        mapping = ErrorMapping(
            error.status_code, INTERNAL_ERROR.code, INTERNAL_ERROR.message
        )
    else:
        try:
            message = HTTPStatus(error.status_code).phrase
        except ValueError:
            message = "The request could not be completed."

        mapping = ErrorMapping(error.status_code, f"HTTP_{error.status_code}", message)

    return _response(mapping, headers=error.headers)


async def internal_error_handler(request: Request, error: Exception) -> JSONResponse:
    _log_internal(error)

    return _response(INTERNAL_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(ValidationError, internal_error_handler)
    app.add_exception_handler(ResponseValidationError, internal_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)


def error_responses(*error_types: type[ApplicationError]) -> dict:
    """Document the same envelope, codes and safe messages used at runtime."""
    mappings = [_error_mapping(cls) for cls in error_types]
    mappings.extend([REQUEST_VALIDATION_ERROR, INTERNAL_ERROR])

    responses: dict = {}

    for mapping in mappings:
        response = responses.setdefault(
            mapping.status,
            {
                "model": ErrorResponse,
                "description": (
                    "Errors use error.code for branching; error.message is for "
                    "display. Details exclude submitted values."
                ),
                "content": {"application/json": {"examples": {}}},
            },
        )

        response["content"]["application/json"]["examples"][mapping.code] = {
            "value": {
                "error": {
                    "code": mapping.code,
                    "message": mapping.message,
                    "details": [],
                }
            },
        }

    responses["default"] = {
        "model": ErrorResponse,
        "description": (
            "Framework HTTP errors use HTTP_<status> (for example HTTP_404); "
            "unexpected failures use INTERNAL_ERROR. "
            "Required HTTP headers are preserved."
        ),
    }

    return responses
