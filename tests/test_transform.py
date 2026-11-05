"""Transform validation, breakpoint snapping and canonical JSON."""

from __future__ import annotations

import typing

import pytest

from dreep import _transform_constants as t
from dreep._transform import (
    canonical_transform_json,
    normalize_transform,
    snap_nearest,
    snap_up,
    transform_body,
)
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
    assert canonical_transform_json(None) is None


def test_transform_body_spells_out_preset() -> None:
    assert transform_body({"preset": "thumb", "width": 10}) == {"preset": "thumb", "width": 10}
    assert transform_body(None) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1, 16), (16, 16), (17, 32), (803, 828), (828, 828), (3999.5, 4000), (9999, 4000)],
)
def test_snap_up_width(value: float, expected: int) -> None:
    assert snap_up(value, t.WIDTH_BREAKPOINTS) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1, 50), (57.5, 50), (57.6, 65), (70, 65), (82, 85), (100, 100), (150, 100)],
)
def test_snap_nearest_quality_keeps_the_lower_on_ties(value: float, expected: int) -> None:
    assert snap_nearest(value, t.QUALITY_BREAKPOINTS) == expected


def test_canonical_json_snaps_orders_and_compacts() -> None:
    transform: Transform = {
        "radius": "max",
        "bg": "ffffff",
        "blur": 2.5,
        "rotate": 90,
        "dpr": 1.5,
        "gravity": "north",
        "quality": 82,
        "fit": "cover",
        "height": 600,
        "width": 803,
        "format": "webp",
    }
    assert canonical_transform_json(transform) == (
        '{"format":"webp","width":828,"height":640,"fit":"cover","quality":85,'
        '"gravity":"north","dpr":2,"rotate":90,"blur":2.5,"bg":"ffffff","radius":"max"}'
    )


def test_canonical_json_appends_preset_and_ignores_unsigned_params() -> None:
    transform: Transform = {"preset": "thumbnail", "width": 200, "crop": "1,2,3,4", "fps": 30}
    assert canonical_transform_json(transform) == '{"width":256,"p":"thumbnail"}'


def test_canonical_json_rejects_non_numeric_sizes() -> None:
    with pytest.raises(TypeError, match="width"):
        canonical_transform_json({"width": "400"})
