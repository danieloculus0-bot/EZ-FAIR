from pathlib import Path

import fitz

import ez_fai_builder as base
from ez_fair_enhancements import ExtractionSettings, detect_title_block_defaults


def test_explicit_symmetric_tolerance_overrides_title_block():
    lsl, usl = base.calculate_tolerance_limits(1.250, "1.250", "LINEAR", "1.250 +/- .005")
    assert lsl == 1.245
    assert usl == 1.255


def test_title_block_precision_classes_include_one_and_four_place():
    saved = dict(base.TITLE_BLOCK_DEFAULTS)
    try:
        base.TITLE_BLOCK_DEFAULTS.update(one_place=0.1, two_place=0.02, three_place=0.005, four_place=0.0005, angular=1.0)
        assert base.calculate_tolerance_limits(1.2, "1.2", "LINEAR") == (1.1, 1.3)
        assert base.calculate_tolerance_limits(1.2345, "1.2345", "LINEAR") == (1.234, 1.235)
    finally:
        base.TITLE_BLOCK_DEFAULTS.clear()
        base.TITLE_BLOCK_DEFAULTS.update(saved)


def test_detects_common_title_block_tolerance_table(tmp_path: Path):
    pdf = tmp_path / "title_tol.pdf"
    doc = fitz.open()
    page = doc.new_page(width=1000, height=800)
    page.insert_textbox(
        fitz.Rect(520, 500, 980, 760),
        "UNLESS OTHERWISE SPECIFIED\n.X +/- .1\n.XX +/- .02\n.XXX +/- .005\n.XXXX +/- .0005\nANGLES +/- 1 DEG",
        fontsize=11,
    )
    doc.save(pdf)
    doc.close()

    detected = detect_title_block_defaults(pdf, ExtractionSettings(enable_ocr_fallback=False))

    assert detected["one_place"] == 0.1
    assert detected["two_place"] == 0.02
    assert detected["three_place"] == 0.005
    assert detected["four_place"] == 0.0005
    assert detected["angular"] == 1.0
