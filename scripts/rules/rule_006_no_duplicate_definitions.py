"""RULE-006: DRY -- one definition per helper.

A top-level function or class name defined in two package modules is almost
always the same helper written twice. Generated files are excluded (they
mirror their async source by design), as are dunder names.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from typing import ClassVar, Final

from rules.base import ERROR, FileContext, ProjectRule, Severity, Violation

_DUNDER: Final = "__"
#: Names that legitimately recur: each module's own logger and type variables.
ALLOWED: Final = frozenset({"logger", "T", "M"})


class NoDuplicateDefinitions(ProjectRule):
    id: ClassVar[str] = "RULE-006"
    category: ClassVar[str] = "No Duplicate Definitions"
    severity: ClassVar[Severity] = ERROR
    description: ClassVar[str] = "A top-level function/class name is defined in one module only"
    remediation: ClassVar[str] = "Keep one definition and import it everywhere else."

    def __init__(self) -> None:
        self._defined: dict[str, list[tuple[FileContext, int]]] = defaultdict(list)

    def collect(self, file: FileContext) -> None:
        if not file.is_package or file.is_generated:
            return
        for node in file.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                if not name.startswith(_DUNDER) and name not in ALLOWED:
                    self._defined[name].append((file, node.lineno))

    def finish(self) -> list[Violation]:
        return [
            self.violation(
                file, line, f"{name!r} is also defined in {len(sites) - 1} other module(s)."
            )
            for name, sites in self._defined.items()
            if len({f.relative for f, _ in sites}) > 1
            for file, line in sites
        ]


RULE = NoDuplicateDefinitions()
