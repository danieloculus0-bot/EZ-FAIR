"""Synthetic-only tests of title-block precision and clean original Excel outputs."""
from pathlib import Path
import pytest
import pymupdf as fitz

from ez_fair_enhancements import (
    ExtractionSettings, detect_title_block_defaults, parse_title_block_tolerances,
)
from hybrid_extraction import extract_pdf_dimensions_hybrid


PRINT_NOTES = (
    "UNLESS OTHERWISE SPECIFIED: DIMENSIONS ARE IN INCHES "
    'FRACTIONAL ±1/16" ANGULAR: MACH ± .5° BEND ± 1° '
    "TWO PLACE DECIMAL ±0.06 THREE PLACE DECIMAL ±0.01"
)


def test_english_worded_precision_rules_do_not_swap_two_and_three_place():
    got = parse_title_block_tolerances(PRINT_NOTES)
    assert got["fractional"] == pytest.approx(1 / 16)
    assert got["two_place"] == pytest.approx(0.06)
    assert got["three_place"] == pytest.approx(0.01)
    assert got["angular_mach"] == pytest.approx(0.5)
    assert got["angular_bend"] == pytest.approx(1.0)
    assert got["angular"] == pytest.approx(1.0)


def test_numeric_title_block_style_is_also_understood():
    got = parse_title_block_tolerances(".XX ±.06  .XXX ±.01 ANGLES ±2°")
    assert got["two_place"] == pytest.approx(.06)
    assert got["three_place"] == pytest.approx(.01)
    assert got["angular"] == pytest.approx(2)


def test_actual_drawing_tolerance_note_left_of_title_box_is_detected(tmp_path):
    pdf = tmp_path / "synthetic_formed_part.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=792, height=612)
        page.insert_text((150, 100), "17.000", fontsize=12)
        page.insert_text((250, 235), "135.000°", fontsize=12)
        page.insert_text((210, 390), "R.320", fontsize=12)
        # Tolerance notes occupy lower LEFT, not lower right.
        for index, line in enumerate([
            "UNLESS OTHERWISE SPECIFIED: DIMENSIONS ARE IN INCHES",
            "FRACTIONAL +/- 1/16",
            "ANGULAR: MACH +/- .5 deg BEND +/- 1 deg",
            "TWO PLACE DECIMAL +/- 0.06",
            "THREE PLACE DECIMAL +/- 0.01",
            "TITLE: GENERIC FORMED SAMPLE",
            "SCALE 1:2",
        ]):
            page.insert_text((105, 500 + 13 * index), line, fontsize=8)
        doc.save(pdf)
    settings = ExtractionSettings(auto_detect_title_block=True, enable_ocr_fallback=False)
    found = detect_title_block_defaults(pdf, settings)
    assert found["two_place"] == pytest.approx(.06)
    assert found["three_place"] == pytest.approx(.01)
    assert found["angular"] == pytest.approx(1)
    chars = extract_pdf_dimensions_hybrid(pdf, settings)
    by_val = {float(c.nominal): c for c in chars if isinstance(c.nominal, (int, float))}
    assert by_val[17.0].lsl == pytest.approx(16.99)
    assert by_val[17.0].usl == pytest.approx(17.01)
    assert by_val[0.32].lsl == pytest.approx(0.31)
    assert by_val[0.32].usl == pytest.approx(0.33)
    assert by_val[135.0].lsl == pytest.approx(134.0)
    assert by_val[135.0].usl == pytest.approx(136.0)
    assert by_val[17.0].metadata["title_block_detected"]["three_place"] == pytest.approx(0.01)
