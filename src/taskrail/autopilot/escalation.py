"""The escalation reasons `autopilot status` computes (DESIGN.md §12.6): governing paths touched and escalated gates.

The other reasons of §12.6 — decisions reserved to humans, contradicting lanes, conflicts outside the
known classes, false premises, diverged bases — stay the orchestrator's judgement.
"""

from __future__ import annotations

import re
from functools import lru_cache

from taskrail.autopilot.runs import GATE_STATES  # a lane in these states is stopped at a gate
from taskrail.config import AutopilotConfig


@lru_cache(maxsize=256)
def _compile(pattern: str) -> re.Pattern:
    """A `governing` entry as a regular expression over repository-relative paths.

    `*` and `?` stay within one path segment, `**` crosses segments (`**/` also matches no
    directory), `[…]` is a character class (`[!…]` negated). The entry matches a path or any of its
    leading directories, so `docs/adr` covers everything below it.
    """
    while pattern.startswith("./"):
        pattern = pattern[2:]
    pattern = pattern.rstrip("/")
    out: list[str] = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if pattern.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif char == "*":
            out.append("[^/]*")
            index += 1
        elif char == "?":
            out.append("[^/]")
            index += 1
        elif char == "[" and (end := pattern.find("]", index + 2)) != -1:
            body = pattern[index + 1 : end]
            negated = body.startswith("!")
            body = body[1:] if negated else body
            body = body.replace("\\", "\\\\")
            if not negated and body.startswith("^"):
                body = "\\" + body  # a literal caret, as in the shell
            out.append("[" + ("^/" if negated else "") + body + "]")
            index = end + 1
        else:
            out.append(re.escape(char))
            index += 1
    return re.compile("".join(out) + "(?:/.*)?", re.DOTALL)


def matches(pattern: str, path: str) -> bool:
    """Whether a `governing` entry covers a repository-relative path (letter case counts)."""
    return _compile(pattern).fullmatch(path) is not None


def governing_touched(touched: list[str], governing: tuple[str, ...]) -> list[str]:
    return sorted(path for path in touched if any(matches(pattern, path) for pattern in governing))


def flags(kind: str | None, state: str | None, gate: str | None, touched: list[str], autopilot: AutopilotConfig) -> dict:
    """The escalation fields of one task row in `autopilot status`."""
    governing = governing_touched(touched, autopilot.governing)
    escalate_gate = None
    if state in GATE_STATES and kind and gate and f"{kind}:{gate}" in autopilot.escalate_gates:
        escalate_gate = f"{kind}:{gate}"
    reasons = (["governing"] if governing else []) + (["escalate-gate"] if escalate_gate else [])
    return {"governing_touched": governing, "escalate_gate": escalate_gate, "escalation": reasons}
