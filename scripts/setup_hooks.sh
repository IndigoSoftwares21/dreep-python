#!/usr/bin/env bash
# One-time setup after cloning: dev environment plus the tracked git hooks.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -e . --group dev

chmod +x .githooks/* scripts/*.sh
git config core.hooksPath .githooks
echo "Hooks installed from .githooks/ (pre-commit, commit-msg, pre-push)."
