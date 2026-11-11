"""Native-PDF + offline OCR evidence reconciliation for the desktop FAI tools.

Both extraction paths run independently on EVERY PDF when OCR is enabled.
A failed or overlapping OCR result can never erase a native PDF dimension.
Corroboration is explicitly not a claim that the extracted print is correct.
All FAI outputs require operator verification against the customer drawing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import extractor_active as native


def _center(characteristic: Any) -> tuple[float, float]:
    x0, y0, x1, y1 = characteristic.rect
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def _nearby(a: Any, b: Any) -> bool:
    if a.page_index != b.page_index:
        return False
    ax, ay = _center(a)
    bx, by = _center(b)
    aw, ah = abs(a.rect[2] - a.rect[0]), abs(a.rect[3] - a.rect[1])
    bw, bh = abs(b.rect[2] - b.rect[0]), abs(b.rect[3] - b.rect[1])
    # OCR boxes often shift 10-20 points relative to native CAD text, while
    # measurements repeated elsewhere on a drawing are usually much farther
    # apart. Bound this tolerance so unrelated annotations never merge.
    max_dx = max(11.0, min(26.0, (aw + bw) / 2))
    max_dy = max(11.0, min(18.0, (ah + bh) / 2 + 5.0))
    return abs(ax - bx) <= max_dx and abs(ay - by) <= max_dy


def _same_nominal(a: Any, b: Any) -> bool:
    try:
        return abs(float(a.nominal) - float(b.nominal)) <= 0.0001
    except (TypeError, ValueError):
        return str(a.nominal) == str(b.nominal)


def _same_limits(a: Any, b: Any) -> bool:
    try:
        return abs(float(a.lsl) - float(b.lsl)) <= 0.0001 and abs(float(a.usl) - float(b.usl)) <= 0.0001
    except (TypeError, ValueError):
        return a.lsl == b.lsl and a.usl == b.usl


def _flag_review(characteristic: Any, reason: str) -> None:
    characteristic.metadata["review_required"] = True
    characteristic.metadata["tolerance_review_required"] = True
    characteristic.metadata["evidence_status"] = "review_required"
    previous = str(characteristic.metadata.get("extraction_conflicts", ""))
    characteristic.metadata["extraction_conflicts"] = "; ".join(filter(None, [previous, reason]))
    note = "REVIEW: " + reason
    if note not in characteristic.comments:
        characteristic.comments = (characteristic.comments + " | " if characteristic.comments else "") + note


def _as_native(characteristic: Any) -> native.Characteristic:
    """Avoid coupling UI data records to the legacy OCR extractor class."""
    return native.Characteristic(
        char_number=characteristic.char_number,
        reference_location=characteristic.reference_location,
        nominal=characteristic.nominal,
        lsl=characteristic.lsl,
        usl=characteristic.usl,
        type=characteristic.type,
        page_index=characteristic.page_index,
        rect=tuple(characteristic.rect),
        raw_text=characteristic.raw_text,
        tooling=characteristic.tooling,
        comments=characteristic.comments,
        actual=getattr(characteristic, "actual", ""),
        metadata=dict(getattr(characteristic, "metadata", {}) or {}),
    )


def reconcile_characteristics(
    vector_candidates: list[Any], ocr_candidates: list[Any]
) -> list[native.Characteristic]:
    """Retain all distinct findings; combine only near-coincident evidence.

    Matching coordinates with differing text/numbers are flagged, not silently
    discarded. An OCR-only finding is retained for human confirmation.
    """
    results = [_as_native(item) for item in vector_candidates]
    for item in results:
        item.metadata["extraction_paths"] = ["native_pdf"]
        item.metadata["evidence_status"] = "single_source"
        item.metadata.setdefault("extraction", "VECTOR")

    for raw_ocr in ocr_candidates:
        ocr = _as_native(raw_ocr)
        ocr.metadata["extraction"] = "OCR"
        near = [item for item in results if "native_pdf" in item.metadata.get("extraction_paths", []) and _nearby(item, ocr)]
        matching = [item for item in near if _same_nominal(item, ocr)]
        if matching:
            chosen = min(matching, key=lambda item: sum(abs(a - b) for a, b in zip(_center(item), _center(ocr))))
            if "ocr" not in chosen.metadata["extraction_paths"]:
                chosen.metadata["extraction_paths"].append("ocr")
            chosen.metadata["ocr_source"] = ocr.metadata.get("source", ocr.raw_text)
            chosen.metadata["ocr_tolerance_status"] = ocr.metadata.get("tolerance_status", "unknown")
            if chosen.type != ocr.type:
                _flag_review(chosen, f"native/OCR feature type differs: {chosen.type} vs {ocr.type}")
            vector_status = chosen.metadata.get("tolerance_status", "unknown")
            ocr_status = ocr.metadata.get("tolerance_status", "unknown")
            if vector_status == "explicit" and ocr_status == "explicit":
                if _same_limits(chosen, ocr):
                    chosen.metadata["tolerance_evidence"] = "both_paths_agree"
                else:
                    _flag_review(chosen, "native/OCR explicit tolerance limits disagree")
            elif ocr_status == "explicit" and vector_status != "explicit":
                # Optical inference alone is not sufficient to replace a
                # source calculation. Keep both proposals visible for review.
                chosen.metadata["ocr_proposed_limits"] = (ocr.lsl, ocr.usl)
                _flag_review(chosen, "OCR found a tolerance not confirmed by native text")
            elif vector_status == "explicit":
                chosen.metadata["tolerance_evidence"] = "native_explicit"
            elif not _same_limits(chosen, ocr):
                _flag_review(chosen, "native/OCR inferred tolerance limits differ")
            if not chosen.metadata.get("review_required"):
                chosen.metadata["evidence_status"] = "corroborated"
            continue

        if near:
            for prior in near:
                _flag_review(prior, "OCR reads a different nominal at the same drawing location")
            _flag_review(ocr, "OCR nominal differs from native PDF at the same drawing location")
            ocr.metadata["extraction_paths"] = ["ocr"]
        else:
            _flag_review(ocr, "OCR-only characteristic needs drawing confirmation")
            ocr.metadata["extraction_paths"] = ["ocr"]
        results.append(ocr)

    for index, item in enumerate(results, start=1):
        item.char_number = index
    return results


def _title_block_top(page: Any) -> float | None:
    """Find an explicitly labeled bottom title block using native PDF text.

    A lower-page numerical dimension remains eligible unless at least two
    distinct document-admin markers establish a title block. Restrict the
    cutoff to the bottom 28% to protect low-positioned detail views.
    """
    import re

    markers: dict[str, float] = {}
    doc_terms = (
        ("proprietary", r"\bPROPRIETARY\b"),
        ("drawing_id", r"\b(?:DWG|DRAWING)\s*(?:NO|NUMBER)\b"),
        ("sheet", r"\bSHEET\b"),
        ("scale", r"\bSCALE\b"),
        ("approval", r"\b(?:DRAWN|APPROVED)\b"),
        ("title", r"\bTITLE\s*:"),
        ("general_tolerances", r"\b(?:UNLESS\s+OTHERWISE|TWO\s+PLACE|THREE\s+PLACE|DECIMAL\s+TOLERANCE)\b"),
    )
    min_start = page.rect.height * 0.72
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            text = " ".join(str(span.get("text", "")) for span in line.get("spans", []))
            top = float(line.get("bbox", (0, 0, 0, 0))[1])
            if top < min_start:
                continue
            for key, pattern in doc_terms:
                if re.search(pattern, text, re.I):
                    markers[key] = min(markers.get(key, top), top)
    if len(markers) < 2:
        return None
    return max(min_start, min(markers.values()) - 8)


def _remove_title_block_candidates(
    pdf_path: Path,
    vector_candidates: list[Any],
    ocr_candidates: list[Any],
) -> tuple[list[Any], list[Any]]:
    """Do not balloon numeric values from explicitly identified title blocks."""
    import pymupdf as fitz

    with fitz.open(pdf_path) as doc:
        cutoff_by_page = {i: _title_block_top(page) for i, page in enumerate(doc)}

    def keep(candidate: Any) -> bool:
        cutoff = cutoff_by_page.get(candidate.page_index)
        return cutoff is None or float(candidate.rect[1]) < cutoff

    return [item for item in vector_candidates if keep(item)], [
        item for item in ocr_candidates if keep(item)
    ]


def extract_pdf_dimensions_hybrid(pdf_path: str | Path, settings: Any = None) -> list[native.Characteristic]:
    """Read native PDF and OCR independently, then reconcile by evidence."""
    from ez_fair_enhancements import (
        ExtractionSettings, _extract_from_ocr, detect_title_block_defaults,
        extract_gdt_characteristics,
    )
    import ez_fai_builder as legacy
    import extractor_engine

    settings = settings or ExtractionSettings.load()
    source = Path(pdf_path)
    title_conflicts = {}
    if settings.auto_detect_title_block:
        try:
            detected = detect_title_block_defaults(source, settings)
            for key, value in detected.items():
                setattr(settings, key, value)
        except (RuntimeError, OSError) as exc:
            # Native text and its drawing information must survive missing OCR.
            title_conflicts["title_block_ocr"] = str(exc)
    defaults = {
        "two_place": float(settings.two_place),
        "three_place": float(settings.three_place),
        "angular": float(settings.angular),
    }
    legacy.TITLE_BLOCK_DEFAULTS.update(defaults)
    extractor_engine.TITLE_BLOCK_DEFAULTS.update(defaults)
    vectors = native.extract_pdf_dimensions(source)
    ocrs: list[Any] = []
    ocr_error = ""
    if settings.enable_ocr_fallback:
        try:
            # Always run OCR; never gate it on len(vectors) == 0.
            ocrs = _extract_from_ocr(source, settings)
        except (RuntimeError, OSError) as exc:
            ocr_error = str(exc)
    if not vectors and not ocrs and ocr_error:
        raise RuntimeError(ocr_error)
    # Preserve title-block tolerance text for default detection, but never
    # promote its numeric fragments to inspection/balloon characteristics.
    vectors, ocrs = _remove_title_block_candidates(source, vectors, ocrs)
    combined = reconcile_characteristics(vectors, ocrs)
    try:
        gdts = extract_gdt_characteristics(source, len(combined) + 1, settings)
    except (RuntimeError, OSError):
        gdts = []
    for candidate in gdts:
        extra = _as_native(candidate)
        if any(_nearby(extra, old) and extra.type == old.type for old in combined):
            continue
        extra.metadata["extraction_paths"] = ["gdt_scan"]
        _flag_review(extra, "GD&T candidate needs feature-control-frame confirmation")
        combined.append(extra)
    for index, item in enumerate(combined, start=1):
        item.char_number = index
        item.metadata.setdefault("drawing_name", source.stem)
        item.metadata["title_block_defaults"] = dict(defaults)
        item.metadata["vector_characteristics"] = len(vectors)
        item.metadata["ocr_characteristics"] = len(ocrs)
        if ocr_error:
            item.metadata["ocr_unavailable"] = ocr_error
        if title_conflicts:
            item.metadata["title_detection_warnings"] = title_conflicts
    return combined
