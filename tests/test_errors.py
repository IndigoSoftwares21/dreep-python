"""Mapping HTTP error responses onto the exception hierarchy."""

from __future__ import annotations

from typing import Any

import pytest

from dreep import (
    DreepAPIError,
    DreepAuthError,
    DreepConflictError,
    DreepLimitError,
    DreepNotFoundError,
    DreepRateLimitError,
    DreepServerError,
    DreepValidationError,
)
from dreep._error_mapping import error_from_response, parse_retry_after


def make(status: int, body: Any = None, **headers: str) -> DreepAPIError:
    return error_from_response(status=status, body=body, headers=headers)


@pytest.mark.parametrize(
    ("status", "cls"),
    [
        (400, DreepValidationError),
        (413, DreepValidationError),
        (401, DreepAuthError),
        (403, DreepAuthError),
        (402, DreepLimitError),
        (404, DreepNotFoundError),
        (409, DreepConflictError),
        (429, DreepRateLimitError),
        (500, DreepServerError),
        (503, DreepServerError),
        (418, DreepAPIError),
    ],
)
def test_status_maps_to_class(status: int, cls: type[DreepAPIError]) -> None:
    error = make(status, {"message": "nope"})
    assert type(error) is cls
    assert (error.status, error.message) == (status, "nope")


def test_limit_error_reads_nested_billing_data() -> None:
    body = {
        "message": "limit",
        "data": {"code": "LIMIT_EXCEEDED", "featureKey": "bg_removals", "used": "10", "limit": 10},
    }
    error = make(402, body)
    assert isinstance(error, DreepLimitError)
    assert (error.code, error.feature_key, error.used, error.limit) == (
        "LIMIT_EXCEEDED",
        "bg_removals",
        10,
        10,
    )


def test_limit_error_falls_back_to_top_level_fields() -> None:
    error = make(402, {"message": "m", "code": "LIMIT_EXCEEDED", "featureKey": "ocr_pages"})
    assert isinstance(error, DreepLimitError)
    assert (error.code, error.feature_key, error.used) == ("LIMIT_EXCEEDED", "ocr_pages", None)


def test_validation_errors_and_request_id() -> None:
    issues = [{"path": ["width"], "message": "too big"}]
    error = make(400, {"message": "bad", "validationErrors": issues}, **{"x-request-id": "r1"})
    assert error.validation_errors == issues
    assert error.request_id == "r1"
    assert str(error) == "[400] bad (request id r1)"


def test_non_json_bodies_get_a_generic_message() -> None:
    error = make(502, None)
    assert error.message == "The request failed."
    assert repr(error).startswith("DreepServerError(status=502")


def test_rate_limit_reads_retry_after() -> None:
    error = make(429, {}, **{"retry-after": "3"})
    assert isinstance(error, DreepRateLimitError)
    assert error.retry_after == 3.0


@pytest.mark.parametrize(
    ("value", "expected"), [(None, None), ("", None), ("2.5", 2.5), ("-1", None), ("Wed, 21", None)]
)
def test_parse_retry_after(value: str | None, expected: float | None) -> None:
    assert parse_retry_after(value) == expected
