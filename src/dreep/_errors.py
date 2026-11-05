"""The exception hierarchy.

Every failure the SDK raises is a :class:`DreepError`, so ``except DreepError``
catches all of them. The subclasses exist so callers can branch on the cases
worth handling differently without comparing status codes.

    DreepError
    ├── DreepAPIError              any non-2xx response
    │   ├── DreepValidationError   400, 413
    │   ├── DreepAuthError         401, 403
    │   ├── DreepLimitError        402
    │   ├── DreepNotFoundError     404
    │   ├── DreepConflictError     409
    │   ├── DreepRateLimitError    429
    │   └── DreepServerError       5xx
    ├── DreepProcessingError       202 where a finished result was required
    └── DreepConnectionError       no response at all
        └── DreepTimeoutError      the request timed out
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "DreepAPIError",
    "DreepAuthError",
    "DreepConflictError",
    "DreepConnectionError",
    "DreepError",
    "DreepLimitError",
    "DreepNotFoundError",
    "DreepProcessingError",
    "DreepRateLimitError",
    "DreepServerError",
    "DreepTimeoutError",
    "DreepValidationError",
]


class DreepError(Exception):
    """Base class for every error the SDK raises."""

    message: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DreepAPIError(DreepError):
    """The API answered with a non-2xx status.

    Attributes:
        status: The HTTP status code.
        code: The machine-readable error code, e.g. ``"invalid_request"`` or
            ``"LIMIT_EXCEEDED"``, when the API sent one.
        validation_errors: Per-field problems on a 400, when the API sent them.
        request_id: The ``x-request-id`` response header, for support tickets.
        body: The decoded JSON error body, or ``None`` if there wasn't one.
    """

    status: int
    code: str | None
    validation_errors: list[Any] | None
    request_id: str | None
    body: Any

    def __init__(
        self,
        message: str,
        *,
        status: int,
        code: str | None = None,
        validation_errors: list[Any] | None = None,
        request_id: str | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.validation_errors = validation_errors
        self.request_id = request_id
        self.body = body

    def __str__(self) -> str:
        parts = [f"[{self.status}]"]
        if self.code:
            parts.append(f"{self.code}:")
        parts.append(self.message)
        if self.request_id:
            parts.append(f"(request id {self.request_id})")
        return " ".join(parts)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(status={self.status!r}, code={self.code!r}, "
            f"message={self.message!r})"
        )


class DreepValidationError(DreepAPIError):
    """400 or 413 -- the request was rejected as invalid.

    A 413 (file over the plan's size limit) lands here too: like a 400, it is
    bad input that no retry will fix. ``validation_errors`` lists each field.
    """


class DreepAuthError(DreepAPIError):
    """401 or 403 -- the API key is missing, malformed or revoked."""


class DreepLimitError(DreepAPIError):
    """402 -- a plan limit was reached.

    Attributes:
        feature_key: Which feature ran out, e.g. ``"bg_removals"``.
        used: Consumption at the moment the request was rejected.
        limit: The plan's ceiling for that feature.
    """

    feature_key: str | None
    used: int | None
    limit: int | None

    def __init__(
        self,
        message: str,
        *,
        feature_key: str | None = None,
        used: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.feature_key = feature_key
        self.used = used
        self.limit = limit


class DreepNotFoundError(DreepAPIError):
    """404 -- no such asset, folder, preset or upload."""


class DreepConflictError(DreepAPIError):
    """409 -- most often confirming an upload whose bytes haven't landed yet."""


class DreepRateLimitError(DreepAPIError):
    """429 -- too many requests.

    Attributes:
        retry_after: Seconds the API asked us to wait, if it said.
    """

    retry_after: float | None

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class DreepServerError(DreepAPIError):
    """5xx -- the API failed. Safe to retry for reads; think before retrying writes."""


class DreepProcessingError(DreepError):
    """A result is still being produced (the API answered 202).

    Raised where the SDK needed a finished result -- for example reading OCR
    text that is still being extracted. Request the same thing again shortly.
    """

    url: str

    def __init__(self, message: str, *, url: str) -> None:
        super().__init__(message)
        self.url = url


class DreepConnectionError(DreepError):
    """No response was received: DNS failure, refused or dropped connection."""


class DreepTimeoutError(DreepConnectionError):
    """The request timed out before a response arrived."""
