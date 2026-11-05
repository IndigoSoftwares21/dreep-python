"""js_number must render numbers byte-for-byte like JavaScript's String(n)."""

from __future__ import annotations

import pytest

from dreep._jsnum import js_number, to_wire

# Expected values are what `String(n)` prints in any ECMAScript engine.
JS_CASES = [
    (0, "0"),
    (-0.0, "0"),
    (2.0, "2"),
    (1.5, "1.5"),
    (-1.5, "-1.5"),
    (100, "100"),
    (100.0, "100"),
    (0.1 + 0.2, "0.30000000000000004"),
    (0.000001, "0.000001"),
    (0.0000001, "1e-7"),
    (1.2345e-7, "1.2345e-7"),
    (2.5e-5, "0.000025"),
    (123456789012345680000.0, "123456789012345680000"),
    (1e21, "1e+21"),
    (1.5e300, "1.5e+300"),
    (5e-324, "5e-324"),
    (12345.678, "12345.678"),
    (10**21, "1e+21"),
    (2**53, "9007199254740992"),
]


@pytest.mark.parametrize(("value", "expected"), JS_CASES)
def test_js_number_matches_javascript(value: float, expected: str) -> None:
    assert js_number(value) == expected


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_js_number_rejects_non_finite(value: float) -> None:
    with pytest.raises(ValueError, match="non-finite"):
        js_number(value)


def test_js_number_rejects_booleans() -> None:
    with pytest.raises(TypeError):
        js_number(True)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, "true"), (False, "false"), (3, "3"), (2.0, "2"), ("webp", "webp")],
)
def test_to_wire(value: object, expected: str) -> None:
    assert to_wire(value) == expected


def test_to_wire_rejects_unsupported_types() -> None:
    with pytest.raises(TypeError, match="Unsupported"):
        to_wire([1, 2])
