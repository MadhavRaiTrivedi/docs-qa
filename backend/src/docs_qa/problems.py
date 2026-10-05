import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import OpenAIError

from docs_qa.answering.errors import AnswerGenerationError, OpenAINotConfiguredError
from docs_qa.auth.api_key import InsufficientRoleError, MissingApiKeyError
from docs_qa.errors import NotFoundError
from docs_qa.library.errors import (
    DuplicateCollectionNameError,
    FileTooLargeError,
    InvalidDocumentTransitionError,
    UnsupportedFileError,
)

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"

_STATUS_BY_ERROR: dict[type[Exception], tuple[int, str]] = {
    NotFoundError: (status.HTTP_404_NOT_FOUND, "Not found"),
    DuplicateCollectionNameError: (status.HTTP_409_CONFLICT, "Duplicate collection name"),
    InvalidDocumentTransitionError: (status.HTTP_409_CONFLICT, "Invalid document state"),
    UnsupportedFileError: (status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Unsupported file"),
    FileTooLargeError: (status.HTTP_413_CONTENT_TOO_LARGE, "File too large"),
    MissingApiKeyError: (status.HTTP_401_UNAUTHORIZED, "Missing or invalid API key"),
    InsufficientRoleError: (status.HTTP_403_FORBIDDEN, "Forbidden"),
    OpenAINotConfiguredError: (status.HTTP_503_SERVICE_UNAVAILABLE, "OpenAI not configured"),
}


def problem(status_code: int, title: str, detail: str, **extensions: object) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status_code, "detail": detail}
    return JSONResponse(body | extensions, status_code=status_code, media_type=PROBLEM_JSON)


def register_problem_handlers(app: FastAPI) -> None:
    async def known_error(_: Request, error: Exception) -> JSONResponse:
        status_code, title = _STATUS_BY_ERROR[type(error)]
        return problem(status_code, title, str(error))

    async def validation_error(_: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, RequestValidationError)
        errors: dict[str, list[str]] = {}
        for item in error.errors():
            field = ".".join(str(part) for part in item["loc"] if part != "body")
            errors.setdefault(field, []).append(item["msg"])
        return problem(
            status.HTTP_400_BAD_REQUEST,
            "Invalid request",
            "One or more fields are invalid.",
            errors=errors,
        )

    async def generation_error(_: Request, error: Exception) -> JSONResponse:
        logger.exception("Answer generation failed", exc_info=error)
        return problem(
            status.HTTP_502_BAD_GATEWAY,
            "Answer generation failed",
            "The language model did not return an answer. Try again in a moment.",
        )

    for error_type in _STATUS_BY_ERROR:
        app.add_exception_handler(error_type, known_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(AnswerGenerationError, generation_error)
    app.add_exception_handler(OpenAIError, generation_error)
