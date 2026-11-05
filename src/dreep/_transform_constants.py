"""Transform parameter names and the server-side snapping tables.

Kept apart from the HTTP constants because they belong to one concern --
describing and canonicalising transforms -- and change for different reasons.
"""

from __future__ import annotations

from typing import Final

from ._decode import camel_case

#: Every transform key the SDK accepts, in snake_case. Must match the keys of
#: :class:`dreep.types.Transform`; a test enforces it. The *order* is
#: load-bearing: the signed keys appear in the API's canonical order, and
#: CANONICAL_PARAM_ORDER below is derived from it.
TRANSFORM_KEYS: Final = (
    "format",
    "width",
    "height",
    "fit",
    "quality",
    "gravity",
    "crop",
    "dpr",
    "rotate",
    "blur",
    "bg",
    "radius",
    "trim_start",
    "trim_end",
    "video_codec",
    "fps",
    "page",
    "preset",
)

#: The one key whose wire name isn't its camelCase: the API reads presets as `p`.
PRESET_KEY: Final = "preset"
QUERY_PRESET: Final = "p"

#: snake_case -> wire name for every transform key.
TRANSFORM_WIRE_NAMES: Final[dict[str, str]] = {
    key: QUERY_PRESET if key == PRESET_KEY else camel_case(key) for key in TRANSFORM_KEYS
}

CROP_KEY: Final = "crop"
#: Number of comma-separated values in an explicit crop: left, top, width, height.
CROP_PARTS: Final = 4
CROP_SEPARATOR: Final = ","

# Copied from the Dreep server (src/services/sharp/constants.ts) by way of the
# official Node SDK.
#
# The API snaps these parameters onto fixed breakpoints before hashing a cache
# key -- and before verifying a signed URL's signature. Signing must apply the
# identical snapping or the link 401s, so these tables are duplicated state:
# changing them on the server without changing them here silently breaks every
# signed URL that carries a transform. The pinned-signature tests catch drift.
WIDTH_BREAKPOINTS: Final = (
    16, 32, 64, 128, 256, 384, 512, 640, 750, 828, 960, 1080, 1200, 1440, 1920,
    2560, 3200, 4000,
)  # fmt: skip
QUALITY_BREAKPOINTS: Final = (50, 65, 75, 85, 95, 100)
DPR_BREAKPOINTS: Final = (1, 2, 3)

#: Keys that ride along on a signed URL without being part of the signature.
UNSIGNED_KEYS: Final = frozenset(
    {"crop", "trim_start", "trim_end", "video_codec", "fps", "page", PRESET_KEY}
)
#: Key order the API serialises canonical transform params in before signing.
#: The signature is over that exact JSON string, so this order is load-bearing.
CANONICAL_PARAM_ORDER: Final = tuple(k for k in TRANSFORM_KEYS if k not in UNSIGNED_KEYS)
#: Snapped up to the next breakpoint, so a request never gets something smaller.
SNAP_UP: Final = {"width": WIDTH_BREAKPOINTS, "height": WIDTH_BREAKPOINTS, "dpr": DPR_BREAKPOINTS}
#: Snapped to the nearest breakpoint: overshooting quality costs bytes for nothing.
SNAP_NEAREST: Final = {"quality": QUALITY_BREAKPOINTS}

QUERY_EXPIRES: Final = "exp"
QUERY_SIGNATURE: Final = "sig"

#: The format that makes the fetch endpoint run OCR and return plain text.
TEXT_FORMAT: Final = "txt"
TEXT_TRANSFORM: Final = {"format": TEXT_FORMAT}
