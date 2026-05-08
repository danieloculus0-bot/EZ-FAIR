from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import fitz

import extractor_engine as base
from extractor_engine import Characteristic, SkippedCandidate

TITLE_SKIP = re.compile(r"\b(?:UNLESS OTHERWISE|DECIMAL|FRACTION|ANGULAR|PROPRIETARY|TITLE|DWG|DRAWN|DATE|MATERIAL|THICKNESS|SCALE|WEIGHT|SHEET|REV|INITIALS|TOLERANCE|DO NOT SCALE)\b", re.I)
DIM_CONTEXT = base.DIMENSION_CONTEXT_PATTERN
DIM_RE = base.DIMENSION_PATTERN


def _decorated_raw(line: str, match: re.Match[str]) -> str:
    raw = match.group(0).replace("⌀", "Ø").replace("º", "°").strip()
    prefix = (match.group("prefix") or "").replace("⌀", "Ø").strip()
    suffix = (match.group("suffix") or "").replace("º", "°").strip()
    lookback = line[max(0, match.start() - 10):match.start()].replace("⌀", "Ø")
    if prefix.upper() == "R":
        return "R" + match.group("num")
    if "Ø" in prefix or re.search(r"Ø\s*$", lookback):
        return "Ø " + match.group("num")
    if suffix:
        return match.group("num") + suffix
    return raw


def classify_dimension(text: str, context: str = "") -> str:
    blob = f"{text or ''} {context or ''}"
    if "°" in blob or "º" in blob or re.search(r"\bdeg\.?\b", blob, re.I):
        return "°"
    if "Ø" in text or "⌀" in text or re.search(r"\b(?:DIA|DIAMETER)\b", blob, re.I):
        return "DIAMETER"
    if re.match(r"\s*[Rr]\s*\.?\d", text or "") or re.search(r"\b(?:RADIUS|RAD)\b", blob, re.I):
        return "RADIUS"
    if base.WELD_PATTERN.search(blob):
        return "WELD"
    return "LINEAR"


def _type_for_match(raw: str, line: str, near: str, match: re.Match[str]) -> str:
    """Classify with slot and thru-hole context.

    CAD PDFs often split the diameter symbol away from the number, so the plain
    numeric token can look linear. For hole/slot callouts, the first value in
    `.440 X 1.380 THRU` is the slot width/diameter-style characteristic, while
    the second value remains linear.
    """
    direct = classify_dimension(raw, line)
    if direct != "LINEAR":
        return direct

    before = line[max(0, match.start() - 14):match.start()]
    after = line[match.end():match.end() + 40]
    line_blob = line.replace("⌀", "Ø")
    near_blob = near.replace("⌀", "Ø")

    if re.search(r"Ø\s*$", before) or re.search(r"^\s*Ø", after):
        return "DIAMETER"
    if re.search(r"\b(?:DIA|DIAMETER)\b", f"{before} {after}", re.I):
        return "DIAMETER"

    has_thru = bool(re.search(r"\bTHRU\b", line_blob, re.I))
    is_second_x_value = bool(re.search(r"[Xx×]\s*$", before))
    is_first_x_value = bool(re.search(r"^\s*[Xx×]\s*\d", after))
    if has_thru and is_first_x_value:
        return "DIAMETER"
    if has_thru and not is_second_x_value and not re.search(r"[Xx×]", before):
        return "DIAMETER"

    # Last-resort local context check for PDFs that separate Ø into a nearby text span.
    # Keep this conservative so nearby title block junk does not turn every number into DIAMETER.
    if "Ø" in near_blob and re.search(r"\bTHRU\b", near_blob, re.I) and not is_second_x_value:
        return "DIAMETER"

    return "LINEAR"


def _center(rect: fitz.Rect) -> tuple[float, float]:
    return ((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)


def _duplicate(chars: list[Characteristic], page_i: int, typ: str, nominal: float, rect: fitz.Rect, source: str) -> bool:
    cx, cy = _center(rect)
    for c in chars:
        if c.page_index != page_i or c.type != typ or abs(c.nominal - nominal) > 0.000001:
            continue
        ox, oy = _center(fitz.Rect(c.rect))
        dist = math.hypot(cx - ox, cy - oy)
        if dist < 32:
            return True
        if source == c.metadata.get("source") and dist < 60:
            return True
    return False


def _title_noise(page: fitz.Page, rect: fitz.Rect, line: str, near: str) -> bool:
    blob = f"{line} {near}"
    if rect.y0 > page.rect.height * 0.70 and TITLE_SKIP.search(blob):
        return True
    if re.search(r"\b(?:TWO|THREE|ONE) PLACE DECIMAL\b", blob, re.I):
        return True
    if re.search(r"\bSHEET\s+\d+\s+(?:OF|/)\s+\d+\b", blob, re.I):
        return True
    return False


def _add(chars: list[Characteristic], skipped: list[SkippedCandidate], page: fitz.Page, page_i: int, raw: str, value: str, rect: fitz.Rect, line: str, near: str, comment: str, meta: dict[str, Any], forced_type: str | None = None) -> None:
    try:
        nominal = float(value)
    except Exception:
        base._record_skip(skipped, page_i, raw, "not numeric after parsing", rect, near)
        return
    if nominal <= 0:
        base._record_skip(skipped, page_i, raw, "zero or negative nominal", rect, near)
        return
    if _title_noise(page, rect, line, near):
        base._record_skip(skipped, page_i, raw, "title block / tolerance block text", rect, near)
        return
    reason = base._noise_reason(raw, value, line, near, page.rect, rect)
    if reason and "title block" not in reason:
        base._record_skip(skipped, page_i, raw, reason, rect, near)
        return
    typ = forced_type or classify_dimension(raw, line)
    if _duplicate(chars, page_i, typ, nominal, rect, line):
        base._record_skip(skipped, page_i, raw, "duplicate candidate at same location", rect, near)
        return
    lsl, usl = base.calculate_tolerance_limits(nominal, value, typ, f"{line} {near}")
    m = dict(meta)
    m.update({"source": line, "nearby": near})
    chars.append(Characteristic(len(chars) + 1, base._reference_location(page, rect, page_i), nominal, lsl, usl, typ, page_i, (rect.x0, rect.y0, rect.x1, rect.y1), raw, base.DEFAULT_TOOLING.get(typ, "CALIPER"), comment, "", m))


def extract_pdf_dimensions(pdf_path: str | Path) -> list[Characteristic]:
    pdf_path = Path(pdf_path)
    chars: list[Characteristic] = []
    skipped: list[SkippedCandidate] = []
    with fitz.open(pdf_path) as doc:
        full_text = "\n".join(p.get_text("text") for p in doc)
        comment = "AFTER GALVANIZE" if re.search(r"galvani[sz]e", full_text, re.I) else ""
        meta = {"drawing_name": pdf_path.stem}
        dwg = re.search(r"(?:DWG\.?\s*NO\.?|DRAWING\s*(?:NO|NUMBER)\.?)\s*[:#]?\s*([A-Z0-9_.\-]+)", full_text, re.I)
        rev = re.search(r"\bREV(?:ISION)?\b\s*[:#]?\s*([A-Z0-9_.\-]+)", full_text, re.I)
        if dwg:
            meta["drawing_no"] = dwg.group(1).strip()
        if rev:
            meta["revision"] = rev.group(1).strip()
        for page_i, page in enumerate(doc):
            before_count = len(chars)
            lines = list(base._line_groups(page))
            for line, line_rect, words in lines:
                if line_rect.y0 > page.rect.height * 0.70 and TITLE_SKIP.search(line):
                    base._record_skip(skipped, page_i, line, "title block line ignored", line_rect, line)
                    continue
                for match in DIM_RE.finditer(line):
                    raw = _decorated_raw(line, match)
                    value = match.group("num")
                    if base._is_count_prefix(line, match):
                        base._record_skip(skipped, page_i, raw, "quantity/count prefix, not a standalone dimension", line_rect, line)
                        continue
                    forced_type = _type_for_match(raw, line, "", match)
                    has_symbol = raw.startswith(("Ø", "R")) or forced_type == "DIAMETER" or bool((match.group("suffix") or "").strip())
                    if not ("." in value or has_symbol or DIM_CONTEXT.search(line) or base.TOLERANCE_PATTERN.search(line)):
                        base._record_skip(skipped, page_i, raw, "no decimal or dimension context", line_rect, line)
                        continue
                    rect = base._match_rect_from_words(line, line_rect, words, match)
                    near = base._nearby_text(page, rect)
                    forced_type = _type_for_match(raw, line, near, match)
                    _add(chars, skipped, page, page_i, raw, value, rect, line, near, comment, meta, forced_type)
            if len(chars) == before_count:
                for line, line_rect in base._iter_text_spans(page):
                    for match in DIM_RE.finditer(line):
                        raw = _decorated_raw(line, match)
                        rect = base._match_rect_from_words(line, line_rect, [], match)
                        near = base._nearby_text(page, rect)
                        forced_type = _type_for_match(raw, line, near, match)
                        _add(chars, skipped, page, page_i, raw, match.group("num"), rect, line, near, comment, meta, forced_type)
    for i, c in enumerate(chars, 1):
        c.char_number = i
    base.LAST_EXTRACTION_DEBUG["skipped"] = skipped
    return chars


def _expanded(rect: fitz.Rect, pad: float) -> fitz.Rect:
    return fitz.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad)


def _nearest(center: fitz.Point, rect: fitz.Rect) -> fitz.Point:
    return fitz.Point(min(max(center.x, rect.x0), rect.x1), min(max(center.y, rect.y0), rect.y1))


def _balloon_pos(page: fitz.Page, rect: fitz.Rect, radius: float, occupied: list[fitz.Rect]) -> fitz.Point:
    offsets = [(25, -15), (-25, -15), (25, 20), (-25, 20), (0, -28), (0, 28), (34, 0), (-34, 0)]
    anchors = [fitz.Point(rect.x1, rect.y0), fitz.Point(rect.x0, rect.y0), fitz.Point(rect.x1, rect.y1), fitz.Point(rect.x0, rect.y1)]
    for a in anchors:
        for dx, dy in offsets:
            p = fitz.Point(a.x + dx, a.y + dy)
            c = fitz.Rect(p.x - radius, p.y - radius, p.x + radius, p.y + radius)
            if page.rect.contains(c) and not c.intersects(_expanded(rect, 3)) and not any(c.intersects(o) for o in occupied):
                return p
    return fitz.Point(min(max(rect.x1 + 20, radius), page.rect.width - radius), min(max(rect.y0 - 16, radius), page.rect.height - radius))


def add_pdf_balloons(pdf_path: str | Path, characteristics: list[Characteristic], output_path: str | Path | None = None) -> Path:
    pdf_path = Path(pdf_path)
    output_path = Path(output_path) if output_path else pdf_path.with_name(f"{pdf_path.stem}_BALLOONED.pdf")
    if output_path.resolve() == pdf_path.resolve():
        raise ValueError("Ballooned PDF output cannot overwrite the original PDF.")
    with fitz.open(pdf_path) as doc:
        occupied: dict[int, list[fitz.Rect]] = {}
        for ch in characteristics:
            if ch.page_index < len(doc):
                occupied.setdefault(ch.page_index, []).append(_expanded(fitz.Rect(ch.rect), 4))
        for ch in characteristics:
            if ch.page_index >= len(doc):
                continue
            page = doc[ch.page_index]
            rect = fitz.Rect(ch.rect)
            radius = 8
            occ = occupied.setdefault(ch.page_index, [])
            center = _balloon_pos(page, rect, radius, occ)
            circle = fitz.Rect(center.x - radius, center.y - radius, center.x + radius, center.y + radius)
            page.draw_oval(circle, color=(1, 0, 0), fill=(1, 1, 1), width=0.85)
            page.insert_textbox(circle, str(ch.char_number), fontsize=6, fontname="helv", color=(1, 0, 0), align=fitz.TEXT_ALIGN_CENTER)
            page.draw_line(center, _nearest(center, rect), color=(1, 0, 0), width=0.35)
            occ.append(_expanded(circle, 5))
        doc.save(output_path, garbage=4, deflate=True)
    return output_path

get_last_skipped_candidates = base.get_last_skipped_candidates
write_debug_report = base.write_debug_report
TITLE_BLOCK_DEFAULTS = base.TITLE_BLOCK_DEFAULTS
TOLERANCE_PATTERN = base.TOLERANCE_PATTERN
