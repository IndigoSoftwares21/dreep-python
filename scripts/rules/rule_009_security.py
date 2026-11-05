"""RULE-009: no secrets, no plain-HTTP endpoints, no emoji in source.

Ported from vsured's ``verify_security.sh`` and ``check-rules.ts``: hardcoded
credentials, ``http://`` URLs other than localhost, and emoji (which break
terminals and grep) are rejected everywhere -- tests included, since a leaked
key in a test is still a leaked key.
"""

from __future__ import annotations

import re
from typing import ClassVar, Final

from rules.base import ERROR, BaseRule, FileContext, Severity, Violation

SECRET: Final = re.compile(
    r"AKIA[0-9A-Z]{16}"
    r"|sk_live_[0-9a-zA-Z]{24}"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|drp_live_[0-9A-Za-z]{16,}"
    r"|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"
)
PLAIN_HTTP: Final = re.compile(r"""['"]http://(?!localhost|127\.0\.0\.1|\[::1\])""")
EMOJI: Final = re.compile("[\U0001f300-\U0001faff☀-➿⬀-⯿️]")
SELF: Final = "scripts/rules/rule_009_security.py"

CHECKS: Final = (
    (SECRET, "Possible hardcoded credential."),
    (PLAIN_HTTP, "Plain-HTTP URL; use https."),
    (EMOJI, "Emoji in source."),
)


class Security(BaseRule):
    id: ClassVar[str] = "RULE-009"
    category: ClassVar[str] = "Security & Hygiene"
    severity: ClassVar[Severity] = ERROR
    description: ClassVar[str] = "No secrets, plain-HTTP URLs or emoji"
    remediation: ClassVar[str] = "Read credentials from the environment; use https; plain text."

    def check(self, file: FileContext) -> list[Violation]:
        if file.relative == SELF:
            return []
        return [
            self.violation(file, number, message)
            for number, line in enumerate(file.lines, start=1)
            for pattern, message in CHECKS
            if pattern.search(line)
        ]


RULE = Security()
