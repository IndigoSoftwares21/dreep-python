"""Validating transforms and mapping them onto the API's wire names."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import _transform_constants as t
from ._jsnum import to_wire
from .types import Transform

__all__ = ["TransformInput", "normalize_transform", "transform_body"]

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
