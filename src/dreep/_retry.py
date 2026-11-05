"""When and how long to wait before retrying a request.

Only GETs are retried: on 429, any 5xx, or a connection failure. Delays grow
exponentially with jitter, and a ``Retry-After`` header wins when present.
"""

from __future__ import annotations

import logging
import random
from http import HTTPStatus
from typing import Final

import httpx

from . import _constants as c
from ._errors import (
    DreepAPIError,
    DreepConnectionError,
    DreepError,
    DreepRateLimitError,
    DreepTimeoutError,
)
from ._http import Request

__all__ = ["connection_error", "log_retry", "retry_delay", "should_retry"]

logger = logging.getLogger(c.LOGGER_NAME)

#: Fraction of a backoff delay randomly shaved off, so clients don't retry in lockstep.
_JITTER: Final = 0.25
_REDACTED_URL: Final = "<url>"


def should_retry(request: Request, error: DreepError) -> bool:
    if not request.retryable:
        return False
    if isinstance(error, DreepConnectionError):
        return True
    if isinstance(error, DreepAPIError):
        return (
            error.status == HTTPStatus.TOO_MANY_REQUESTS
            or error.status >= HTTPStatus.INTERNAL_SERVER_ERROR
        )
    return False


def retry_delay(attempt: int, error: DreepError) -> float:
    """Exponential backoff with jitter, or the server's ``Retry-After`` when given."""
    if isinstance(error, DreepRateLimitError) and error.retry_after is not None:
        return min(error.retry_after, c.RETRY_MAX_DELAY)
    base: float = min(c.RETRY_BASE_DELAY * float(2**attempt), c.RETRY_MAX_DELAY)
    return base * (1 - _JITTER * random.random())  # noqa: S311 -- jitter, not crypto


def connection_error(exc: httpx.TransportError) -> DreepConnectionError:
    if isinstance(exc, httpx.TimeoutException):
        return DreepTimeoutError(f"The request timed out: {exc}")
    return DreepConnectionError(f"The request failed before a response was received: {exc}")


def log_retry(request: Request, attempt: int, delay: float, error: DreepError) -> None:
    # Absolute URLs may be signed; never log one.
    target = _REDACTED_URL if request.is_absolute else request.path
    logger.info(
        "Retrying %s %s in %.2fs (retry %d) after: %s",
        request.method,
        target,
        delay,
        attempt + 1,
        error,
    )
