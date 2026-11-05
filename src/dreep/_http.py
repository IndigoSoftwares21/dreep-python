"""Transport-agnostic HTTP core shared by the sync and async clients.

Everything here is pure: describing a request, turning a response into a
payload or a typed error, deciding whether and when to retry. The two clients
differ only in how they *send* a :class:`Request`, so all behaviour -- and its
tests -- lives in one place.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Final, Generic, TypeVar
from urllib.parse import urlsplit

import httpx

from . import _constants as c
from ._config import ClientConfig, TimeoutArg, _NotGiven, make_timeout, user_agent
from ._error_mapping import error_from_response
from ._errors import (
    DreepProcessingError,
)
from ._files import PreparedFile

__all__ = [
    "Operation",
    "Request",
    "build_request",
    "discard",
    "parse_response",
    "parse_text_response",
    "text_request",
]

T = TypeVar("T")

_PROCESSING_MESSAGE: Final = (
    "The result is still being produced. Request it again in a few seconds."
)


@dataclass
class Request:
    """Everything needed to send one HTTP request, with no transport attached."""

    method: str
    #: An API path (joined onto the base URL, authenticated), or an absolute
    #: URL sent as-is *without* the API key -- e.g. a public CDN fetch URL.
    path: str
    query: dict[str, str] = field(default_factory=dict)
    json: Any = None
    form: dict[str, str] | None = None
    file: PreparedFile | None = None
    #: A raw (possibly streamed) body, for PUTs to presigned storage URLs.
    content: Any = None
    #: Extra headers, merged over the defaults.
    headers: dict[str, str] = field(default_factory=dict)
    #: Uploads default to no timeout: a large file takes as long as it takes.
    is_upload: bool = False

    @property
    def is_absolute(self) -> bool:
        return urlsplit(self.path).scheme in c.URL_SCHEMES

    @property
    def retryable(self) -> bool:
        """Only GETs are retried. A retried upload would store a duplicate asset
        and bill a second transformation, and after a timeout there is no way to
        know whether the first attempt reached the API."""
        return self.method == c.Method.GET


@dataclass
class Operation(Generic[T]):
    """A request plus the function that turns its decoded payload into a result."""

    request: Request
    parse: Callable[[Any], T]


def text_request(url: str) -> Request:
    """A GET for an asset's OCR text through its public fetch URL (no API key)."""
    return Request(c.Method.GET, url)


def discard(_: Any) -> None:
    """Parser for endpoints whose success body carries nothing worth returning."""
    return


def build_request(
    client: httpx.Client | httpx.AsyncClient,
    config: ClientConfig,
    request: Request,
    timeout: TimeoutArg,
) -> httpx.Request:
    """Turns a :class:`Request` into an ``httpx.Request`` for either client type."""
    headers = {c.Header.USER_AGENT: user_agent(), c.Header.ACCEPT: c.CONTENT_TYPE_JSON}
    if not request.is_absolute:
        headers[c.Header.AUTHORIZATION] = f"{c.AUTH_SCHEME} {config.api_key}"
    headers.update(request.headers)
    if isinstance(timeout, _NotGiven):
        timeout = None if request.is_upload else config.timeout
    url = request.path if request.is_absolute else f"{config.base_url}{c.API_PREFIX}{request.path}"
    f = request.file
    return client.build_request(
        request.method,
        url,
        headers=headers,
        params=sorted(request.query.items()) or None,
        files={c.FILE_FIELD: (f.filename, f.stream, f.content_type)} if f else None,
        data=(request.form or {}) if f else None,
        json=None if f else request.json,
        content=request.content,
        timeout=make_timeout(timeout),
    )


def _decode_json(response: httpx.Response) -> Any:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        # A proxy or gateway error page rather than the API. The status still
        # says what happened, so the body is discarded.
        return None


def _raise_for_status(response: httpx.Response, body: Any) -> None:
    if not response.is_success:
        raise error_from_response(status=response.status_code, body=body, headers=response.headers)


def parse_response(response: httpx.Response) -> Any:
    """The payload of a successful response, or a raised typed error.

    Successes are wrapped as ``{message, code, data}``; ``data`` is unwrapped so
    callers get the asset rather than the envelope around it.
    """
    body = _decode_json(response)
    _raise_for_status(response, body)
    if isinstance(body, Mapping) and c.ENVELOPE_DATA in body:
        return body[c.ENVELOPE_DATA]
    return body


def parse_text_response(response: httpx.Response) -> str:
    """For CDN fetches that return text (OCR). A 202 means "not ready yet"."""
    if response.status_code == HTTPStatus.ACCEPTED:
        raise DreepProcessingError(_PROCESSING_MESSAGE, url=str(response.request.url))
    if not response.is_success:
        _raise_for_status(response, _decode_json(response))
    return response.text
