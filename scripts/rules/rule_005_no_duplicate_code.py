"""RULE-005: DRY -- no copy-pasted blocks.

"Never duplicate logic, schemas, constants, error classes or helpers. If one
exists, import and reuse it" (vsured code-standards-and-dry.md).

Every authored package module is normalised (whitespace, comments, docstring
lines and pure wiring lines dropped) and hashed in windows of
:data:`WINDOW` consecutive logic lines. A window that appears in two places
is reported at both. Wiring lines -- parameter declarations and
``name=name,`` pass-throughs -- are skipped, because a keyword-only API
necessarily repeats its parameter lists; logic is what must not repeat.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import ClassVar, Final

from rules.base import ERROR, FileContext, ProjectRule, Severity, Violation

WINDOW: Final = 6
#: Lines that carry no logic of their own: signature parameters, pass-throughs,
#: bare brackets, decorators, and name lists (``__all__`` entries, imports).
WIRING: Final = re.compile(
    r"^(\*?\w+: [^=]+(= .+)?,?|\w+=\w+(\.\w+)*,?|[)\]}]+[,:]?( -> .+:)?|@\w+.*|\.\.\."
    r"|\"[\w.]+\",?|\w+,)$"
)
COMMENT: Final = "#"
DOCSTRING_QUOTES: Final = ('"""', "'''")


def _logic_lines(file: FileContext) -> list[tuple[int, str]]:
    kept: list[tuple[int, str]] = []
    in_docstring = False
    for number, raw in enumerate(file.lines, start=1):
        line = raw.strip()
        quotes = sum(line.count(q) for q in DOCSTRING_QUOTES)
        if in_docstring or line.startswith(DOCSTRING_QUOTES):
            in_docstring = in_docstring != (quotes % 2 == 1)
            continue
        if not line or line.startswith(COMMENT) or WIRING.match(line):
            continue
        kept.append((number, line))
    return kept


class NoDuplicateCode(ProjectRule):
    id: ClassVar[str] = "RULE-005"
    category: ClassVar[str] = "No Duplicate Code"
    severity: ClassVar[Severity] = ERROR
    description: ClassVar[str] = f"No block of {WINDOW}+ logic lines may appear twice"
    remediation: ClassVar[str] = "Extract the shared block into one function and call it."

    def __init__(self) -> None:
        self._windows: dict[tuple[str, ...], list[tuple[FileContext, int]]] = defaultdict(list)

    def collect(self, file: FileContext) -> None:
        if not file.is_package or file.is_generated:
            return
        lines = _logic_lines(file)
        for start in range(len(lines) - WINDOW + 1):
            window = tuple(text for _, text in lines[start : start + WINDOW])
            self._windows[window].append((file, lines[start][0]))

    def finish(self) -> list[Violation]:
        reported: set[tuple[str, int]] = set()
        violations = []
        for sites in self._windows.values():
            if len(sites) < 2:
                continue
            for file, line in sites:
                # One report per region, not one per overlapping window.
                if any((file.relative, line - d) in reported for d in range(WINDOW)):
                    continue
                reported.add((file.relative, line))
                others = ", ".join(f"{f.relative}:{n}" for f, n in sites if (f, n) != (file, line))
                violations.append(
                    self.violation(file, line, f"Duplicated block; also at {others}.")
                )
        return violations


RULE = NoDuplicateCode()
