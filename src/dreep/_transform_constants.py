"""Transform parameter names and signed-URL query keys.

Kept apart from the HTTP constants because they belong to one concern --
describing transforms -- and change for different reasons.
"""

from __future__ import annotations

from typing import Final

from ._decode import camel_case

#: Every transform key the SDK accepts, in snake_case. Must match the keys of
#: :class:`dreep.types.Transform`; a test enforces it.
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

#: The signed payload is "{asset id}:{expiry}".
SIGNATURE_SEPARATOR: Final = ":"
QUERY_EXPIRES: Final = "exp"
QUERY_SIGNATURE: Final = "sig"

#: The format that makes the fetch endpoint run OCR and return plain text.
TEXT_FORMAT: Final = "txt"
TEXT_TRANSFORM: Final = {"format": TEXT_FORMAT}
