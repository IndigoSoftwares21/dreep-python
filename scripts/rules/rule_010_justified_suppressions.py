"""RULE-010: every suppression names what it suppresses.

Ported from lernicle's "no any" rule, adapted to Python: a bare
``# type: ignore`` or ``# noqa`` silences everything on the line, including
the next, unrelated bug. Suppressions must name their error code.
"""

from __future__ import annotations

import re
from typing import ClassVar, Final

from rules.base import ERROR, BaseRule, FileContext, Severity, Violation

BARE_SUPPRESSION: Final = re.compile(r"#\s*(type:\s*ignore|noqa)(?![\[:])")
SELF: Final = "scripts/rules/rule_010_justified_suppressions.py"


class JustifiedSuppressions(BaseRule):
    id: ClassVar[str] = "RULE-010"
    category: ClassVar[str] = "Justified Suppressions"
    severity: ClassVar[Severity] = ERROR
    description: ClassVar[str] = "type: ignore / noqa must name an error code"
    remediation: ClassVar[str] = "Write '# type: ignore[code]' or '# noqa: CODE'."

    def check(self, file: FileContext) -> list[Violation]:
        if file.relative == SELF:
            return []
        return [
            self.violation(file, number, "Bare suppression.")
            for number, line in enumerate(file.lines, start=1)
            if BARE_SUPPRESSION.search(line)
        ]


RULE = JustifiedSuppressions()
