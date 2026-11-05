"""Asset-shaped response models: things that live in storage and have a URL.

Each model is a frozen, slotted dataclass with snake_case attributes. Decoding
is declarative (see :mod:`dreep._decode`): a field's wire name is the camelCase
of its attribute unless ``wire(...)`` says otherwise, and its type decides the
coercion. Every model keeps the undecoded payload in ``raw``, so a field the API
adds before the SDK models it is still reachable without an upgrade.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ._decode import ApiModel, raw_field, wire

__all__ = [
    "Asset",
    "BackgroundRemovedAsset",
    "ConvertedDocument",
    "MediaItem",
    "MediaPage",
    "Pagination",
    "PresignedUpload",
]

_READY = "ready"


@dataclass(frozen=True, slots=True, kw_only=True)
class Asset(ApiModel):
    """A stored asset, as returned by upload and confirm."""

    id: str
    #: Ready-to-use delivery URL, extension included.
    url: str
    original_filename: str | None = None
    mimetype: str | None = None
    #: Coerced to ``int``; the API sends it as a string (Postgres ``BIGINT``).
    size_bytes: int = 0
    status: str | None = None
    #: Images only.
    format: str | None = None
    #: Images only.
    width: int | None = None
    #: Images only.
    height: int | None = None
    folder_id: str | None = None
    #: Slug path of the folder the asset lives in.
    folder: str | None = None
    project_id: str | None = None
    created_at: datetime | None = None
    raw: Mapping[str, Any] = raw_field()


@dataclass(frozen=True, slots=True, kw_only=True)
class MediaItem(ApiModel):
    """One entry of a media listing -- a lighter shape than :class:`Asset`."""

    id: str
    url: str
    filename: str | None = None
    #: MIME type, e.g. ``image/webp``.
    mimetype: str | None = field(default=None, metadata=wire("type"))
    size_bytes: int = 0
    #: ``"image"`` or ``"file"``.
    asset_type: str | None = None
    folder_id: str | None = None
    folder: str | None = None
    created_at: datetime | None = None
    raw: Mapping[str, Any] = raw_field()


@dataclass(frozen=True, slots=True, kw_only=True)
class Pagination(ApiModel):
    page: int = 0
    limit: int = 0
    #: Total assets matching the filter, across all pages.
    total: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class MediaPage(ApiModel):
    """One page of a media listing. Iterating it yields its assets."""

    assets: list[MediaItem] = field(default_factory=list)
    pagination: Pagination = field(default_factory=Pagination)
    raw: Mapping[str, Any] = raw_field()

    def __iter__(self) -> Iterator[MediaItem]:
        return iter(self.assets)

    def __len__(self) -> int:
        return len(self.assets)


@dataclass(frozen=True, slots=True, kw_only=True)
class PresignedUpload(ApiModel):
    """A presigned upload, before its bytes have been PUT to storage."""

    #: Pass to ``confirm_upload`` once the bytes are in place.
    id: str
    #: Single-use, valid for about ten minutes. ``None`` when ``already_exists``.
    upload_url: str | None = None
    content_type: str | None = None
    #: ``True`` when ``content_hash`` matched content Dreep already stores.
    already_exists: bool = False
    raw: Mapping[str, Any] = raw_field()


@dataclass(frozen=True, slots=True, kw_only=True)
class BackgroundRemovedAsset(ApiModel):
    """A cutout with its alpha channel kept. Serve it on a colour with ``bg``."""

    id: str
    url: str
    storage_key: str | None = None
    format: str | None = None
    width: int | None = None
    height: int | None = None
    size_bytes: int = 0
    raw: Mapping[str, Any] = raw_field()


@dataclass(frozen=True, slots=True, kw_only=True)
class ConvertedDocument(ApiModel):
    """A converted document, saved as a new asset.

    A very long conversion comes back with ``status == "processing"``; its
    ``url`` answers 202 until it is ready.
    """

    id: str
    url: str
    #: The original name with the new extension, e.g. ``contract.pdf``.
    filename: str | None = None
    format: str | None = None
    mimetype: str | None = None
    #: ``0`` while still processing.
    size_bytes: int = 0
    status: str | None = None
    folder_id: str | None = None
    raw: Mapping[str, Any] = raw_field()

    @property
    def is_ready(self) -> bool:
        return self.status == _READY
