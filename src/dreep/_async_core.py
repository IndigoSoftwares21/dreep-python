"""The asynchronous client's core: configuration, transport, retries, URLs.

This file is the source of truth for ``_sync_core.py``, which
``scripts/unasync.py`` generates from it. Edit this one, then regenerate.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from types import TracebackType
from typing import Any, TypeVar

import anyio
import httpx

from . import _constants as c
from ._config import NOT_GIVEN, ClientConfig, TimeoutArg, masked_key
from ._errors import DreepError
from ._http import (
    Operation,
    Request,
    build_request,
    parse_response,
)
from ._retry import connection_error, log_retry, retry_delay, should_retry
from ._transform import TransformInput
from ._urls import build_signed_url, build_url

T = TypeVar("T")
_Self = TypeVar("_Self", bound="AsyncCore")


class AsyncCore:
    """Shared plumbing. Use :class:`dreep.AsyncDreep`, which builds on this."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        signing_secret: str | None = None,
        timeout: float | None = c.DEFAULT_TIMEOUT,
        max_retries: int = c.DEFAULT_MAX_RETRIES,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Creates a client.

        Args:
            api_key: Project API key (``drp_live_…``). Defaults to the
                ``DREEP_API_KEY`` environment variable. Keep it server-side: it
                can read, upload and delete every asset in the project.
            signing_secret: URL Signing Secret, needed only by
                :meth:`signed_url`. Defaults to ``DREEP_SIGNING_SECRET``.
            timeout: Seconds a JSON request may take; ``None`` for no limit.
                Uploads ignore it and default to no limit -- bound them with a
                per-call ``timeout=``.
            max_retries: Retries for GET requests on 429, 5xx and connection
                failures. ``0`` disables. Writes are never retried.
            http_client: A preconfigured ``httpx`` client (proxies, custom
                transports). The caller keeps ownership and must close it.
        """
        self._config = ClientConfig.resolve(
            api_key=api_key, signing_secret=signing_secret, timeout=timeout, max_retries=max_retries
        )
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(follow_redirects=False)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(api_key={masked_key(self._config.api_key)!r})"

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def aclose(self) -> None:
        """Closes the underlying HTTP connections, unless the caller owns them."""
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self: _Self) -> _Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    # ------------------------------------------------------------------ #
    # Transport
    # ------------------------------------------------------------------ #

    async def _send(self, request: Request, timeout: TimeoutArg) -> httpx.Response:
        http_request = build_request(self._http, self._config, request, timeout)
        try:
            return await self._http.send(http_request)
        except httpx.TransportError as exc:
            raise connection_error(exc) from exc

    async def _run(
        self,
        op: Operation[T],
        timeout: TimeoutArg = NOT_GIVEN,
        read: Callable[[httpx.Response], Any] = parse_response,
    ) -> T:
        """Sends an operation, retrying idempotent requests, and parses the result."""
        attempt = 0
        while True:
            try:
                response = await self._send(op.request, timeout)
                return op.parse(read(response))
            except DreepError as error:
                if attempt >= self._config.max_retries or not should_retry(op.request, error):
                    raise
                delay = retry_delay(attempt, error)
                log_retry(op.request, attempt, delay, error)
                await anyio.sleep(delay)
                attempt += 1

    # ------------------------------------------------------------------ #
    # URLs -- pure string work, no network
    # ------------------------------------------------------------------ #

    def url(self, target: Any, transform: TransformInput = None) -> str:
        """Applies a transform to an asset's delivery URL. No network call.

        Args:
            target: An asset (anything with a ``url``), or a URL the API returned.
            transform: The transform to apply. Omit for the original.

        Example::

            client.url(asset, {"width": 400, "format": "webp"})
        """
        return build_url(target, transform)

    def signed_url(
        self,
        asset: Any,
        *,
        expires_in: int | timedelta,
        transform: TransformInput = None,
    ) -> str:
        """A time-limited URL for an asset in a signed folder. No network call.

        Requires ``signing_secret``. Treat the result as a bearer token: anyone
        holding it can fetch the asset until it expires, with no API key.

        Args:
            asset: The asset itself (``id`` and ``url``); the id is what's signed.
            expires_in: Seconds (or a ``timedelta``) until the link stops working.
            transform: A transform to sign alongside the asset. Width, height,
                quality and dpr are snapped onto the API's breakpoints first,
                exactly as the API does before verifying.
        """
        return build_signed_url(
            asset,
            signing_secret=self._config.signing_secret,
            expires_in=expires_in,
            transform=transform,
        )
