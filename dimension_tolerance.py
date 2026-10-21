"""Attach explicit tolerances to the actual nominal on an annotation line.

Never give every number on a line the first tolerance found on that line.
A missing or ambiguous association falls back to drawing defaults and carries
an explicit review flag. All extraction results remain human-review candidates.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


_BILATERAL = re.compile(
    r"\+\s*(?P<plus>\.?\d+(?:\.\d+)?)\s*/?\s*-\s*(?P<minus>\.?\d+(?:\.\d+)?)"
)
_SYMMETRIC = re.compile(r"±\s*(?P<tol>\.?\d+(?:\.\d+)?)")


@dataclass(frozen=True)
class BoundDimension:
    match: re.Match[str]
    context: str
    status: str  # explicit, default, or review_required


def bind_tolerances(line: str, dimension_pattern: re.Pattern[str]) -> list[BoundDimension]:
    """Recognize tolerances, exclude their components as nominals, and bind leftward.

    Bilateral (+a/-b) and symmetric (±a) tolerances attach only when immediately
    following one nominal with punctuation/whitespace separators. A tolerance
    before a nominal, intervening words, or repeated tolerance groups is
    ambiguous and must be reviewed; no tolerance is silently borrowed.
    """
    groups: list[tuple[int, int, str]] = [
        (m.start(), m.end(), m.group(0)) for m in _BILATERAL.finditer(line)
    ]
    groups += [
        (m.start(), m.end(), f"+{m.group('tol')} -{m.group('tol')}")
        for m in _SYMMETRIC.finditer(line)
        if not any(x <= m.start() < y for x, y, _ in groups)
    ]
    groups.sort(key=lambda item: item[0])

    nominals = [
        m for m in dimension_pattern.finditer(line)
        if not any(m.start() < end and m.end() > start for start, end, _ in groups)
    ]
    bound: dict[int, str] = {}
    conflicts: set[int] = set()
    unassigned = False
    for start, _end, normalized in groups:
        previous = [m for m in nominals if m.end() <= start]
        if not previous:
            unassigned = True
            continue
        candidate = previous[-1]
        separating = line[candidate.end():start]
        if not re.fullmatch(r"[\s,;:()]*", separating):
            unassigned = True
            continue
        key = candidate.start()
        if key in bound:
            conflicts.add(key)
        else:
            bound[key] = normalized

    output: list[BoundDimension] = []
    for m in nominals:
        key = m.start()
        if key in conflicts or unassigned:
            # Do not trust the line's explicit tolerances when association is
            # unresolved. A human must decide, instead of inheriting a neighbor.
            output.append(BoundDimension(m, "", "review_required"))
        elif key in bound:
            output.append(BoundDimension(m, bound[key], "explicit"))
        else:
            output.append(BoundDimension(m, "", "default"))
    return output
