"""Operations on project resources: folders, presets and usage.

Like :mod:`dreep._operations_media`, these only describe requests; the clients
send them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import _constants as c
from ._errors import DreepError
from ._http import Operation, Request, discard
from ._models_project import Folder, FolderListing, Preset, Usage
from ._params import check_exclusive, wire_body, wire_form
from ._transform import normalize_transform
from .types import AccessControlType, Transform

__all__ = [
    "op_create_folder",
    "op_create_preset",
    "op_delete_preset",
    "op_get_usage",
    "op_list_folders",
    "op_list_presets",
]


def _presets(payload: Any) -> list[Preset]:
    items = payload.get(c.PRESETS_WRAPPER) if isinstance(payload, Mapping) else payload
    if not isinstance(items, list):
        raise DreepError("Unexpected response from the API: expected a list of presets.")
    return [Preset._from_api(item) for item in items]


def op_create_folder(
    *,
    name: str | None,
    path: str | None,
    parent_id: str | None,
    parent_path: str | None,
    access_control_type: AccessControlType | None,
    default_expiry_seconds: int | None,
) -> Operation[Folder]:
    if (name is None) == (path is None):
        raise ValueError("Pass exactly one of name or path.")
    if path is not None and (parent_id is not None or parent_path is not None):
        raise ValueError("path can't be combined with parent_id or parent_path.")
    check_exclusive(parent_id=parent_id, parent_path=parent_path)
    body = wire_body(
        name=name,
        path=path,
        parent_id=parent_id,
        parent_path=parent_path,
        access_control_type=access_control_type,
        default_expiry_seconds=default_expiry_seconds,
    )
    return Operation(Request(c.Method.POST, c.Path.FOLDERS, json=body), Folder._from_api)


def op_list_folders(
    *, path: str | None, parent_id: str | None, root_only: bool
) -> Operation[FolderListing]:
    check_exclusive(path=path, parent_id=parent_id, root_only=root_only or None)
    query = wire_form(path=path, parent_id=c.ROOT_PARENT_ID if root_only else parent_id)
    return Operation(Request(c.Method.GET, c.Path.FOLDERS, query=query), FolderListing._from_api)


def op_create_preset(*, key: str, name: str, transform: Transform) -> Operation[Preset]:
    if not key or not name:
        raise ValueError("key and name are required.")
    wire = normalize_transform(transform)
    if not wire:
        raise ValueError("A preset needs a non-empty transform.")
    body = {**wire_body(key=key, name=name), **wire}
    return Operation(Request(c.Method.POST, c.Path.PRESETS, json=body), Preset._from_api)


def op_list_presets() -> Operation[list[Preset]]:
    return Operation(Request(c.Method.GET, c.Path.PRESETS), _presets)


def op_delete_preset(preset_id: str) -> Operation[None]:
    return Operation(Request(c.Method.DELETE, c.Path.preset(preset_id)), discard)


def op_get_usage() -> Operation[Usage]:
    return Operation(Request(c.Method.GET, c.Path.USAGE), Usage._from_api)
