"""Declarative JSON -> dataclass decoding.

A model declares its fields once, with Python types; this module derives each
field's wire name (``size_bytes`` -> ``sizeBytes``) and coerces the value by
its annotation. Nothing else in the SDK spells out a response key, so a field
exists in exactly one place.

Decoding is lenient by design: a missing *optional* field becomes ``None`` (or
an empty container), a numeric string becomes an ``int`` (Postgres ``BIGINT``
columns arrive as strings), and only a missing *required* string -- an ``id``
or a ``url``, without which the object is useless -- raises.
"""

from __future__ import annotations

import dataclasses
import types
import typing
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any, TypeGuard, TypeVar, Union

from ._coerce import opt_datetime, opt_int, opt_str, to_bool, to_int, to_mapping
from ._errors import DreepError

__all__ = ["ApiModel", "camel_case", "raw_field", "wire"]

#: Field metadata key overriding the derived wire name.
_WIRE: typing.Final = "wire"
#: Name of the field that receives the undecoded payload.
_RAW_FIELD: typing.Final = "raw"

M = TypeVar("M", bound="ApiModel")
_Coerce = Callable[[Any], Any]


def camel_case(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.title() for part in rest)


def wire(name: str) -> dict[str, str]:
    """Field metadata for a key whose wire name isn't the camelCase of the field."""
    return {_WIRE: name}


def _unexpected(detail: str) -> DreepError:
    return DreepError(f"Unexpected response from the API: {detail}.")


# --------------------------------------------------------------------------- #
# Annotation -> coercer
# --------------------------------------------------------------------------- #

_SCALARS: dict[Any, _Coerce] = {
    int: to_int,
    bool: to_bool,
    int | None: opt_int,
    str | None: opt_str,
    datetime | None: opt_datetime,
    Mapping[str, Any]: to_mapping,
}


def _required_str(key: str) -> _Coerce:
    def coerce(value: Any) -> str:
        if not isinstance(value, str) or not value:
            raise _unexpected(f"missing {key!r}")
        return value

    return coerce


def _optional_of(hint: Any) -> Any | None:
    """``X`` for ``X | None`` (either spelling), else ``None``."""
    if typing.get_origin(hint) in (Union, types.UnionType):
        args = [a for a in typing.get_args(hint) if a is not type(None)]
        if len(args) == 1 and len(typing.get_args(hint)) == 2:
            return args[0]
    return None


def _is_model(hint: Any) -> TypeGuard[type[ApiModel]]:
    return isinstance(hint, type) and issubclass(hint, ApiModel)


def _coercer(key: str, hint: Any) -> _Coerce:
    if hint is str:
        return _required_str(key)
    if hint in _SCALARS:
        return _SCALARS[hint]
    if _is_model(hint):  # a required nested model: decode whatever is there
        required = hint._from_api
        return lambda v: required(v if isinstance(v, Mapping) else {})
    inner = _optional_of(hint)
    if _is_model(inner):
        nested = inner._from_api
        return lambda v: nested(v) if isinstance(v, Mapping) else None
    if typing.get_origin(hint) is list:
        (item,) = typing.get_args(hint)
        item_coerce: _Coerce = (
            item._from_api if _is_model(item) else (lambda v: v)  # Mapping items pass through
        )
        return lambda v: (
            [item_coerce(x) for x in v if isinstance(x, Mapping)] if isinstance(v, list) else []
        )
    raise TypeError(f"No decoder for {key!r}: {hint!r}")  # a programming error, caught by tests


# --------------------------------------------------------------------------- #
# Base class
# --------------------------------------------------------------------------- #


class ApiModel:
    """Base for response models. Subclasses are frozen, slotted dataclasses."""

    __slots__ = ()

    @classmethod
    def _from_api(cls: type[M], data: Any) -> M:
        if not isinstance(data, Mapping):
            raise _unexpected(f"expected {cls.__name__} to be an object")
        plan = _plan(cls)
        values = {name: coerce(data.get(key)) for name, key, coerce in plan.fields}
        if plan.has_raw:
            values[_RAW_FIELD] = data
        return cls(**values)


@dataclasses.dataclass(frozen=True)
class _Plan:
    #: (attribute, wire key, coercer) for every decoded field.
    fields: tuple[tuple[str, str, _Coerce], ...]
    has_raw: bool


_PLANS: dict[type, _Plan] = {}


def _plan(cls: type[ApiModel]) -> _Plan:
    """How to decode ``cls``, worked out from its annotations once and cached."""
    if cls not in _PLANS:
        hints = typing.get_type_hints(cls)
        all_fields = dataclasses.fields(cls)  # type: ignore[arg-type]  # models are dataclasses
        decoded = tuple(
            (f.name, key, _coercer(key, hints[f.name]))
            for f in all_fields
            if f.name != _RAW_FIELD
            for key in [f.metadata.get(_WIRE, camel_case(f.name))]
        )
        _PLANS[cls] = _Plan(decoded, any(f.name == _RAW_FIELD for f in all_fields))
    return _PLANS[cls]


def raw_field() -> Any:
    """The ``raw`` field every model carries: the undecoded payload."""
    return dataclasses.field(default_factory=dict, repr=False, compare=False)
