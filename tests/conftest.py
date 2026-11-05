"""Shared fixtures: clients wired to an in-memory transport instead of the network."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest

import dreep
from dreep import _async_core, _sync_core
from tests.support import API_KEY, SIGNING_SECRET, Handler


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DREEP_API_KEY", "DREEP_SIGNING_SECRET", "DREEP_API_URL"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retries happen instantly in tests; backoff maths is tested on its own."""
    monkeypatch.setattr(_sync_core, "retry_delay", lambda *_: 0.0)
    monkeypatch.setattr(_async_core, "retry_delay", lambda *_: 0.0)


@pytest.fixture
def make_client() -> Iterator[Callable[..., dreep.Dreep]]:
    clients: list[dreep.Dreep] = []

    def factory(handler: Handler, **kwargs: Any) -> dreep.Dreep:
        kwargs.setdefault("signing_secret", SIGNING_SECRET)
        http = httpx.Client(transport=httpx.MockTransport(handler))
        client = dreep.Dreep(API_KEY, http_client=http, **kwargs)
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client._http.close()


@pytest.fixture
def make_async_client() -> Callable[..., dreep.AsyncDreep]:
    def factory(handler: Handler, **kwargs: Any) -> dreep.AsyncDreep:
        kwargs.setdefault("signing_secret", SIGNING_SECRET)
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return dreep.AsyncDreep(API_KEY, http_client=http, **kwargs)

    return factory


@pytest.fixture(params=["asyncio", "trio"])
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return str(request.param)
