#!/usr/bin/env bash
# The full quality gate: run by the pre-commit hook and by CI.
# Cheap checks first, then analysis, then tests. Never bypass with --no-verify.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY="python"

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

step "Generated sync client is up to date"
"$PY" scripts/unasync.py --check

step "Lint (ruff)"
"$PY" -m ruff check src tests scripts examples

step "Format (ruff)"
"$PY" -m ruff format --check src tests scripts examples

step "Repository rules (scripts/verify_rules.py)"
"$PY" scripts/verify_rules.py --summary

step "Types (mypy --strict)"
"$PY" -m mypy

step "Tests (pytest, coverage >= 90%)"
"$PY" -m pytest -q --cov --cov-report=term-missing:skip-covered

printf '\n\033[32mQuality gate passed.\033[0m\n'
