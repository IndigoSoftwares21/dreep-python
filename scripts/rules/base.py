"""Shared types and helpers for the repository rules.

Ported from the lernicle/vsured ``verify-rules`` architecture: every rule is a
small object with an id, a severity and a ``check`` method; the runner builds
one :class:`FileContext` per file and hands it to every rule.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import ClassVar, Final, Literal, Protocol

Severity = Literal["ERROR", "WARN"]
ERROR: Final[Severity] = "ERROR"
WARN: Final[Severity] = "WARN"

ROOT: Final = Path(__file__).resolve().parents[2]
PACKAGE_DIR: Final = ROOT / "src" / "dreep"
TESTS_DIR: Final = ROOT / "tests"
SCAN_DIRS: Final = (PACKAGE_DIR, TESTS_DIR, ROOT / "scripts")
SKIP_DIRS: Final = frozenset({".venv", "__pycache__", ".git", "build", "dist", ".mypy_cache"})

#: Generated from the async sources by scripts/unasync.py. Rules that judge
#: authored code (duplication, magic strings) skip these: they mirror their
#: source by construction.
GENERATED: Final = re.compile(r"(^|/)src/dreep/(_sync_\w+|_client)\.py$")
#: Modules whose job is to define constants; literals there are the point.
CONSTANTS_MODULE: Final = re.compile(r"(^|/)_?\w*constants\.py$")
SNIPPET_LENGTH: Final = 120


@dataclass(frozen=True)
class Violation:
    rule_id: str
    category: str
    severity: Severity
    path: str
    line: int
    message: str
    remediation: str
    snippet: str | None = None


@dataclass
class FileContext:
    """A file read once and classified once, shared by every rule."""

    path: Path
    relative: str
    content: str
    lines: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.lines = self.content.splitlines()

    @property
    def is_test(self) -> bool:
        return self.relative.startswith("tests/")

    @property
    def is_package(self) -> bool:
        return self.relative.startswith("src/dreep/")

    @property
    def is_script(self) -> bool:
        return self.relative.startswith("scripts/")

    @property
    def is_generated(self) -> bool:
        return bool(GENERATED.search(self.relative))

    @property
    def is_constants(self) -> bool:
        return bool(CONSTANTS_MODULE.search(self.relative))

    @property
    def module(self) -> str:
        return self.path.stem

    @cached_property
    def tree(self) -> ast.Module:
        return ast.parse(self.content, filename=self.relative)

    def snippet(self, line: int) -> str:
        return self.lines[line - 1].strip()[:SNIPPET_LENGTH] if 0 < line <= len(self.lines) else ""


class Rule(Protocol):
    id: ClassVar[str]
    category: ClassVar[str]
    severity: ClassVar[Severity]
    description: ClassVar[str]

    def check(self, file: FileContext) -> list[Violation]: ...


class BaseRule:
    """Convenience base: subclasses set the ClassVars and implement ``check``."""

    id: ClassVar[str]
    category: ClassVar[str]
    severity: ClassVar[Severity]
    description: ClassVar[str]
    remediation: ClassVar[str]

    def violation(
        self, file: FileContext, line: int, message: str, *, severity: Severity | None = None
    ) -> Violation:
        return Violation(
            rule_id=self.id,
            category=self.category,
            severity=severity or self.severity,
            path=file.relative,
            line=line,
            message=message,
            remediation=self.remediation,
            snippet=file.snippet(line) or None,
        )


class ProjectRule(BaseRule):
    """A rule that judges the codebase as a whole rather than one file.

    The runner calls :meth:`check` for every file (so the rule can collect)
    and :meth:`finish` once at the end (so it can report).
    """

    def check(self, file: FileContext) -> list[Violation]:
        self.collect(file)
        return []

    def collect(self, file: FileContext) -> None:
        raise NotImplementedError

    def finish(self) -> list[Violation]:
        raise NotImplementedError


def has_allow_comment(file: FileContext, line: int, tag: str) -> bool:
    """True if ``# <tag>: <reason>`` is on the line or the line above it.

    Each flagged line must justify itself inline; there are no blanket exemptions.
    """
    pattern = re.compile(rf"#\s*{re.escape(tag)}:\s*\S")
    candidates = (line, line - 1)
    return any(0 < n <= len(file.lines) and pattern.search(file.lines[n - 1]) for n in candidates)


def walk_python_files() -> Iterator[Path]:
    for base in SCAN_DIRS:
        for path in sorted(base.rglob("*.py")):
            if not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
                yield path


def build_context(path: Path) -> FileContext:
    return FileContext(
        path=path, relative=path.relative_to(ROOT).as_posix(), content=path.read_text()
    )
