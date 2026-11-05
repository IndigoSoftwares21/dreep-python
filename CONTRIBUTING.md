# Contributing

## Setup

```bash
bash scripts/setup_hooks.sh
```

This creates `.venv`, installs the package with its dev group, and points git at the
tracked hooks in `.githooks/`.

## The quality gate

`bash scripts/quality_gate.sh` runs on every commit (pre-commit hook) and in CI, in
this order:

1. `scripts/unasync.py --check`: the generated sync client matches its async source
2. `ruff check` and `ruff format --check`
3. `scripts/verify_rules.py`: the repository rules listed below
4. `mypy --strict`
5. `pytest` with coverage of at least 90%

## Repository rules

| Rule | Checks | Severity |
| :- | :- | :- |
| RULE-001 | Module length: warn above 200 lines, fail above 400 | ERROR |
| RULE-002 | No barrel (re-export-only) modules | ERROR |
| RULE-003 | No `print()` or `breakpoint()` in the package | ERROR |
| RULE-004 | No magic strings (behavioural or repeated literals) | ERROR |
| RULE-005 | No duplicated six-line logic blocks | ERROR |
| RULE-006 | One definition per helper name | ERROR |
| RULE-007 | Layer boundaries: I/O only in the http and client layers | ERROR |
| RULE-008 | Names communicate intent | WARN |
| RULE-009 | No secrets, plain-HTTP URLs or emoji | ERROR |
| RULE-010 | Suppressions name their error code | ERROR |
| RULE-011 | Package modules are referenced by tests | WARN |

```bash
python scripts/verify_rules.py --rule=RULE-004
```

```bash
python scripts/verify_rules.py --strict
```

The baseline (`scripts/rules-baseline.json`) is a ratchet. More violations than it
records fails the gate, and fewer also fails until you lower it with `--update-baseline`.

## Changing the client

The async modules (`src/dreep/_async_*.py`) are the source of truth. After editing them,
regenerate the sync client:

```bash
python scripts/unasync.py
```

## Git conventions

- **Branches:** `feature/…`, `bugfix/…`, `hotfix/…`, `refactor/…`, `chore/…`, `docs/…`,
  `ci/…`, `release/…`. Lowercase kebab-case.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org), at most 100
  characters per line, signed.
- **`main` is protected.** The pre-push hook blocks direct pushes, force pushes and
  unsigned commits. Open a pull request.

## Releasing

1. Bump `src/dreep/_version.py` and add a section to `CHANGELOG.md`.
2. Merge to `main`, then push a `vX.Y.Z` tag. The release workflow builds the package
   and publishes it to PyPI through trusted publishing.
