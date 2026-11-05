"""Building request bodies, query strings and multipart forms from keyword args.

Wire names are derived from Python parameter names (``folder_id`` ->
``folderId``), the same rule the response models use, so no request field is
spelled out as a string anywhere. Unset (``None``) values are dropped.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import _constants as c
from ._decode import camel_case
from ._jsnum import to_wire

__all__ = [
    "check_destination",
    "check_exclusive",
    "wire_body",
    "wire_form",
    "with_wire",
]


def wire_body(**values: Any) -> dict[str, Any]:
    """A JSON body: camelCase keys, ``None`` dropped, values left typed."""
    return {camel_case(key): value for key, value in values.items() if value is not None}


def wire_form(**values: Any) -> dict[str, str]:
    """Query or multipart fields: like :func:`wire_body`, with JS-style strings."""
    return {key: to_wire(value) for key, value in wire_body(**values).items()}


def with_wire(base: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, str]:
    """Merges pre-named wire fields (e.g. a transform) with derived ones, stringified."""
    return {**{k: to_wire(v) for k, v in base.items()}, **fields}


def check_exclusive(**values: Any) -> None:
    """Raises if more than one of the named arguments is set."""
    given = [name for name, value in values.items() if value is not None]
    if len(given) > 1:
        raise ValueError(f"Pass at most one of {', '.join(values)}; got {', '.join(given)}.")


def check_destination(*, folder: str | None, key: str | None, folder_id: str | None) -> None:
    """The destination rules shared by every upload-shaped endpoint.

    ``folder`` and ``key`` are mutually exclusive, as are ``folder_id`` and
    ``folder``; a ``key`` may accompany ``folder_id`` only if it is a bare
    filename. Omitting all three targets the project's default folder.
    """
    check_exclusive(folder=folder, key=key)
    check_exclusive(folder=folder, folder_id=folder_id)
    if folder_id is not None and key is not None and c.PATH_SEPARATOR in key:
        raise ValueError("A key with a folder prefix can't be combined with folder_id.")
