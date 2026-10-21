"""Line-local association of explicit tolerance to its own nominal dimension.

Only an immediately following tolerance in the current dimension's segment is
accepted. Ambiguous or unattached tolerances are returned as review-required,
never silently borrowed from another characteristic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


SYMMETRIC = re.compile(r"(?:±|\+/-)\s*(?P<delta>\.?\d+(?:\.\d+)?)")


@dataclass(frozen=True)
class ToleranceAssociation:
    source: str  # explicit, default, unresolved
    lower: float | None = None
    upper: float | None = None
    reason: str = ""


def _tolerances(line, bilateral_pattern):
    matches = [(m.start(), m.end(), float(m.group("plus")), float(m.group("minus")))
               for m in bilateral_pattern.finditer(line)]
    matches += [(m.start(), m.end(), float(m.group("delta")), float(m.group("delta")))
                for m in SYMMETRIC.finditer(line)
                if not any(a < m.end() and m.start() < b for a, b, _, _ in matches)]
    return sorted(matches)


def nominal_matches(line, dimension_pattern, bilateral_pattern):
    """Exclude every tolerance component from the nominal candidate set."""
    tolerances = _tolerances(line, bilateral_pattern)
    return [m for m in dimension_pattern.finditer(line)
            if not any(a < m.end() and m.start() < b for a, b, _, _ in tolerances)]


def associate(line, nominal_match, nominals, bilateral_pattern, nominal):
    tolerances = _tolerances(line, bilateral_pattern)
    following = min((m.start() for m in nominals if m.start() > nominal_match.start()), default=len(line))
    between = [t for t in tolerances if nominal_match.end() <= t[0] < following]
    if len(between) == 1:
        start, _end, plus, minus = between[0]
        # No intervening words, other annotations, or numbers can be guessed.
        if not line[nominal_match.end():start].strip():
            return ToleranceAssociation(
                "explicit", round(nominal - minus, 6), round(nominal + plus, 6)
            )
        return ToleranceAssociation("unresolved", reason="text between dimension and tolerance")
    if len(between) > 1:
        return ToleranceAssociation("unresolved", reason="multiple plausible tolerances")
    if tolerances:
        return ToleranceAssociation("unresolved", reason="tolerance on line belongs elsewhere or is unattached")
    return ToleranceAssociation("default")
