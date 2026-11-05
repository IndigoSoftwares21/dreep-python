"""The repository rules detect what they claim to, and the repo passes them."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from rules import load_rules  # noqa: E402 -- needs the path above
from rules.base import FileContext, ProjectRule, Violation  # noqa: E402


def violations_for(
    rule_id: str, source: str, relative: str = "src/dreep/_sample.py"
) -> list[Violation]:
    rule = next(r for r in load_rules() if r.id == rule_id)
    file = FileContext(path=ROOT / relative, relative=relative, content=source)
    found = rule.check(file)
    if isinstance(rule, ProjectRule):
        found += rule.finish()
    return found


LONG = "x = 1\n" * 201
# Built from parts so this file doesn't trip the very rules it tests.
PLAIN_HTTP = "http" + "://api.example.com"
BARE_IGNORE = "# type" + ": ignore"


@pytest.mark.parametrize(
    ("rule_id", "bad", "good"),
    [
        ("RULE-001", LONG, "x = 1\n"),
        ("RULE-002", "from .a import b\nfrom .c import d\n", "from .a import b\nVALUE = b\n"),
        ("RULE-003", "print('hi')\n", "logger.info('hi')\n"),
        ("RULE-004", "if status == 'ready':\n    pass\n", "if status == READY:\n    pass\n"),
        ("RULE-004", "a = d['data']\n", "a = d[DATA]\n"),
        ("RULE-004", "a = f('abc')\nb = g('abc')\n", "ABC = 'abc'\na = f(ABC)\n"),
        ("RULE-005", "".join(f"v{i} = f({i})\n" for i in range(6)) * 2, "a = f(1)\n"),
        ("RULE-007", "import httpx\n", "import json\n"),
        ("RULE-008", "def process():\n    pass\n", "def snap_up():\n    pass\n"),
        ("RULE-009", f"URL = '{PLAIN_HTTP}'\n", "URL = 'https://api.example.com'\n"),
        ("RULE-010", f"x = 1  {BARE_IGNORE}\n", f"x = 1  {BARE_IGNORE}[assignment]\n"),
    ],
)
def test_rule_flags_bad_and_passes_good(rule_id: str, bad: str, good: str) -> None:
    assert violations_for(rule_id, bad), f"{rule_id} missed a violation"
    assert not violations_for(rule_id, good), f"{rule_id} raised a false positive"


def test_duplicate_definitions_across_modules() -> None:
    rule = next(r for r in load_rules() if r.id == "RULE-006")
    assert isinstance(rule, ProjectRule)
    for name in ("_a.py", "_b.py"):
        relative = f"src/dreep/{name}"
        rule.check(FileContext(ROOT / relative, relative, "def shared():\n    pass\n"))
    assert len(rule.finish()) == 2


def test_allow_comment_exempts_a_line() -> None:
    source = "if mode == 'x':  # allow-magic: protocol keyword\n    pass\n"
    assert not violations_for("RULE-004", source)


def test_generated_and_test_files_are_exempt_from_authoring_rules() -> None:
    assert not violations_for("RULE-001", LONG, "src/dreep/_sync_core.py")
    assert not violations_for("RULE-003", "print(1)\n", "tests/test_x.py")


def test_repository_passes_its_own_rules() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_rules.py"), "--summary"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
