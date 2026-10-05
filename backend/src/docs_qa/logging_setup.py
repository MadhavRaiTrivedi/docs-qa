import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import UTC, datetime

from fastapi import Request, Response

from docs_qa.http_headers import HeaderNames

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

logger = logging.getLogger("docs_qa.http")

MILLISECONDS_PER_SECOND = 1000


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "requestId": request_id.get(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    # Uvicorn's access log would repeat every request that log_requests already records.
    logging.getLogger("uvicorn.access").disabled = True


async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    current_id = request.headers.get(HeaderNames.REQUEST_ID) or str(uuid.uuid4())
    token = request_id.set(current_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * MILLISECONDS_PER_SECOND)
        logger.info(
            "%s %s -> %s in %s ms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        response.headers[HeaderNames.REQUEST_ID] = current_id
        return response
    finally:
        request_id.reset(token)
