"""RULE-002: no barrel modules.

A module whose every statement is a re-export adds an import hop and hides
where things live. The package's top-level ``__init__.py`` -- the public API
surface -- is the one sanctioned exception, along with the public
``types.py`` facade.
"""

from __future__ import annotations

import ast
from typing import ClassVar, Final

from rules.base import ERROR, BaseRule, FileContext, Severity, Violation

PUBLIC_FACADES: Final = frozenset({"src/dreep/__init__.py"})
MIN_REEXPORTS: Final = 2
_DUNDER_ALL: Final = "__all__"


def _is_reexport(node: ast.stmt) -> bool:
    if isinstance(node, ast.ImportFrom):
        return node.level > 0
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
        return True  # docstring
    if isinstance(node, ast.Assign):
        return any(isinstance(t, ast.Name) and t.id == _DUNDER_ALL for t in node.targets)
    return False


class NoBarrelFiles(BaseRule):
    id: ClassVar[str] = "RULE-002"
    category: ClassVar[str] = "No Barrel Files"
    severity: ClassVar[Severity] = ERROR
    description: ClassVar[str] = "Modules must not consist solely of re-exports"
    remediation: ClassVar[str] = "Import from the defining module instead."

    def check(self, file: FileContext) -> list[Violation]:
        if not file.is_package or file.relative in PUBLIC_FACADES:
            return []
        body = [
            n
            for n in file.tree.body
            if not isinstance(n, ast.ImportFrom) or n.module != "__future__"
        ]
        imports = [n for n in body if isinstance(n, ast.ImportFrom) and n.level > 0]
        if len(imports) >= MIN_REEXPORTS and all(_is_reexport(n) for n in body):
            return [self.violation(file, 1, "Module only re-exports other modules.")]
        return []


RULE = NoBarrelFiles()
