from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import fitz

import extractor_engine as base
import extractor_precision_patch as prev
from extractor_engine import Characteristic, SkippedCandidate

FRACTION_RE = re.compile(r"(?<![A-Za-z0-9])(?:(?P<whole>\d+)\s+)?(?P<num>\d+)\s*/\s*(?P<den>\d+)(?![A-Za-z0-9])")
COMMON_DENOMINATORS = {2, 4, 8, 16, 32, 64}
WELD_FEATURE_RE = re.compile(r"\b(?:WELD|FILLET|SEAM|BEAD|TACK|STITCH|PLUG\s+WELD|SPOT\s+WELD|CONTINUOUS|ALL\s+AROUND)\b|[△⌒⏊]", re.I)
TITLE_SKIP = re.compile(r"\b(?:UNLESS OTHERWISE|DECIMAL|FRACTION|ANGULAR|PROPRIETARY|TITLE|DWG|DRAWN|DATE|MATERIAL|THICKNESS|SCALE|WEIGHT|SHEET|REV|INITIALS|TOLERANCE|DO NOT SCALE)\b", re.I)


def classify_dimension(text: str, context: str = "") -> str:
    return prev.classify_dimension(text, context)


def _center(rect: fitz.Rect) -> tuple[float, float]:
    return ((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)


def _match_rect_from_chars(line_text: str, line_rect: fitz.Rect, match: re.Match[str]) -> fitz.Rect:
    ratio0 = match.start() / max(len(line_text), 1)
    ratio1 = match.end() / max(len(line_text), 1)
    x0 = line_rect.x0 + line_rect.width * ratio0
    x1 = line_rect.x0 + line_rect.width * ratio1
    return fitz.Rect(x0, line_rect.y0, max(x1, x0 + 12), line_rect.y1)


def _fraction_value(match: re.Match[str]) -> float | None:
    whole = int(match.group("whole") or 0)
    numerator = int(match.group("num"))
    denominator = int(match.group("den"))
    if denominator == 0 or denominator not in COMMON_DENOMINATORS:
        return None
    if numerator >= denominator and whole == 0:
        return None
    return whole + numerator / denominator


def _is_fraction_noise(line: str, page: fitz.Page, rect: fitz.Rect) -> bool:
    blob = line.strip()
    if rect.y0 > page.rect.height * 0.70 and TITLE_SKIP.search(blob):
        return True
    if re.search(r"\bSHEET\s+\d+\s*(?:OF|/)\s*\d+\b", blob, re.I):
        return True
    if re.search(r"\bPAGE\s+\d+\s*(?:OF|/)\s*\d+\b", blob, re.I):
        return True
    if re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", blob):
        return True
    if re.search(r"\b(?:SCALE|DATE|REV|DWG|DRAWING|TITLE|TOLERANCE)\b", blob, re.I) and not base.DIMENSION_CONTEXT_PATTERN.search(blob):
        return True
    return False


def _is_close_duplicate(chars: list[Characteristic], page_i: int, typ: str, nominal: float, rect: fitz.Rect) -> bool:
    cx, cy = _center(rect)
    for char in chars:
        if char.page_index != page_i or char.type != typ:
            continue
        try:
            existing_nominal = float(char.nominal)
        except Exception:
            continue
        if abs(existing_nominal - nominal) > 0.000001:
            continue
        ox, oy = _center(fitz.Rect(char.rect))
        if math.hypot(cx - ox, cy - oy) < 42:
            return True
    return False


def _weld_duplicate(chars: list[Characteristic], page_i: int, rect: fitz.Rect, source: str) -> bool:
    cx, cy = _center(rect)
    for char in chars:
        if char.page_index != page_i or char.type != "WELD":
            continue
        if source and source == char.metadata.get("source"):
            return True
        ox, oy = _center(fitz.Rect(char.rect))
        if math.hypot(cx - ox, cy - oy) < 55:
            return True
    return False


def _metadata(pdf_path: Path, full_text: str) -> dict[str, str]:
    meta: dict[str, str] = {"drawing_name": pdf_path.stem}
    dwg = re.search(r"(?:DWG\.?\s*NO\.?|DRAWING\s*(?:NO|NUMBER)\.?)\s*[:#]?\s*([A-Z0-9_.\-]+)", full_text, re.I)
    rev = re.search(r"\bREV(?:ISION)?\b\s*[:#]?\s*([A-Z0-9_.\-]+)", full_text, re.I)
    if dwg:
        meta["drawing_no"] = dwg.group(1).strip()
    if rev:
        meta["revision"] = rev.group(1).strip()
    return meta


def _add_fraction(chars: list[Characteristic], skipped: list[SkippedCandidate], page: fitz.Page, page_i: int, line: str, line_rect: fitz.Rect, match: re.Match[str], comment: str, meta: dict[str, Any]) -> None:
    value = _fraction_value(match)
    raw = match.group(0).strip()
    rect = _match_rect_from_chars(line, line_rect, match)
    if value is None:
        base._record_skip(skipped, page_i, raw, "fraction denominator/noise not supported", rect, line)
        return
    if _is_fraction_noise(line, page, rect):
        base._record_skip(skipped, page_i, raw, "fraction-like title block/admin text", rect, line)
        return
    near = base._nearby_text(page, rect)
    typ = prev.classify_dimension(raw, f"{line} {near}")
    if typ == "WELD":
        typ = "LINEAR"
    if _is_close_duplicate(chars, page_i, typ, value, rect):
        base._record_skip(skipped, page_i, raw, "duplicate fraction candidate", rect, near)
        return
    # Fractions are commonly shop dimensions. Use a visible guessed fractional tolerance and flag it for review.
    explicit = base.TOLERANCE_PATTERN.search(line)
    if explicit:
        lsl, usl = base.calculate_tolerance_limits(value, f"{value:.4f}", typ, line)
        extra_comment = comment
    else:
        tol = 1 / 32
        lsl, usl = round(value - tol, 6), round(value + tol, 6)
        extra_comment = (comment + " | " if comment else "") + "FRACTION - VERIFY TOLERANCE"
    m = dict(meta)
    m.update({"source": line, "nearby": near, "fraction_value": raw})
    chars.append(Characteristic(len(chars) + 1, base._reference_location(page, rect, page_i), value, lsl, usl, typ, page_i, (rect.x0, rect.y0, rect.x1, rect.y1), raw, base.DEFAULT_TOOLING.get(typ, "CALIPER"), extra_comment, "", m))


def _add_weld_feature(chars: list[Characteristic], skipped: list[SkippedCandidate], page: fitz.Page, page_i: int, line: str, rect: fitz.Rect, comment: str, meta: dict[str, Any]) -> None:
    clean = " ".join(line.split())
    if not clean:
        return
    if rect.y0 > page.rect.height * 0.70 and TITLE_SKIP.search(clean):
        base._record_skip(skipped, page_i, clean, "weld text in title/admin block", rect, clean)
        return
    if base.DIMENSION_PATTERN.search(clean) or FRACTION_RE.search(clean):
        return
    if _weld_duplicate(chars, page_i, rect, clean):
        base._record_skip(skipped, page_i, clean, "duplicate weld feature", rect, clean)
        return
    m = dict(meta)
    m.update({"source": clean, "nearby": clean})
    chars.append(Characteristic(len(chars) + 1, base._reference_location(page, rect, page_i), "SEE PRINT", "", "", "WELD", page_i, (rect.x0, rect.y0, rect.x1, rect.y1), "WELD SYMBOL", "VISUAL", (comment + " | " if comment else "") + clean[:120], "", m))


def extract_pdf_dimensions(pdf_path: str | Path) -> list[Characteristic]:
    pdf_path = Path(pdf_path)
    chars = prev.extract_pdf_dimensions(pdf_path)
    skipped = list(base.LAST_EXTRACTION_DEBUG.get("skipped", []))

    with fitz.open(pdf_path) as doc:
        full_text = "\n".join(page.get_text("text") for page in doc)
        comment = "AFTER GALVANIZE" if re.search(r"galvani[sz]e", full_text, re.I) else ""
        meta = _metadata(pdf_path, full_text)
        for page_i, page in enumerate(doc):
            for line, line_rect, _words in base._line_groups(page):
                if WELD_FEATURE_RE.search(line):
                    _add_weld_feature(chars, skipped, page, page_i, line, line_rect, comment, meta)
                for match in FRACTION_RE.finditer(line):
                    _add_fraction(chars, skipped, page, page_i, line, line_rect, match, comment, meta)
            # Span fallback catches some CAD PDFs where fraction glyphs or weld symbols are split oddly.
            for line, line_rect in base._iter_text_spans(page):
                if WELD_FEATURE_RE.search(line):
                    _add_weld_feature(chars, skipped, page, page_i, line, line_rect, comment, meta)
                for match in FRACTION_RE.finditer(line):
                    _add_fraction(chars, skipped, page, page_i, line, line_rect, match, comment, meta)

    for i, char in enumerate(chars, 1):
        char.char_number = i
        char.metadata.setdefault("drawing_name", pdf_path.stem)
    base.LAST_EXTRACTION_DEBUG["skipped"] = skipped
    return chars

add_pdf_balloons = prev.add_pdf_balloons
get_last_skipped_candidates = base.get_last_skipped_candidates
write_debug_report = base.write_debug_report
TITLE_BLOCK_DEFAULTS = base.TITLE_BLOCK_DEFAULTS
TOLERANCE_PATTERN = base.TOLERANCE_PATTERN
