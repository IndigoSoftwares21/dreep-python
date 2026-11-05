"""RULE-011: behaviour is protected by tests.

Ported from lernicle RULE-007/009. Every authored package module of
:data:`MIN_LINES` or more must be exercised by name somewhere in ``tests/``
(an import of the module, or of something it defines). Line coverage itself
is enforced by pytest-cov's ``fail_under``; this rule catches a module that
no test even mentions.
"""

from __future__ import annotations

import ast
import re
from typing import ClassVar, Final

from rules.base import TESTS_DIR, WARN, FileContext, ProjectRule, Severity, Violation

MIN_LINES: Final = 10
#: Modules covered through the public API rather than by direct import: the
#: package facade, and the client mixins that only exist as bases of
#: Dreep/AsyncDreep (exercised by tests/test_client.py and test_async_client.py).
COVERED_VIA_PUBLIC_API: Final = re.compile(r"^(__init__|_version|types|_async_\w+)$")


class ModulesHaveTests(ProjectRule):
    id: ClassVar[str] = "RULE-011"
    category: ClassVar[str] = "Modules Have Tests"
    severity: ClassVar[Severity] = WARN
    description: ClassVar[str] = f"Package modules of {MIN_LINES}+ lines are referenced by tests"
    remediation: ClassVar[str] = "Add a test that exercises this module's behaviour."

    def __init__(self) -> None:
        self._modules: list[tuple[FileContext, set[str]]] = []
        self._test_text = "\n".join(p.read_text() for p in sorted(TESTS_DIR.rglob("*.py")))

    def collect(self, file: FileContext) -> None:
        if not file.is_package or file.is_generated or COVERED_VIA_PUBLIC_API.match(file.module):
            return
        if len(file.lines) < MIN_LINES:
            return
        names = {file.module} | {
            node.name
            for node in file.tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("_")
        }
        self._modules.append((file, names))

    def finish(self) -> list[Violation]:
        return [
            self.violation(file, 1, "No test references this module or anything it defines.")
            for file, names in self._modules
            if not any(name in self._test_text for name in names)
        ]


RULE = ModulesHaveTests()
