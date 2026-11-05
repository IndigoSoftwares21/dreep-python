"""Git hook guards, ported from the lernicle/vsured husky scripts to Python.

    python scripts/git_guards.py branch            # branch name follows the convention
    python scripts/git_guards.py commit-msg FILE   # Conventional Commits subject/body
    python scripts/git_guards.py pre-push          # reads git's pre-push stdin

pre-push blocks, per ref being pushed:

* direct pushes to a protected branch (open a pull request instead),
* force pushes that rewrite a long-lived branch's history,
* unsigned commits.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Final

LONG_LIVED: Final = frozenset({"main", "master", "dev", "development", "testing", "production"})
PROTECTED: Final = LONG_LIVED
NO_REWRITE: Final = LONG_LIVED
BRANCH: Final = re.compile(r"^(feature|bugfix|hotfix|refactor|chore|docs|ci|release)/[a-z0-9._-]+$")
PR_MERGE_REF: Final = re.compile(r"^(refs/pull/)?\d+/merge$")

COMMIT_TYPES: Final = "feat|fix|refactor|perf|test|docs|style|build|ci|chore|revert"
SUBJECT: Final = re.compile(rf"^({COMMIT_TYPES})(\([a-z0-9_-]+\))?!?: .+")
EXEMPT_SUBJECT: Final = re.compile(r"^(Merge|Revert) ")
MAX_LINE: Final = 100

ZERO_SHA: Final = "0" * 40
HEADS_PREFIX: Final = "refs/heads/"
UNSIGNED: Final = "N"
DETACHED: Final = "HEAD"
OK, FAIL = 0, 1


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def _fail(message: str) -> int:
    sys.stderr.write(f"\n  BLOCKED: {message}\n\n")
    return FAIL


def check_branch(name: str | None = None) -> int:
    name = name or _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if name == DETACHED:
        sys.stderr.write("Detached HEAD: skipping branch-name check.\n")
        return OK
    if name in LONG_LIVED or BRANCH.match(name) or PR_MERGE_REF.match(name):
        return OK
    return _fail(
        f"Branch {name!r} doesn't follow <type>/<kebab-description>, "
        "e.g. feature/presigned-uploads or bugfix/signed-url-snapping."
    )


def check_commit_message(path: str) -> int:
    lines = [ln for ln in Path(path).read_text().splitlines() if not ln.startswith("#")]
    subject = lines[0] if lines else ""
    if EXEMPT_SUBJECT.match(subject):
        return OK
    if not SUBJECT.match(subject):
        return _fail(
            f"Commit subject must be '<type>(<scope>)?: <summary>' with type in {COMMIT_TYPES}."
        )
    too_long = [n for n, ln in enumerate(lines, start=1) if len(ln) > MAX_LINE]
    if too_long:
        return _fail(f"Line(s) {too_long} exceed {MAX_LINE} characters.")
    return OK


def _pushed_refs(stdin: str) -> list[tuple[str, str, str]]:
    """(branch, local sha, remote sha) for every non-deleting push line."""
    refs = []
    for line in stdin.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[1] != ZERO_SHA:
            _, local_sha, remote_ref, remote_sha = parts
            refs.append((remote_ref.removeprefix(HEADS_PREFIX), local_sha, remote_sha))
    return refs


def _check_ref(branch: str, local_sha: str, remote_sha: str) -> str | None:
    if branch in PROTECTED:
        return f"Direct push to {branch!r}. Push a branch and open a pull request."
    is_new = remote_sha == ZERO_SHA
    rewrites = (
        branch in NO_REWRITE
        and not is_new
        and _git("merge-base", "--is-ancestor", remote_sha, local_sha).returncode != 0
    )
    if rewrites:
        return f"Force push to {branch!r} would rewrite shared history."
    commits = [local_sha, "-1"] if is_new else [f"{remote_sha}..{local_sha}"]
    signatures = _git("log", "--format=%G?", *commits)
    if signatures.returncode != 0:
        return f"Couldn't verify signatures on {branch!r}: {signatures.stderr.strip()}"
    if UNSIGNED in signatures.stdout.split():
        return "Unsigned commits. Sign them: git commit --amend --no-edit -S (or rebase -S)."
    return None


def check_pre_push(stdin: str) -> int:
    for branch, local_sha, remote_sha in _pushed_refs(stdin):
        problem = _check_ref(branch, local_sha, remote_sha)
        if problem:
            return _fail(problem)
    return OK


def main(argv: list[str]) -> int:
    command, *rest = argv or [""]
    if command == "branch":
        return check_branch(rest[0] if rest else None)
    if command == "commit-msg" and rest:
        return check_commit_message(rest[0])
    if command == "pre-push":
        return check_pre_push(sys.stdin.read())
    sys.stderr.write(__doc__ or "")
    return FAIL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
