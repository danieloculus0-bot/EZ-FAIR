"""Deterministic manufacturing requirement parsing for EZ FAIR.

This module classifies common drawing callouts and resolves explicit limits without
pretending to understand feature-control frames. GD&T remains a separate control.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

NUM = r"(?:\d+(?:\.\d+)?|\.\d+)"
SYMMETRIC = re.compile(rf"(?P<nom>{NUM})\s*(?:±|\+/-)\s*(?P<tol>{NUM})", re.I)
ASYMMETRIC = re.compile(rf"(?P<nom>{NUM})\s*\+\s*(?P<plus>{NUM})\s*(?:/|\s)\s*-\s*(?P<minus>{NUM})", re.I)
PLUS_ONLY = re.compile(rf"(?P<nom>{NUM})\s*\+\s*(?P<plus>{NUM})(?!\s*(?:/|-)\s*{NUM})", re.I)
MINUS_ONLY = re.compile(rf"(?P<nom>{NUM})\s*-\s*(?P<minus>{NUM})(?!\s*(?:TO|THRU)\s*{NUM})", re.I)
LIMITS = re.compile(rf"(?P<low>{NUM})\s*(?:–|—|\bTO\b|\bTHRU\b)\s*(?P<high>{NUM})", re.I)
MAXIMUM = re.compile(rf"(?P<value>{NUM})\s*MAX\b", re.I)
MINIMUM = re.compile(rf"(?P<value>{NUM})\s*MIN\b", re.I)


@dataclass(frozen=True)
class ParsedRequirement:
    feature_type: str
    nominal: Decimal | None = None
    lsl: Decimal | None = None
    usl: Decimal | None = None
    quantity: int = 1
    explicit_tolerance: bool = False
    reference_only: bool = False
    basic: bool = False
    warnings: tuple[str, ...] = ()


def _d(value: str) -> Decimal:
    return Decimal(value)


def classify_feature(text: str) -> str:
    value = (text or "").upper().replace("º", "°")
    if re.search(r"\b(?:SPHERICAL\s+RADIUS|SR)\s*" + NUM, value):
        return "SPHERICAL RADIUS"
    if re.search(r"(?:Ø|⌀|\bDIA\.?\b|\bDIAMETER\b)\s*" + NUM, value):
        return "DIAMETER"
    if re.search(r"(?:\bR\s*" + NUM + r"|\bRADIUS\b)", value):
        return "RADIUS"
    if "°" in value or re.search(r"\bDEG(?:REE)?S?\b", value):
        return "ANGLE"
    if re.search(r"\b(?:C'?BORE|COUNTERBORE)\b|⌴", value):
        return "COUNTERBORE"
    if re.search(r"\b(?:C'?SINK|COUNTERSINK)\b|⌵", value):
        return "COUNTERSINK"
    if re.search(r"\b(?:DEPTH|DEEP)\b|↧", value):
        return "DEPTH"
    if re.search(r"\b(?:UNC|UNF|UNEF|NPT|BSPP?|ACME|THREAD|THD)\b|\d+\s*-\s*\d+", value):
        return "THREAD"
    if re.search(r"\bCHAMFER\b|" + NUM + r"\s*[X×]\s*45\s*°", value):
        return "CHAMFER"
    if re.search(r"\bSURFACE\s+FINISH\b|\bRA\b|√", value):
        return "SURFACE FINISH"
    if re.search(r"\bWELD|FILLET|SEAM\b", value):
        return "WELD"
    return "LINEAR"


def parse_requirement(text: str) -> ParsedRequirement:
    normalized = " ".join((text or "").replace(",", ".").split())
    upper = normalized.upper()
    quantity_match = re.search(r"(?:^|\s)(?P<qty>\d+)\s*[X×](?:\s|$)", upper)
    quantity = int(quantity_match.group("qty")) if quantity_match else 1
    reference = bool(re.search(r"\bREF(?:ERENCE)?\b", upper) or re.search(r"\(\s*" + NUM + r"\s*\)", upper))
    basic = bool(re.search(r"\[\s*" + NUM + r"\s*\]", upper))
    feature_type = classify_feature(normalized)

    match = ASYMMETRIC.search(normalized)
    if match:
        nominal = _d(match.group("nom"))
        return ParsedRequirement(feature_type, nominal, nominal - _d(match.group("minus")), nominal + _d(match.group("plus")), quantity, True, reference, basic)
    match = SYMMETRIC.search(normalized)
    if match:
        nominal = _d(match.group("nom")); tol = _d(match.group("tol"))
        return ParsedRequirement(feature_type, nominal, nominal - tol, nominal + tol, quantity, True, reference, basic)
    match = LIMITS.search(normalized)
    if match:
        low, high = _d(match.group("low")), _d(match.group("high"))
        if low > high:
            low, high = high, low
        return ParsedRequirement(feature_type, None, low, high, quantity, True, reference, basic)
    match = MAXIMUM.search(normalized)
    if match:
        return ParsedRequirement(feature_type, None, None, _d(match.group("value")), quantity, True, reference, basic)
    match = MINIMUM.search(normalized)
    if match:
        return ParsedRequirement(feature_type, None, _d(match.group("value")), None, quantity, True, reference, basic)
    match = PLUS_ONLY.search(normalized)
    if match:
        nominal = _d(match.group("nom"))
        return ParsedRequirement(feature_type, nominal, nominal, nominal + _d(match.group("plus")), quantity, True, reference, basic)
    match = MINUS_ONLY.search(normalized)
    if match:
        nominal = _d(match.group("nom"))
        return ParsedRequirement(feature_type, nominal, nominal - _d(match.group("minus")), nominal, quantity, True, reference, basic)

    nominal_match = re.search(NUM, normalized)
    nominal = None
    if nominal_match:
        try:
            nominal = _d(nominal_match.group(0))
        except InvalidOperation:
            nominal = None
    warnings = ("Basic dimension must not receive title-block limits.",) if basic else ()
    return ParsedRequirement(feature_type, nominal, None, None, quantity, False, reference, basic, warnings)
