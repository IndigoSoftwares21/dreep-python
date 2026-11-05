"""Validating transforms and producing the canonical form the API signs.

See :mod:`dreep._transform_constants` for why the snapping tables exist and
why their values and key order must match the server exactly.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import _transform_constants as t
from ._jsnum import js_json_value, to_wire
from .types import Transform

__all__ = [
    "canonical_transform_json",
    "normalize_transform",
    "snap_nearest",
    "snap_up",
    "transform_body",
]

TransformInput = Transform | Mapping[str, Any] | None


def normalize_transform(transform: TransformInput) -> dict[str, Any]:
    """Validates a transform's keys and maps them onto wire names.

    Unknown keys raise rather than being dropped: a typo such as ``widht``
    would otherwise silently deliver the untransformed original.
    """
    if not transform:
        return {}
    if not isinstance(transform, Mapping):
        raise TypeError(f"transform must be a dict, not {type(transform).__name__}.")
    unknown = sorted(set(transform) - set(t.TRANSFORM_KEYS))
    if unknown:
        valid = ", ".join(t.TRANSFORM_KEYS)
        raise TypeError(f"Unknown transform parameter(s): {', '.join(unknown)}. Valid: {valid}.")
    return {
        t.TRANSFORM_WIRE_NAMES[key]: _crop(value) if key == t.CROP_KEY else value
        for key, value in transform.items()
        if value is not None
    }


def _crop(value: Any) -> str:
    if isinstance(value, str):
        return value
    parts = tuple(value)
    if len(parts) != t.CROP_PARTS:
        raise ValueError("crop must be 'left,top,width,height' or a 4-tuple of ints.")
    return t.CROP_SEPARATOR.join(to_wire(part) for part in parts)


def transform_body(transform: TransformInput) -> dict[str, Any] | None:
    """A transform as a nested JSON object, for the confirm endpoint.

    Unlike upload (flat multipart fields, preset as ``p``), confirm takes the
    transform as an object whose preset key is spelled out as ``preset``.
    """
    wire = normalize_transform(transform)
    if t.QUERY_PRESET in wire:
        wire[t.PRESET_KEY] = wire.pop(t.QUERY_PRESET)
    return wire or None


def snap_up(value: float, breakpoints: tuple[int, ...]) -> int:
    """Rounds up to the next breakpoint; anything above the top one gets the top."""
    return next((b for b in breakpoints if value <= b), breakpoints[-1])


def snap_nearest(value: float, breakpoints: tuple[int, ...]) -> int:
    """Rounds to the closest breakpoint. Ties keep the lower one, as the server does."""
    nearest = breakpoints[0]
    for breakpoint in breakpoints[1:]:
        if abs(breakpoint - value) < abs(nearest - value):
            nearest = breakpoint
    return nearest


def _snapped(key: str, value: Any) -> Any:
    rule = snap_up if key in t.SNAP_UP else snap_nearest if key in t.SNAP_NEAREST else None
    if rule is None:
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"transform[{key!r}] must be a number, not {value!r}.")
    return rule(value, {**t.SNAP_UP, **t.SNAP_NEAREST}[key])


def canonical_transform_json(transform: TransformInput) -> str | None:
    """The params string the API verifies a signed URL against, or ``None``.

    Only parameters that change the cached variant are signed (format, size,
    fit, quality, gravity, dpr, rotate, blur, bg, radius) plus the preset. Crop,
    trim, codec, fps and page ride along unsigned, as on the server.
    """
    normalize_transform(transform)  # same key validation as everywhere else
    source: Mapping[str, Any] = transform or {}
    entries = [
        (key, _snapped(key, source[key]))
        for key in t.CANONICAL_PARAM_ORDER
        if source.get(key) is not None
    ]
    if source.get(t.PRESET_KEY) is not None:
        entries.append((t.QUERY_PRESET, source[t.PRESET_KEY]))
    if not entries:
        return None
    return "{" + ",".join(f"{js_json_value(k)}:{js_json_value(v)}" for k, v in entries) + "}"
