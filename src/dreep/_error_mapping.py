"""Turning an error response into the right exception, in one place.

The API is not perfectly uniform about where error detail lives: the reference
documents ``{error, message, code}`` while billing errors nest ``code``,
``featureKey``, ``used`` and ``limit`` under ``data``. Both are read, nested
first, so the exception carries the detail wherever the API put it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import partial
from http import HTTPStatus
from typing import Any, Final

from . import _constants as c
from ._errors import (
    DreepAPIError,
    DreepAuthError,
    DreepConflictError,
    DreepLimitError,
    DreepNotFoundError,
    DreepRateLimitError,
    DreepServerError,
    DreepValidationError,
)

__all__ = ["error_from_response", "parse_retry_after"]

_UNKNOWN_MESSAGE: Final = "The request failed."


class _Body:
    """Keys of an error response body."""

    MESSAGE: Final = "message"
    CODE: Final = "code"
    VALIDATION_ERRORS: Final = "validationErrors"
    FEATURE_KEY: Final = "featureKey"
    USED: Final = "used"
    LIMIT: Final = "limit"


#: Statuses with a dedicated exception class; anything else is a plain
#: DreepAPIError, or DreepServerError for 5xx.
_BY_STATUS: Final[dict[int, type[DreepAPIError]]] = {
    HTTPStatus.BAD_REQUEST: DreepValidationError,
    # A file over the plan's size limit is bad input that no retry will fix.
    HTTPStatus.REQUEST_ENTITY_TOO_LARGE: DreepValidationError,
    HTTPStatus.UNAUTHORIZED: DreepAuthError,
    HTTPStatus.FORBIDDEN: DreepAuthError,
    HTTPStatus.NOT_FOUND: DreepNotFoundError,
    HTTPStatus.CONFLICT: DreepConflictError,
}


def _as_int(value: Any) -> int | None:
    # Billing counters may arrive as strings (Postgres BIGINT).
    if isinstance(value, bool):
        return None
    try:
        return int(value) if isinstance(value, (int, float, str)) else None
    except ValueError:
        return None


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _as_list(value: Any) -> list[Any] | None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    return None


def parse_retry_after(value: str | None) -> float | None:
    """Reads a ``Retry-After`` header given in seconds. HTTP-dates are ignored."""
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


def error_from_response(*, status: int, body: Any, headers: Mapping[str, str]) -> DreepAPIError:
    """The single place an HTTP status becomes a typed error."""
    obj: Mapping[str, Any] = body if isinstance(body, Mapping) else {}
    nested = obj.get(c.ENVELOPE_DATA)
    data: Mapping[str, Any] = nested if isinstance(nested, Mapping) else {}

    def pick(key: str) -> Any:
        return data.get(key, obj.get(key))

    make = partial(
        _build,
        _as_str(obj.get(_Body.MESSAGE)) or _UNKNOWN_MESSAGE,
        status=status,
        code=_as_str(pick(_Body.CODE)),
        validation_errors=_as_list(pick(_Body.VALIDATION_ERRORS)),
        request_id=headers.get(c.Header.REQUEST_ID),
        body=body,
    )
    if status == HTTPStatus.PAYMENT_REQUIRED:
        return make(
            DreepLimitError,
            feature_key=_as_str(pick(_Body.FEATURE_KEY)),
            used=_as_int(pick(_Body.USED)),
            limit=_as_int(pick(_Body.LIMIT)),
        )
    if status == HTTPStatus.TOO_MANY_REQUESTS:
        return make(
            DreepRateLimitError,
            retry_after=parse_retry_after(headers.get(c.Header.RETRY_AFTER)),
        )
    if status in _BY_STATUS:
        return make(_BY_STATUS[status])
    if status >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return make(DreepServerError)
    return make(DreepAPIError)


def _build(message: str, cls: type[DreepAPIError], **kwargs: Any) -> DreepAPIError:
    return cls(message, **kwargs)
