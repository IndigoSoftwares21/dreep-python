<div align="center">

<img src="https://raw.githubusercontent.com/IndigoSoftwares21/dreep-python/main/.github/assets/dreep-logo.svg" alt="Dreep" width="64" height="71">

# Contributing to the Dreep Python SDK

</div>

Thank you for helping improve the SDK. This guide covers everything from finding
something to work on to getting your pull request merged.

## The contribution flow at a glance

```mermaid
flowchart LR
    A[Find or open<br/>an issue] --> B[Get it assigned<br/>to you]
    B --> C[Branch:<br/>type/123-short-name]
    C --> D[Code + tests<br/>quality gate passes]
    D --> E[Open a PR that<br/>says Closes #123]
    E --> F[Review from both<br/>maintainers]
    F --> G[Approved:<br/>squash and merge]
```

**Every pull request must be linked to an issue, and must be reviewed by both maintainers.**
That way each change has an agreed purpose before anyone writes code, and nothing is
merged without review.

| Maintainer | GitHub |
| :- | :- |
| Abe Toluwani | [abetoluwani](https://github.com/abetoluwani) |
| Precious Orjiude (Indigo) | [IndigoSoftwares21](https://github.com/IndigoSoftwares21) |

## 1. Start with an issue

- **Found a bug?** Search the [open issues](https://github.com/IndigoSoftwares21/dreep-python/issues)
  first. If it isn't there, [file a bug report](https://github.com/IndigoSoftwares21/dreep-python/issues/new?template=bug_report.yml)
  with the SDK version, Python version, and the smallest code that shows the problem.
- **Want a feature?** [Open a feature request](https://github.com/IndigoSoftwares21/dreep-python/issues/new?template=feature_request.yml)
  that describes the problem you're trying to solve, not only the solution you have in mind.
- **Want to help but don't have an idea?** Look for issues labelled
  [`good first issue`](https://github.com/IndigoSoftwares21/dreep-python/labels/good%20first%20issue)
  or [`help wanted`](https://github.com/IndigoSoftwares21/dreep-python/labels/help%20wanted).

Comment on the issue to say you'd like to take it, and wait until a maintainer assigns it
to you before you start. That way two people don't build the same thing, and the approach
is agreed before you write code.

> [!NOTE]
> Security problems are the exception: never report them in a public issue. See
> [SECURITY.md](SECURITY.md).

## 2. Set up your environment

```bash
gh repo fork IndigoSoftwares21/dreep-python --clone   # or: git clone, if you're a collaborator
cd dreep-python
bash scripts/setup_hooks.sh
```

`setup_hooks.sh` creates `.venv`, installs the SDK with its development tools, and turns
on the git hooks in `.githooks/`. The hooks run the quality gate before every commit, so
problems show up on your machine, not in review.

## 3. Create a branch for the issue

Name the branch `<type>/<issue-number>-<short-description>`, in lowercase kebab-case:

```bash
git switch -c feature/42-configurable-retry-delay
```

| Type | Use it for |
| :- | :- |
| `feature/` | New capability |
| `bugfix/` | Fixing incorrect behaviour |
| `hotfix/` | Urgent fix for a released version |
| `refactor/` | Restructuring without changing behaviour |
| `docs/` | Documentation only |
| `chore/`, `ci/` | Tooling, dependencies, workflows |
| `release/` | Preparing a release |

## 4. Make the change

### How the code is organised

| Where | What lives there |
| :- | :- |
| `src/dreep/_async_*.py` | The client. **This is the code you edit.** |
| `src/dreep/_sync_*.py`, `_client.py` | Generated from the async files. **Never edit these by hand.** |
| `src/dreep/_operations_*.py` | One builder per endpoint: checks arguments and describes the request |
| `src/dreep/_models*.py` | Response models (frozen dataclasses) |
| `src/dreep/*_constants.py` | Every value that affects behaviour |
| `tests/` | Tests, against an in-memory transport (no network) |
| `scripts/rules/` | The repository rules (one file per rule) |

[AGENTS.md](AGENTS.md) has the full architecture and the reasons behind it.

### Adding or changing an endpoint

1. Add or update the builder in `_operations_media.py` or `_operations_project.py`.
2. Add or update the model in `_models.py` or `_models_project.py`. Field names convert
   to the API's names automatically (`size_bytes` becomes `sizeBytes`).
3. Add the method to the matching `_async_*.py` file.
4. Regenerate the sync client:
   ```bash
   .venv/bin/python scripts/unasync.py
   ```
5. Add tests to `tests/test_client.py` (and `tests/test_async_client.py` if the async
   behaviour differs).
6. Document it in `README.md` and add a line under **Unreleased** in `CHANGELOG.md`.

### House rules

These are enforced automatically: a commit that breaks them is stopped by the hooks.

- **No magic strings.** Put behaviour-affecting values in the owning constants module.
- **DRY.** Don't repeat a block of logic; extract it.
- **Small files.** Over 200 lines warns; over 400 fails.
- **Layering.** Only the client layer may use `httpx` or `anyio`.
- **Every suppression explains itself:** `# type: ignore[code]`, `# noqa: CODE`,
  `# allow-magic: reason`.
- **Tests come with every behaviour change.** A bug fix includes a test that would have
  caught the bug.

### Run the quality gate

```bash
bash scripts/quality_gate.sh
```

It runs, in order:
1. Generated-client check
2. ruff lint and format
3. Repository rules
4. `mypy --strict`
5. pytest, with coverage of at least 90%

The pre-commit hook runs the same gate, and so does CI.

## 5. Commit

Use [Conventional Commits](https://www.conventionalcommits.org), with lines of at most 100
characters, and sign your commits:

```text
feat(upload): allow a custom chunk size for presigned uploads

Large uploads over slow links benefit from smaller chunks.

Closes #42
```

Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `style`, `build`, `ci`,
`chore`, `revert`. The commit-msg hook checks the format.

If you haven't set up commit signing yet, see
[GitHub's guide](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits).

## 6. Open a pull request, linked to the issue

```bash
git push -u origin feature/42-configurable-retry-delay
gh pr create --fill --reviewer abetoluwani,IndigoSoftwares21
```

The PR template asks for:

- **The linked issue.** Write `Closes #42` (or `Fixes #42`) in the description. GitHub then
  closes the issue when the PR merges. A CI check fails any PR that isn't linked to an
  issue.
- **Reviewers.** Request review from both maintainers: **Abe Toluwani
  ([abetoluwani](https://github.com/abetoluwani))** and **Indigo
  ([IndigoSoftwares21](https://github.com/IndigoSoftwares21))**. CODEOWNERS requests them
  automatically, but check that both are listed.
- **What changed and how you tested it.**

Keep each PR focused on its issue. Unrelated clean-ups belong in their own issue and PR.

## 7. Review and merge

- Both maintainers review. Answer each comment with either a change or a reply, then
  re-request review.
- CI must be green: the quality gate on Python 3.10 to 3.14, plus the issue-link check.
- After **both maintainers approve**, a maintainer squash-merges the PR. The squashed
  commit keeps your Conventional Commit title.
- Don't push directly to `main` or rewrite its history. The pre-push hook blocks both.

## Releasing (maintainers)

1. Open a `release/x.y.z` PR that bumps `src/dreep/_version.py` and moves the
   **Unreleased** notes in `CHANGELOG.md` under the new version.
2. Merge it with both approvals.
3. Tag the merge commit and push the tag:
   ```bash
   git tag -s vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```
4. The release workflow tests and builds the package, publishes it to PyPI, and creates the
   GitHub Release.

## Getting help

Ask on the issue you're working on, or open a
[discussion issue](https://github.com/IndigoSoftwares21/dreep-python/issues/new). For
questions about the Dreep API itself, see the [Dreep docs](https://docs.dreep.cloud).
