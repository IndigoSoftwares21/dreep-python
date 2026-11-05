"""Rendering values exactly as JavaScript does.

The API is a JavaScript service that reads query parameters and form fields
as JavaScript renders values. A Python value rendered differently -- ``2.0``
instead of ``2``, ``True`` instead of ``true`` -- would split CDN cache keys or
fail validation. Everything that becomes a wire string goes through here.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Final

__all__ = ["js_number", "to_wire"]

#: ECMAScript switches to exponent notation at 10**21 and below 10**-6.
_MAX_PLAIN_EXPONENT: Final = 21
_MIN_PLAIN_EXPONENT: Final = -6
_ZERO: Final = "0"
_TRUE: Final = "true"
_FALSE: Final = "false"


def js_number(value: float) -> str:
    """Formats a number exactly as JavaScript's ``String(number)`` does.

    Python's ``repr`` and JavaScript both emit the *shortest* digit string that
    round-trips, so only the layout differs: where the decimal point goes and
    when to use exponent notation. This is ECMAScript ``Number::toString``.
    """
    if isinstance(value, bool):
        raise TypeError("Booleans are not numbers here.")
    if isinstance(value, int) and abs(value) < 10**_MAX_PLAIN_EXPONENT:
        return str(value)
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"Cannot encode non-finite number {value!r}.")
    if x == 0:
        return _ZERO  # -0 too, as in JavaScript
    if x < 0:
        return "-" + js_number(-x)
    digits, n = _shortest_digits(x)
    return _layout(digits, n)


def _shortest_digits(x: float) -> tuple[str, int]:
    """``(s, n)`` with ``x == 0.s * 10**n`` and ``s`` free of trailing zeros."""
    _, digit_tuple, exponent = Decimal(repr(x)).as_tuple()
    assert isinstance(exponent, int)  # finite input, so never 'n'/'N'/'F'
    digits = list(digit_tuple)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    return "".join(map(str, digits)), exponent + len(digits)


def _layout(s: str, n: int) -> str:
    k = len(s)
    if k <= n <= _MAX_PLAIN_EXPONENT:
        return s + _ZERO * (n - k)
    if 0 < n <= _MAX_PLAIN_EXPONENT:
        return f"{s[:n]}.{s[n:]}"
    if _MIN_PLAIN_EXPONENT < n <= 0:
        return "0." + _ZERO * (-n) + s
    e = n - 1
    mantissa = s if k == 1 else f"{s[0]}.{s[1:]}"
    return f"{mantissa}e{'+' if e >= 0 else '-'}{abs(e)}"


def to_wire(value: Any) -> str:
    """A value as JavaScript's ``String(value)`` renders it, for queries and forms."""
    if isinstance(value, bool):
        return _TRUE if value else _FALSE
    if isinstance(value, (int, float)):
        return js_number(value)
    if isinstance(value, str):
        return value
    raise TypeError(f"Unsupported parameter value {value!r} ({type(value).__name__}).")
