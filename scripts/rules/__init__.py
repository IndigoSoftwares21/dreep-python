"""Registry of repository rules. One module per rule: ``rule_NNN_<name>.py``.

Each rule module exposes ``RULE``. Rules are discovered by filename, so adding
a rule means adding one file -- nothing else to keep in sync.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Final

from rules.base import Rule

_PREFIX: Final = "rule_"


def load_rules() -> list[Rule]:
    """Fresh instances of every rule, in id order (project rules keep state)."""
    names = sorted(m.name for m in pkgutil.iter_modules(__path__) if m.name.startswith(_PREFIX))
    return [importlib.reload(importlib.import_module(f"{__name__}.{name}")).RULE for name in names]
