"""RULE-004: no magic strings.

"A magic string is an unexplained or repeated value that represents
application behaviour" (lernicle AGENTS.md section 6). Detected with the AST:

* a literal compared against (``x == "ready"``, ``k in ("a", "b")``),
* a literal used as a lookup key (``d["data"]``, ``d.get("data")``),
* the same literal appearing in two or more places across the package.

Not flagged: docstrings, f-string text, messages passed to exceptions or the
logger, ``__all__``, ``Literal[...]`` types, named module constants
(``UPPER_CASE = "..."``), constants modules, generated files, tests, and any
line carrying ``# allow-magic: <reason>``.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from typing import ClassVar, Final, TypeGuard

from rules.base import ERROR, FileContext, ProjectRule, Severity, Violation, has_allow_comment

ALLOW_TAG: Final = "allow-magic"
MIN_REPEAT_LENGTH: Final = 3
MIN_OCCURRENCES: Final = 2
LOOKUP_METHODS: Final = frozenset({"get", "pop", "setdefault"})
MESSAGE_CALLEES: Final = frozenset(
    {"debug", "info", "warning", "error", "exception", "critical", "write"}
)
_LITERAL: Final = "Literal"
_DUNDER_ALL: Final = "__all__"


def _exempt_nodes(tree: ast.Module) -> set[int]:
    """ids of string constants that are not behaviour: docs, messages, types, names."""
    exempt: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                exempt.add(id(first.value))
        elif isinstance(node, ast.JoinedStr):
            exempt.update(id(v) for v in node.values)
        elif isinstance(node, ast.Raise) and node.exc is not None:
            exempt.update(id(n) for n in ast.walk(node.exc))
        elif isinstance(node, ast.Call) and _callee(node) in MESSAGE_CALLEES:
            exempt.update(id(n) for n in ast.walk(node))
        elif isinstance(node, ast.Subscript) and _callee_name(node.value) == _LITERAL:
            exempt.update(id(n) for n in ast.walk(node.slice))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and _is_named_constant(node):
            exempt.update(id(n) for n in ast.walk(node))
    return exempt


def _callee_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    return node.attr if isinstance(node, ast.Attribute) else None


def _callee(node: ast.Call) -> str | None:
    return _callee_name(node.func)


def _is_named_constant(node: ast.Assign | ast.AnnAssign) -> bool:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    names = [t.id for t in targets if isinstance(t, ast.Name)]
    return bool(names) and all(n.isupper() or n == _DUNDER_ALL for n in names if n.strip("_"))


def _behavioural(tree: ast.Module) -> set[int]:
    """ids of string constants in comparisons or used as lookup keys."""
    flagged: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for side in [node.left, *node.comparators]:
                flagged.update(id(n) for n in ast.walk(side) if _is_str(n))
        elif isinstance(node, ast.Subscript) and _is_str(node.slice):
            flagged.add(id(node.slice))
        elif (
            isinstance(node, ast.Call)
            and _callee(node) in LOOKUP_METHODS
            and node.args
            and _is_str(node.args[0])
        ):
            flagged.add(id(node.args[0]))
    return flagged


def _is_str(node: ast.AST) -> TypeGuard[ast.Constant]:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


class NoMagicStrings(ProjectRule):
    id: ClassVar[str] = "RULE-004"
    category: ClassVar[str] = "No Magic Strings"
    severity: ClassVar[Severity] = ERROR
    description: ClassVar[str] = "Behavioural or repeated string literals must be named constants"
    remediation: ClassVar[str] = (
        "Name it in the owning constants module (or a module-level UPPER_CASE Final), "
        f"or justify it with '# {ALLOW_TAG}: <reason>'."
    )

    def __init__(self) -> None:
        self._occurrences: dict[str, list[tuple[FileContext, int]]] = defaultdict(list)
        self._direct: list[Violation] = []

    def collect(self, file: FileContext) -> None:
        if not file.is_package or file.is_generated or file.is_constants:
            return
        exempt, behavioural = _exempt_nodes(file.tree), _behavioural(file.tree)
        for node in ast.walk(file.tree):
            if (
                not _is_str(node)
                or id(node) in exempt
                or has_allow_comment(file, node.lineno, ALLOW_TAG)
            ):
                continue
            value = str(node.value)
            if id(node) in behavioural:
                self._direct.append(self.violation(file, node.lineno, f"Magic string {value!r}."))
            elif len(value) >= MIN_REPEAT_LENGTH:
                self._occurrences[value].append((file, node.lineno))

    def finish(self) -> list[Violation]:
        repeated = [
            self.violation(file, line, f"{value!r} appears {len(sites)} times.")
            for value, sites in self._occurrences.items()
            if len(sites) >= MIN_OCCURRENCES
            for file, line in sites
        ]
        return self._direct + repeated


RULE = NoMagicStrings()
