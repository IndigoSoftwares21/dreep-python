"""Delivery URLs and signed URLs -- pure string work, no network.

URLs are never built from scratch: the delivery host and API version come from
server configuration, so the only correct base is a URL the API returned.
Query strings are encoded byte-for-byte like JavaScript's ``URLSearchParams``.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import time
from collections.abc import Mapping
from datetime import timedelta
from typing import Any, Final
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from . import _constants as c
from . import _transform_constants as t
from ._errors import DreepError
from ._jsnum import to_wire
from ._transform import TransformInput, normalize_transform

__all__ = ["build_signed_url", "build_url", "target_id", "target_url"]

_SIGNING_REQUIRED_MESSAGE: Final = (
    "signed_url() requires a signing secret. Pass signing_secret= to the client or set "
    "DREEP_SIGNING_SECRET. Find it on the API Keys page of your dashboard."
)
_ID_ATTR: Final = "id"
_URL_ATTR: Final = "url"
#: Characters ``application/x-www-form-urlencoded`` leaves unescaped.
_FORM_SAFE: Final = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789*-._")
_SPACE: Final = " "
_FORM_SPACE: Final = "+"

Pairs = list[tuple[str, str]]


def _attr(target: Any, name: str) -> Any:
    return target.get(name) if isinstance(target, Mapping) else getattr(target, name, None)


def target_url(target: Any) -> str:
    """The delivery URL of an asset, a mapping with ``url``, or a URL string."""
    url = target if isinstance(target, str) else _attr(target, _URL_ATTR)
    if not isinstance(url, str) or not url:
        raise TypeError("Expected an asset with a 'url', or a URL string the API returned.")
    parts = urlsplit(url)
    if parts.scheme not in c.URL_SCHEMES or not parts.netloc:
        raise ValueError(f"Not an absolute http(s) URL: {url!r}")
    return url


def target_id(target: Any) -> str:
    asset_id = _attr(target, _ID_ATTR)
    if not isinstance(asset_id, str) or not asset_id:
        raise TypeError("Expected the asset itself (with 'id' and 'url'), not a bare URL.")
    return asset_id


def _form_encode(text: str) -> str:
    return "".join(
        ch
        if ch in _FORM_SAFE
        else _FORM_SPACE
        if ch == _SPACE
        else "".join(f"%{b:02X}" for b in ch.encode())
        for ch in text
    )


def _set_param(pairs: Pairs, key: str, value: str) -> None:
    """``URLSearchParams.set``: replace the first occurrence, drop the rest, or append."""
    for i, (existing, _) in enumerate(pairs):
        if existing == key:
            pairs[i] = (key, value)
            pairs[i + 1 :] = [p for p in pairs[i + 1 :] if p[0] != key]
            return
    pairs.append((key, value))


def _with_params(base: str, updates: Pairs, *, sort: bool) -> str:
    parts = urlsplit(base)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    for key, value in updates:
        _set_param(pairs, key, value)
    if sort:
        pairs.sort(key=lambda pair: pair[0])  # stable, like URLSearchParams.sort()
    query = "&".join(f"{_form_encode(k)}={_form_encode(v)}" for k, v in pairs)
    return urlunsplit(parts._replace(query=query))


def build_url(target: Any, transform: TransformInput = None) -> str:
    """Appends transform parameters to an asset's delivery URL.

    Parameters are sorted so a transform always yields the same URL however it
    was built, which keeps CDN cache entries from splitting.
    """
    updates = [(k, to_wire(v)) for k, v in normalize_transform(transform).items()]
    return _with_params(target_url(target), updates, sort=True)


def _expiry_seconds(expires_in: int | timedelta) -> int:
    if isinstance(expires_in, timedelta):
        seconds = expires_in.total_seconds()
        if not seconds.is_integer():
            raise ValueError("expires_in must be a whole number of seconds.")
        expires_in = int(seconds)
    if isinstance(expires_in, bool) or not isinstance(expires_in, int):
        raise TypeError("expires_in must be an int (seconds) or a timedelta.")
    if expires_in <= 0:
        raise ValueError("expires_in must be positive.")
    return expires_in


def build_signed_url(
    target: Any,
    *,
    signing_secret: str | None,
    expires_in: int | timedelta,
    transform: TransformInput = None,
    now: float | None = None,
) -> str:
    """A time-limited URL for an asset in a signed folder.

    The signature is HMAC-SHA256 (hex) over ``"{id}:{exp}"`` with the project's
    URL Signing Secret, as the API reference specifies. It locks the asset and
    the expiry, not the transform: transform parameters ride along unsigned,
    so a frontend may adjust them without a new signature. (Verified against
    the live API: signing transform values makes the API reject the link.)
    """
    if not signing_secret:
        raise DreepError(_SIGNING_REQUIRED_MESSAGE)
    asset_id = target_id(target)
    expires = math.floor(time.time() if now is None else now) + _expiry_seconds(expires_in)
    payload = f"{asset_id}{t.SIGNATURE_SEPARATOR}{expires}"
    signature = hmac.new(signing_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    # exp and sig go after the sorted transform params rather than among them.
    updates = [(t.QUERY_EXPIRES, str(expires)), (t.QUERY_SIGNATURE, signature)]
    return _with_params(build_url(target, transform), updates, sort=False)
