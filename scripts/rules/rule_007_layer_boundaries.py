"""RULE-007: separation of concerns -- each layer imports only what it may.

"Client/transport communicates. Models describe. Domain logic decides.
Constants define." The SDK's layers, innermost first:

* **pure** -- constants, errors, models, decoding, transforms, URLs, params:
  no I/O libraries at all, so they are trivially testable.
* **http** -- request description and retry policy: may use ``httpx`` types.
* **client** -- the only layer that creates an HTTP client or sleeps.

A pure module importing ``httpx``/``anyio``, or anything outside the client
layer constructing an ``httpx.Client``, is a layering bug.
"""

from __future__ import annotations

import ast
import re
from typing import ClassVar, Final

from rules.base import ERROR, BaseRule, FileContext, Severity, Violation

IO_LIBRARIES: Final = frozenset({"httpx", "anyio", "requests", "aiohttp", "urllib3"})
HTTP_LAYER: Final = re.compile(r"^_(http|retry|config)$")
CLIENT_LAYER: Final = re.compile(r"^_(async|sync)_\w+$|^_client$")
#: Pure modules that may still touch anyio: the file streamer offloads reads.
IO_EXCEPTIONS: Final = frozenset({"_files"})
CLIENT_CONSTRUCTORS: Final = frozenset({"Client", "AsyncClient"})


def _imported_roots(tree: ast.Module) -> list[tuple[str, int]]:
    roots = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots += [(alias.name.split(".")[0], node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.append((node.module.split(".")[0], node.lineno))
    return roots


class LayerBoundaries(BaseRule):
    id: ClassVar[str] = "RULE-007"
    category: ClassVar[str] = "Layer Boundaries"
    severity: ClassVar[Severity] = ERROR
    description: ClassVar[str] = "I/O libraries only in the http/client layers"
    remediation: ClassVar[str] = "Move the I/O into the client layer and pass plain data inward."

    def check(self, file: FileContext) -> list[Violation]:
        if not file.is_package:
            return []
        module = file.module
        in_client = bool(CLIENT_LAYER.match(module))
        may_import_io = in_client or HTTP_LAYER.match(module) or module in IO_EXCEPTIONS
        violations = [
            self.violation(file, line, f"Pure module imports I/O library {root!r}.")
            for root, line in _imported_roots(file.tree)
            if root in IO_LIBRARIES and not may_import_io
        ]
        if not in_client:
            violations += [
                self.violation(
                    file, node.lineno, "HTTP client constructed outside the client layer."
                )
                for node in ast.walk(file.tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in CLIENT_CONSTRUCTORS
            ]
        return violations


RULE = LayerBoundaries()
