"""Lenient coercion of JSON scalars into the types models declare.

A missing optional value becomes ``None``; a numeric string becomes an ``int``
(Postgres ``BIGINT`` columns arrive as strings); booleans may arrive as the
strings ``"true"``/``"false"``.
"""

from __future__ import annotations

import contextlib
import math
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

__all__ = ["opt_datetime", "opt_int", "opt_str", "to_bool", "to_int", "to_mapping"]

#: ISO-8601 "Zulu" suffix that ``fromisoformat`` rejects before Python 3.11.
_UTC_SUFFIXES: Final = ("Z", "z")
_UTC_OFFSET: Final = "+00:00"
_TRUE: Final = "true"


def opt_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def opt_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else None
    if isinstance(value, str):
        # int() first: a BIGINT string past 2**53 would lose digits through float.
        with contextlib.suppress(ValueError):
            return int(value)
        with contextlib.suppress(ValueError):
            return opt_int(float(value))
    return None


def to_int(value: Any) -> int:
    return opt_int(value) or 0


def to_bool(value: Any) -> bool:
    return value.lower() == _TRUE if isinstance(value, str) else bool(value)


def opt_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + _UTC_OFFSET if value.endswith(_UTC_SUFFIXES) else value
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def to_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
