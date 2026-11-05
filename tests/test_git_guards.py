"""The git hook guards accept the conventions and reject everything else."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import git_guards

ZERO = "0" * 40


@pytest.mark.parametrize("name", ["main", "feature/presigned-uploads", "bugfix/x-1", "1/merge"])
def test_valid_branch_names(name: str) -> None:
    assert git_guards.check_branch(name) == git_guards.OK


@pytest.mark.parametrize("name", ["Feature/X", "presigned", "feature/Has_Caps", "wip/thing"])
def test_invalid_branch_names(name: str) -> None:
    assert git_guards.check_branch(name) == git_guards.FAIL


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("feat(upload): stream presigned PUTs\n\nBody.\n", git_guards.OK),
        ("fix!: drop python 3.9\n", git_guards.OK),
        ("Merge branch 'x'\n", git_guards.OK),
        ("added stuff\n", git_guards.FAIL),
        ("feat: " + "x" * 120 + "\n", git_guards.FAIL),
    ],
)
def test_commit_messages(tmp_path: Path, message: str, expected: int) -> None:
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text(message)
    assert git_guards.check_commit_message(str(path)) == expected


def test_pre_push_blocks_protected_branches_and_ignores_deletes() -> None:
    sha = "a" * 40
    assert git_guards.check_pre_push(f"refs/heads/main {sha} refs/heads/main {ZERO}\n") == 1
    assert git_guards._pushed_refs(f"refs/heads/x {ZERO} refs/heads/x {sha}\n") == []
