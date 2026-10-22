from sqlalchemy.exc import (
    DBAPIError, DisconnectionError, IntegrityError, InterfaceError, OperationalError,
    SQLAlchemyError, TimeoutError as SQLAlchemyTimeoutError,
)

from core.exception_handlers import ApplicationError


class PDFInvalidFilenameError(ApplicationError):
    status_code = 422
    code = "PDF_INVALID_FILENAME"
    message = "A nonblank filename is required."


class PDFEmptyUploadError(ApplicationError):
    status_code = 422
    code = "PDF_EMPTY_UPLOAD"
    message = "The uploaded PDF is empty."


class PDFUnsupportedMediaTypeError(ApplicationError):
    status_code = 415
    code = "PDF_UNSUPPORTED_MEDIA_TYPE"
    message = "Upload a PDF or generic binary file."


class PDFUploadTooLargeError(ApplicationError):
    status_code = 413
    code = "PDF_UPLOAD_TOO_LARGE"
    message = "The uploaded PDF exceeds the 10 MiB limit."


class PDFInvalidError(ApplicationError):
    status_code = 422
    code = "PDF_INVALID"
    message = "The uploaded PDF could not be processed."


class PDFEncryptedError(PDFInvalidError):
    status_code = 422
    code = "PDF_ENCRYPTED"
    message = "Encrypted PDFs are not supported."


class PDFNotFoundError(ApplicationError):
    status_code = 404
    code = "PDF_NOT_FOUND"
    message = "The PDF document was not found."


class PDFDatabaseUnavailableError(ApplicationError):
    status_code = 503
    code = "PDF_DATABASE_UNAVAILABLE"
    message = "The PDF database is temporarily unavailable."


class PDFPersistenceError(ApplicationError):
    status_code = 500
    code = "PDF_PERSISTENCE_FAILED"
    message = "The PDF operation could not be completed."


def translate_database_error(error: SQLAlchemyError) -> ApplicationError:
    """Classify repository operations and service-owned commits identically.

    Constraint and other SQL failures remain persistence errors. Operational
    errors without a SQLSTATE include connection attempts rejected by the driver.
    """
    if isinstance(error, IntegrityError):
        return PDFPersistenceError()
    
    unavailable = isinstance(error, (DisconnectionError, SQLAlchemyTimeoutError))

    if isinstance(error, DBAPIError):
        sqlstate = getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)
        unavailable = error.connection_invalidated or (
            isinstance(error, (OperationalError, InterfaceError))
            and (sqlstate is None or sqlstate.startswith("08") or sqlstate in {
                "57P01", "57P02", "57P03", "53300",
            })
        )
    return PDFDatabaseUnavailableError() if unavailable else PDFPersistenceError()
