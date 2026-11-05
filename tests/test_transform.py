"""Transform validation and wire-name mapping."""

from __future__ import annotations

import typing

import pytest

from dreep import _transform_constants as t
from dreep._transform import normalize_transform, transform_body
from dreep.types import Transform


def test_transform_keys_match_the_public_typeddict() -> None:
    assert set(t.TRANSFORM_KEYS) == set(typing.get_type_hints(Transform))


def test_wire_names_are_camel_case_except_preset() -> None:
    assert t.TRANSFORM_WIRE_NAMES["trim_start"] == "trimStart"
    assert t.TRANSFORM_WIRE_NAMES["video_codec"] == "videoCodec"
    assert t.TRANSFORM_WIRE_NAMES["preset"] == "p"


def test_normalize_maps_names_drops_none_and_formats_crop() -> None:
    wire = normalize_transform(
        {"width": 400, "trim_start": 1.5, "crop": (10, 20, 100, 100), "fit": None}
    )
    assert wire == {"width": 400, "trimStart": 1.5, "crop": "10,20,100,100"}


def test_normalize_rejects_unknown_keys() -> None:
    with pytest.raises(TypeError, match="widht"):
        normalize_transform({"widht": 400})


@pytest.mark.parametrize("bad", [(1, 2, 3), "not-a-dict"])
def test_normalize_rejects_bad_shapes(bad: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        normalize_transform({"crop": bad} if isinstance(bad, tuple) else bad)  # type: ignore[arg-type]


def test_empty_transform_is_a_no_op() -> None:
    assert normalize_transform(None) == {}
    assert normalize_transform({}) == {}


def test_transform_body_spells_out_preset() -> None:
    assert transform_body({"preset": "thumb", "width": 10}) == {"preset": "thumb", "width": 10}
    assert transform_body(None) is None
