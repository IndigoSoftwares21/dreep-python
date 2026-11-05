"""Operations that send or manage media: uploads, processing, listing, deletion.

Each builder validates its arguments, describes the HTTP request, and pairs it
with the parser for the response. Builders never perform I/O -- that is the
clients' job -- so the sync and async clients share every one of them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import _constants as c
from . import _transform_constants as t
from ._files import PreparedFile
from ._http import Operation, Request, discard
from ._models import Asset, BackgroundRemovedAsset, ConvertedDocument, MediaPage, PresignedUpload
from ._models_project import OCRResult
from ._params import check_destination, check_exclusive, wire_body, wire_form, with_wire
from ._transform import normalize_transform, transform_body
from .types import Transform

__all__ = [
    "op_confirm_upload",
    "op_convert_document",
    "op_delete_media",
    "op_extract_text",
    "op_list_media",
    "op_presign_upload",
    "op_remove_background",
    "op_upload",
]


def _unwrap_asset(payload: Any) -> Any:
    """bg-remove and convert wrap their result as ``{"asset": {...}}``."""
    if isinstance(payload, Mapping) and isinstance(payload.get(c.ASSET_WRAPPER), Mapping):
        return payload[c.ASSET_WRAPPER]
    return payload


def _upload_request(path: str, file: PreparedFile, form: dict[str, str]) -> Request:
    return Request(c.Method.POST, path, form=form, file=file, is_upload=True)


def op_upload(
    file: PreparedFile,
    *,
    folder: str | None,
    key: str | None,
    folder_id: str | None,
    auto_create_folders: bool | None,
    transform: Transform | None,
    preset_key: str | None,
) -> Operation[Asset]:
    check_destination(folder=folder, key=key, folder_id=folder_id)
    # Upload reads its preset from `p`, the name the fetch endpoint uses -- not
    # the `presetKey` presign takes -- so it travels inside the transform.
    merged: dict[str, Any] = dict(transform or {})
    if preset_key is not None:
        merged[t.PRESET_KEY] = preset_key
    form = with_wire(
        normalize_transform(merged),
        wire_form(
            folder=folder, key=key, folder_id=folder_id, auto_create_folders=auto_create_folders
        ),
    )
    return Operation(_upload_request(c.Path.UPLOAD, file, form), Asset._from_api)


def op_presign_upload(
    *,
    content_type: str,
    size_bytes: int,
    filename: str | None,
    folder: str | None,
    key: str | None,
    folder_id: str | None,
    auto_create_folders: bool | None,
    format: str | None,
    preset_key: str | None,
    content_hash: str | None,
) -> Operation[PresignedUpload]:
    check_destination(folder=folder, key=key, folder_id=folder_id)
    if not content_type:
        raise ValueError("content_type is required.")
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes <= 0:
        raise ValueError("size_bytes must be a positive int -- the file's exact size.")
    body = wire_body(
        content_type=content_type,
        size_bytes=size_bytes,
        filename=filename,
        folder=folder,
        key=key,
        folder_id=folder_id,
        auto_create_folders=auto_create_folders,
        format=format,
        preset_key=preset_key,
        content_hash=content_hash,
    )
    request = Request(c.Method.POST, c.Path.UPLOAD_PRESIGN, json=body)
    return Operation(request, PresignedUpload._from_api)


def op_confirm_upload(
    upload_id: str, *, transform: Transform | None, preset_key: str | None
) -> Operation[Asset]:
    body = wire_body(transform=transform_body(transform), preset_key=preset_key)
    request = Request(c.Method.POST, c.Path.upload_confirm(upload_id), json=body)
    return Operation(request, Asset._from_api)


def op_list_media(
    *,
    page: int | None,
    limit: int | None,
    folder: str | None,
    folder_id: str | None,
    recursive: bool | None,
) -> Operation[MediaPage]:
    check_exclusive(folder=folder, folder_id=folder_id)
    query = wire_form(
        page=page, limit=limit, folder=folder, folder_id=folder_id, recursive=recursive
    )
    return Operation(Request(c.Method.GET, c.Path.MEDIA, query=query), MediaPage._from_api)


def op_delete_media(media_id: str) -> Operation[None]:
    return Operation(Request(c.Method.DELETE, c.Path.media(media_id)), discard)


def op_remove_background(
    file: PreparedFile,
    *,
    format: str | None,
    folder: str | None,
    folder_id: str | None,
    auto_create_folders: bool | None,
) -> Operation[BackgroundRemovedAsset]:
    check_destination(folder=folder, key=None, folder_id=folder_id)
    form = wire_form(
        format=format, folder=folder, folder_id=folder_id, auto_create_folders=auto_create_folders
    )
    return Operation(
        _upload_request(c.Path.BG_REMOVE, file, form),
        lambda payload: BackgroundRemovedAsset._from_api(_unwrap_asset(payload)),
    )


def op_extract_text(
    file: PreparedFile,
    *,
    folder: str | None,
    folder_id: str | None,
    auto_create_folders: bool | None,
    include_blocks: bool | None,
) -> Operation[OCRResult]:
    check_destination(folder=folder, key=None, folder_id=folder_id)
    form = wire_form(
        folder=folder,
        folder_id=folder_id,
        auto_create_folders=auto_create_folders,
        include_blocks=include_blocks,
    )
    return Operation(_upload_request(c.Path.OCR, file, form), OCRResult._from_api)


def op_convert_document(
    file: PreparedFile,
    *,
    format: str,
    page: int | None,
    key: str | None,
    folder: str | None,
    folder_id: str | None,
    auto_create_folders: bool | None,
) -> Operation[ConvertedDocument]:
    if not format:
        raise ValueError("format is required.")
    check_destination(folder=folder, key=key, folder_id=folder_id)
    form = wire_form(
        format=format,
        page=page,
        key=key,
        folder=folder,
        folder_id=folder_id,
        auto_create_folders=auto_create_folders,
    )
    return Operation(
        _upload_request(c.Path.CONVERT, file, form),
        lambda payload: ConvertedDocument._from_api(_unwrap_asset(payload)),
    )
