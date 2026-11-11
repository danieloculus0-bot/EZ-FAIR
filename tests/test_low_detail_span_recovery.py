"""Regression for dimension callouts exposed only as CAD PDF text spans.

Synthetic test geometry, not employer/customer drawings. It reproduces a
mixed-word/span page where the main 17.000 dimension is a parsed word but
.480 and R.320 below the side view must still be recovered and ballooned.
"""
from __future__ import annotations

import pymupdf as fitz
import extractor_precision_patch as precision
from hybrid_extraction import extract_pdf_dimensions_hybrid
from ez_fair_enhancements import ExtractionSettings


def make_synthetic_drawing(tmp_path):
    source = tmp_path / "generic-bent-part.pdf"
    with fitz.open() as book:
        page = book.new_page(width=792, height=612)
        page.insert_text((110, 100), "17.000", fontsize=12)
        page.insert_text((185, 456), "3.390", fontsize=12)
        # Lower view beside the title block, where previously lost:
        page.insert_text((250, 478), ".480", fontsize=12)
        page.insert_text((388, 478), "R.320", fontsize=12)
        # Date is nearby, but is *not* part of these dimensions.
        page.insert_text((380, 533), "DATE 05-12-2020", fontsize=9)
        page.insert_text((380, 556), "TITLE: GENERIC SAMPLE", fontsize=9)
        page.insert_text((380, 575), "SCALE 1:2", fontsize=9)
        book.save(source)
    return source


def test_low_detail_span_candidates_survive_when_word_parser_finds_other_dims(
    tmp_path, monkeypatch
):
    source = make_synthetic_drawing(tmp_path)
    original_words = precision.base._line_groups

    def incomplete_words(page):
        # Mimic CAD PDF word extraction that succeeds on several dimensions
        # but fails to tokenize lower side-view text.
        for line, rect, words in original_words(page):
            if "17.000" in line or "3.390" in line:
                yield line, rect, words

    monkeypatch.setattr(precision.base, "_line_groups", incomplete_words)
    dimensions = precision.extract_pdf_dimensions(source)
    main = {(round(float(ch.nominal), 3), ch.type) for ch in dimensions}
    assert (17.0, "LINEAR") in main
    assert (3.39, "LINEAR") in main
    assert (0.48, "LINEAR") in main
    assert (0.32, "RADIUS") in main
    assert len(dimensions) == 4

    for nominal in (0.48, 0.32):
        recovered = next(ch for ch in dimensions if ch.nominal == nominal)
        assert recovered.page_index == 0
        assert recovered.rect[1] > 612 * 0.70

    ballooned = tmp_path / "generic-bent-part_BALLOONED.pdf"
    precision.add_pdf_balloons(source, dimensions, ballooned)
    assert ballooned.is_file()
    with fitz.open(ballooned) as doc:
        # Four circles and leader lines are drawn, not just rows in a table.
        assert len(doc[0].get_drawings()) >= 8


def test_lower_detail_not_discarded_because_date_is_in_nearby_text(tmp_path):
    source = make_synthetic_drawing(tmp_path)
    with fitz.open(source) as doc:
        page = doc[0]
        rect = page.search_for(".480")[0]
        assert "DATE" in precision.base._nearby_text(page, rect, radius=150)
        assert not precision._title_noise(page, rect, ".480", "DATE 05-12-2020")
        assert not precision.base._noise_reason(
            ".480", ".480", ".480", "DATE 05-12-2020", page.rect, rect
        )


def test_hybrid_keeps_both_lower_dimensions_on_fully_searchable_pdf(tmp_path, monkeypatch):
    source = make_synthetic_drawing(tmp_path)
    # Isolate local native path: OCR reconciliation is tested separately.
    settings = ExtractionSettings(
        auto_detect_title_block=False, enable_ocr_fallback=False
    )
    import ez_fair_enhancements as enhanced
    monkeypatch.setattr(enhanced, "extract_gdt_characteristics", lambda *_: [])
    chars = extract_pdf_dimensions_hybrid(source, settings)
    assert any(ch.type == "LINEAR" and abs(ch.nominal - 0.48) < 1e-6 for ch in chars)
    assert any(ch.type == "RADIUS" and abs(ch.nominal - 0.32) < 1e-6 for ch in chars)
