"""Public types: parameter literals, the :class:`Transform` dict, and models.

Enum-like parameters are ``Literal`` aliases rather than ``Enum`` classes, so
plain strings work at runtime while a type checker still rejects a typo such as
``fit="squish"``.
"""

from __future__ import annotations

from typing import Literal, Protocol, TypedDict

from ._models import (
    Asset,
    BackgroundRemovedAsset,
    ConvertedDocument,
    MediaItem,
    MediaPage,
    Pagination,
    PresignedUpload,
)
from ._models_project import Folder, FolderListing, OCRResult, Preset, SavedTextAsset, Usage

__all__ = [
    "AccessControlType",
    "Asset",
    "AssetLike",
    "AudioFormat",
    "BackgroundRemovalFormat",
    "BackgroundRemovedAsset",
    "ConvertFormat",
    "ConvertedDocument",
    "DocumentFormat",
    "Fit",
    "Folder",
    "FolderListing",
    "Gravity",
    "ImageFormat",
    "MediaItem",
    "MediaPage",
    "OCRResult",
    "OutputFormat",
    "Pagination",
    "Preset",
    "PresignedUpload",
    "Radius",
    "Rotate",
    "SavedTextAsset",
    "TextFormat",
    "Transform",
    "Usage",
    "VideoCodec",
    "VideoFormat",
]

ImageFormat = Literal["jpeg", "jpg", "png", "webp", "avif", "gif", "tiff", "heic", "heif"]
VideoFormat = Literal["mp4", "webm", "mov", "hls", "m3u8", "gif"]
AudioFormat = Literal["mp3", "wav", "aac"]
#: Requesting a text format on an image or PDF runs OCR.
TextFormat = Literal["txt", "text"]
#: Requesting one of these on a Word, Excel, PowerPoint or PDF asset converts it.
DocumentFormat = Literal["pdf", "docx", "odt", "rtf", "xlsx", "ods", "csv", "pptx", "odp"]
OutputFormat = ImageFormat | VideoFormat | AudioFormat | TextFormat | DocumentFormat
#: What :meth:`Dreep.convert_document` can produce.
ConvertFormat = Literal[
    "pdf", "docx", "odt", "rtf", "xlsx", "ods", "csv", "pptx", "odp", "png", "jpeg"
]
#: Only alpha-capable formats: a JPEG cutout would lose its transparency.
BackgroundRemovalFormat = Literal["png", "webp"]

Fit = Literal["cover", "contain", "fill", "inside", "outside"]
Gravity = Literal[
    "center",
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
    "attention",
    "entropy",
]
Rotate = Literal[90, 180, 270]
#: The API accepts these four. ``libx264``/``libvpx-vp9`` appear in the
#: OpenAPI spec but are rejected by the server, so they are not offered here.
VideoCodec = Literal["h264", "vp8", "vp9", "hevc"]
#: Pixels, or ``"max"`` for a full circle or pill.
Radius = int | float | Literal["max"]
AccessControlType = Literal["public", "private", "signed"]


class Transform(TypedDict, total=False):
    """A transform, applied on the fly at delivery or before storage on upload.

    Every key is optional and an empty dict is a no-op. Which keys apply is
    enforced server-side per media type.
    """

    #: Output format. Also drives OCR (``txt``), document conversion and video
    #: thumbnail extraction.
    format: OutputFormat
    #: Pixels, max 4000.
    width: int
    #: Pixels, max 4000.
    height: int
    fit: Fit
    #: 1-100.
    quality: int
    #: Image crop anchor when resizing.
    gravity: Gravity
    #: Explicit crop as ``"left,top,width,height"`` or a 4-tuple of ints.
    crop: str | tuple[int, int, int, int]
    #: Device pixel ratio multiplier, max 3.
    dpr: float
    rotate: Rotate
    #: Gaussian blur sigma, 0.3-100.
    blur: float
    #: Hex colour without ``#``: ``fff``, ``ffffff`` or ``ffffffcc``.
    bg: str
    radius: Radius
    #: Video trim start, seconds.
    trim_start: float
    #: Video trim end, seconds.
    trim_end: float
    video_codec: VideoCodec
    fps: int
    #: PDF page to render when converting a PDF to ``png`` or ``jpeg``.
    page: int
    #: Key of a saved preset, applied instead of individual fields.
    preset: str


class AssetLike(Protocol):
    """Anything with an ``id`` and a delivery ``url``.

    Every asset-shaped model satisfies this: :class:`Asset`, :class:`MediaItem`,
    :class:`BackgroundRemovedAsset`, :class:`ConvertedDocument`.
    """

    @property
    def id(self) -> str: ...

    @property
    def url(self) -> str: ...
