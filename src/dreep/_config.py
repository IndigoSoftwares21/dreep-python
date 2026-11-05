"""Client configuration, resolved once at construction."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from enum import Enum
from typing import Final

import httpx

from . import _constants as c
from ._errors import DreepError
from ._version import __version__

__all__ = ["NOT_GIVEN", "ClientConfig", "TimeoutArg", "make_timeout", "masked_key", "user_agent"]

_MISSING_API_KEY: Final = (
    "An API key is required. Pass api_key= or set the DREEP_API_KEY environment variable."
)
#: Characters of a key shown at each end when masked for logs and reprs.
_MASK_HEAD: Final = 9
_MASK_TAIL: Final = 4
_MASK_MIN_LENGTH: Final = 16
_ELLIPSIS: Final = "…"


class _NotGiven(Enum):
    """Sentinel distinguishing "not passed" from an explicit ``None``."""

    NOT_GIVEN = "NOT_GIVEN"

    def __repr__(self) -> str:
        return self.value


NOT_GIVEN: Final = _NotGiven.NOT_GIVEN
#: Per-call timeout: seconds, ``None`` for no limit, or ``NOT_GIVEN`` for the default.
TimeoutArg = float | None | _NotGiven


@dataclass(frozen=True)
class ClientConfig:
    api_key: str
    signing_secret: str | None
    base_url: str
    timeout: float | None
    max_retries: int

    @classmethod
    def resolve(
        cls,
        *,
        api_key: str | None,
        signing_secret: str | None,
        timeout: float | None,
        max_retries: int,
    ) -> ClientConfig:
        """Fills unset values from the environment and validates the rest."""
        key = api_key if api_key is not None else os.environ.get(c.ENV_API_KEY)
        if not key:
            raise DreepError(_MISSING_API_KEY)
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0.")
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be positive, or None for no limit.")
        secret = (
            signing_secret if signing_secret is not None else os.environ.get(c.ENV_SIGNING_SECRET)
        )
        return cls(
            api_key=key,
            signing_secret=secret or None,
            base_url=(os.environ.get(c.ENV_API_URL) or c.API_URL).rstrip("/"),
            timeout=timeout,
            max_retries=max_retries,
        )

    def __repr__(self) -> str:
        # Never let a key reach a log line or a traceback.
        return (
            f"ClientConfig(api_key={masked_key(self.api_key)!r}, base_url={self.base_url!r}, "
            f"timeout={self.timeout!r}, max_retries={self.max_retries!r})"
        )


def user_agent() -> str:
    return (
        f"dreep-python/{__version__} "
        f"(python {platform.python_version()}; httpx {httpx.__version__})"
    )


def masked_key(api_key: str) -> str:
    """Enough of a key to tell two apart in a log, never enough to use it."""
    if len(api_key) <= _MASK_MIN_LENGTH:
        return _ELLIPSIS
    return f"{api_key[:_MASK_HEAD]}{_ELLIPSIS}{api_key[-_MASK_TAIL:]}"


def make_timeout(seconds: float | None) -> httpx.Timeout:
    """A total timeout, but never an unbounded *connect*."""
    connect = c.CONNECT_TIMEOUT if seconds is None else min(seconds, c.CONNECT_TIMEOUT)
    return httpx.Timeout(seconds, connect=connect)
