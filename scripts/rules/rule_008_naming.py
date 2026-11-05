"""RULE-008: names communicate intent.

"The filename should communicate what the module does" (lernicle section 19)
and "avoid names like process() or doStuff()" (section 24). Generic module
names and placeholder identifiers are rejected.
"""

from __future__ import annotations

import ast
from typing import ClassVar, Final

from rules.base import WARN, BaseRule, FileContext, Severity, Violation

GENERIC_MODULES: Final = frozenset({"utils", "helpers", "common", "misc", "stuff", "util"})
VAGUE_NAMES: Final = frozenset(
    {"process", "handle_data", "do_stuff", "helper", "temp", "tmp", "data2", "foo", "bar", "baz"}
)


class Naming(BaseRule):
    id: ClassVar[str] = "RULE-008"
    category: ClassVar[str] = "Naming Communicates Intent"
    severity: ClassVar[Severity] = WARN
    description: ClassVar[str] = "No generic module names or placeholder identifiers"
    remediation: ClassVar[str] = "Name it after what it does (e.g. 'snap_up', '_error_mapping')."

    def check(self, file: FileContext) -> list[Violation]:
        if file.is_test:
            return []
        violations = []
        if file.module.lstrip("_") in GENERIC_MODULES:
            violations.append(self.violation(file, 1, f"Generic module name {file.path.name!r}."))
        for name, line in _defined_names(file.tree):
            if name.lstrip("_") in VAGUE_NAMES:
                violations.append(self.violation(file, line, f"Vague name {name!r}."))
        return violations


def _defined_names(tree: ast.Module) -> list[tuple[str, int]]:
    """Every function, class and assigned variable name, with its line."""
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append((node.name, node.lineno))
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.append((node.id, node.lineno))
    return names


RULE = Naming()
