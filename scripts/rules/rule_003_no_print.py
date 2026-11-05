"""RULE-003: libraries never print.

A library writing to stdout corrupts its host's output. Diagnostics go through
``logging.getLogger("dreep")`` so applications decide what to show.
"""

from __future__ import annotations

import ast
from typing import ClassVar, Final

from rules.base import ERROR, BaseRule, FileContext, Severity, Violation

BANNED_CALLS: Final = frozenset({"print", "breakpoint", "pprint"})


class NoPrint(BaseRule):
    id: ClassVar[str] = "RULE-003"
    category: ClassVar[str] = "No Print"
    severity: ClassVar[Severity] = ERROR
    description: ClassVar[str] = "No print()/breakpoint() in the package"
    remediation: ClassVar[str] = "Use the 'dreep' logger, or remove the debugging call."

    def check(self, file: FileContext) -> list[Violation]:
        if not file.is_package:
            return []
        return [
            self.violation(file, node.lineno, f"{node.func.id}() call.")
            for node in ast.walk(file.tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in BANNED_CALLS
        ]


RULE = NoPrint()
