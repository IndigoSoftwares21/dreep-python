"""Project-level response models: folders, presets, usage and OCR results."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from ._decode import ApiModel, raw_field

__all__ = ["Folder", "FolderListing", "OCRResult", "Preset", "SavedTextAsset", "Usage"]


@dataclass(frozen=True, slots=True, kw_only=True)
class Folder(ApiModel):
    id: str
    name: str | None = None
    slug: str | None = None
    #: Slug path from the project root, e.g. ``avatars/2024/q1``.
    path: str | None = None
    parent_id: str | None = None
    #: ``"public"``, ``"private"`` or ``"signed"``. Set on root folders only;
    #: nested folders inherit it from the root of their tree.
    access_control_type: str | None = None
    #: Default link lifetime for a signed folder, in seconds.
    default_expiry_seconds: int | None = None
    raw: Mapping[str, Any] = raw_field()


@dataclass(frozen=True, slots=True, kw_only=True)
class FolderListing(ApiModel):
    """Folders, plus the folder the ``path``/``parent_id`` filter named."""

    folders: list[Folder] = field(default_factory=list)
    current_folder: Folder | None = None
    raw: Mapping[str, Any] = raw_field()

    def __iter__(self) -> Iterator[Folder]:
        return iter(self.folders)

    def __len__(self) -> int:
        return len(self.folders)


@dataclass(frozen=True, slots=True, kw_only=True)
class Preset(ApiModel):
    """A named transform. Apply it by ``key``; delete it by ``id``."""

    id: str
    key: str | None = None
    name: str | None = None
    params: Mapping[str, Any] = field(default_factory=dict)
    raw: Mapping[str, Any] = raw_field()


@dataclass(frozen=True, slots=True, kw_only=True)
class Usage(ApiModel):
    """Storage consumed and object counts for the project."""

    storage_bytes: int = 0
    image_count: int = 0
    file_count: int = 0
    folder_count: int = 0
    raw: Mapping[str, Any] = raw_field()


@dataclass(frozen=True, slots=True, kw_only=True)
class SavedTextAsset(ApiModel):
    """The ``.txt`` asset OCR wrote, when a destination folder was given."""

    id: str
    storage_key: str | None = None
    raw: Mapping[str, Any] = raw_field()


@dataclass(frozen=True, slots=True, kw_only=True)
class OCRResult(ApiModel):
    #: The full extracted text.
    text: str | None = None
    #: Line blocks with bounding boxes. Empty unless ``include_blocks=True``.
    blocks: list[Mapping[str, Any]] = field(default_factory=list)
    #: Set only when a destination folder was given.
    saved_asset: SavedTextAsset | None = None
    raw: Mapping[str, Any] = raw_field()
