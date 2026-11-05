"""RULE-001: modules stay small enough to hold in your head.

Over 200 lines warns, over 400 fails. A file may opt out with
``# rule-001-allow: <reason>`` in its first 10 lines. Tests and generated
files are exempt: tests are flat lists of cases, generated files mirror a
source that is itself held to the limit.
"""

from __future__ import annotations

import re
from typing import ClassVar, Final

from rules.base import ERROR, WARN, BaseRule, FileContext, Severity, Violation

SOFT_LIMIT: Final = 200
HARD_LIMIT: Final = 400
HEADER_LINES: Final = 10
ALLOW: Final = re.compile(r"#\s*rule-001-allow:\s*\S")


class ModuleFileLength(BaseRule):
    id: ClassVar[str] = "RULE-001"
    category: ClassVar[str] = "Module File Length"
    severity: ClassVar[Severity] = ERROR
    description: ClassVar[str] = f"Modules warn above {SOFT_LIMIT} lines, fail above {HARD_LIMIT}"
    remediation: ClassVar[str] = "Split the module along a responsibility boundary."

    def check(self, file: FileContext) -> list[Violation]:
        if file.is_test or file.is_generated:
            return []
        if any(ALLOW.search(line) for line in file.lines[:HEADER_LINES]):
            return []
        count = len(file.lines)
        if count <= SOFT_LIMIT:
            return []
        hard = count > HARD_LIMIT
        limit = HARD_LIMIT if hard else SOFT_LIMIT
        severity = ERROR if hard else WARN
        return [self.violation(file, 1, f"{count} lines (limit {limit}).", severity=severity)]


RULE = ModuleFileLength()
