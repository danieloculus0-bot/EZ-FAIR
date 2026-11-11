"""Synthetic evidence tests. No actual customer drawings or company templates."""
from __future__ import annotations

import extractor_active as native
import ez_fair_enhancements as enhanced
from hybrid_extraction import reconcile_characteristics, extract_pdf_dimensions_hybrid
import hybrid_extraction as hybrid


def dim(n=1.25, x=60.0, y=80.0, typ="LINEAR", limits=None, status="explicit"):
    low, high = limits if limits is not None else (n - 0.02, n + 0.02)
    return native.Characteristic(
        char_number=1, reference_location="P1-R1C1", nominal=n,
        lsl=low, usl=high, type=typ, page_index=0,
        rect=(x, y, x + 26, y + 10), raw_text=str(n),
        metadata={"tolerance_status": status, "source": f"synthetic {n}"},
    )


def test_ocr_agreement_corroborates_but_never_replaces_native():
    result = reconcile_characteristics([dim()], [dim(x=61, y=81)])
    assert len(result) == 1
    assert result[0].metadata["extraction_paths"] == ["native_pdf", "ocr"]
    assert result[0].metadata["evidence_status"] == "corroborated"
    assert result[0].metadata["tolerance_evidence"] == "both_paths_agree"


def test_nearby_disagreement_retains_both_for_review():
    result = reconcile_characteristics([dim(n=1.25)], [dim(n=1.28)])
    assert len(result) == 2
    assert {round(c.nominal, 2) for c in result} == {1.25, 1.28}
    assert all(c.metadata["review_required"] for c in result)


def test_distant_equal_dimensions_are_not_suppressed_by_overlap_filter():
    result = reconcile_characteristics([dim()], [dim(x=250, y=250)])
    assert len(result) == 2
    assert result[1].metadata["review_required"]
    assert result[1].metadata["extraction_paths"] == ["ocr"]


def test_ocr_explicit_tolerance_does_not_silently_override_native_default():
    result = reconcile_characteristics([
        dim(limits=(1.23, 1.27), status="default")
    ], [
        dim(limits=(1.22, 1.29), status="explicit")
    ])
    assert len(result) == 1
    assert (result[0].lsl, result[0].usl) == (1.23, 1.27)
    assert result[0].metadata["ocr_proposed_limits"] == (1.22, 1.29)
    assert result[0].metadata["review_required"]


def test_explicit_tolerance_conflicts_require_review():
    result = reconcile_characteristics([
        dim(limits=(1.23, 1.27))
    ], [
        dim(limits=(1.22, 1.28))
    ])
    assert len(result) == 1
    assert result[0].metadata["review_required"]
    assert "disagree" in result[0].metadata["extraction_conflicts"]


def test_both_paths_run_even_when_vector_finds_dimensions(monkeypatch):
    called = {"ocr": 0}
    monkeypatch.setattr(native, "extract_pdf_dimensions", lambda _p: [dim()])
    def ocr(_p, _settings):
        called["ocr"] += 1
        return [dim()]
    monkeypatch.setattr(enhanced, "_extract_from_ocr", ocr)
    monkeypatch.setattr(enhanced, "extract_gdt_characteristics", lambda *_args: [])
    monkeypatch.setattr(hybrid, "_remove_title_block_candidates", lambda _p, v, o: (v, o))
    settings = enhanced.ExtractionSettings(
        auto_detect_title_block=False, enable_ocr_fallback=True
    )
    result = extract_pdf_dimensions_hybrid("synthetic-not-saved.pdf", settings)
    assert called["ocr"] == 1
    assert result[0].metadata["evidence_status"] == "corroborated"


def test_ocr_failure_keeps_valid_native_dimensions(monkeypatch):
    monkeypatch.setattr(native, "extract_pdf_dimensions", lambda _p: [dim()])
    def failed_ocr(*_args):
        raise RuntimeError("Tesseract unavailable")
    monkeypatch.setattr(enhanced, "_extract_from_ocr", failed_ocr)
    monkeypatch.setattr(enhanced, "extract_gdt_characteristics", lambda *_args: [])
    monkeypatch.setattr(hybrid, "_remove_title_block_candidates", lambda _p, v, o: (v, o))
    settings = enhanced.ExtractionSettings(auto_detect_title_block=False)
    result = extract_pdf_dimensions_hybrid("synthetic-not-saved.pdf", settings)
    assert len(result) == 1
    assert result[0].nominal == 1.25
    assert "Tesseract" in result[0].metadata["ocr_unavailable"]



def test_title_block_numbers_are_not_inspection_characteristics(tmp_path):
    """Synthetic labelled title block must not generate false balloons."""
    import pymupdf as fitz
    from hybrid_extraction import _remove_title_block_candidates
    pdf = tmp_path / "synthetic-title-block.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=792, height=612)
        page.insert_text((100, 120), "17.000", fontsize=12)
        page.insert_text((320, 410), "0.375", fontsize=12)
        page.insert_text((500, 520), "TITLE: BRACKET", fontsize=10)
        page.insert_text((500, 543), "SCALE 1:2", fontsize=10)
        page.insert_text((500, 566), "THREE PLACE DECIMAL 0.005", fontsize=10)
        doc.save(pdf)
    good = dim(n=17.0, y=120)
    low_detail = dim(n=0.375, y=408)
    admin = dim(n=0.005, y=554)
    native, ocr = _remove_title_block_candidates(pdf, [good, admin], [low_detail, admin])
    assert native == [good]
    assert ocr == [low_detail]


def test_unmarked_low_detail_is_not_excluded(tmp_path):
    import pymupdf as fitz
    from hybrid_extraction import _remove_title_block_candidates
    pdf = tmp_path / "no-title.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=792, height=612)
        page.insert_text((100, 530), "0.375", fontsize=12)
        doc.save(pdf)
    low_detail = dim(n=0.375, y=510)
    native, ocr = _remove_title_block_candidates(pdf, [low_detail], [low_detail])
    assert native == [low_detail]
    assert ocr == [low_detail]


def test_radius_not_reclassified_as_angle_by_adjacent_degree_symbol():
    from extractor_precision_patch import classify_dimension, _decorated_raw, _type_for_match
    from extractor_engine import DIMENSION_PATTERN
    line = "UP 19.86° R .32"
    bindings = [m for m in DIMENSION_PATTERN.finditer(line) if m.group("num") == ".32"]
    assert len(bindings) == 1
    raw = _decorated_raw(line, bindings[0])
    assert classify_dimension(raw, line) == "RADIUS"
    assert _type_for_match(raw, line, "", bindings[0]) == "RADIUS"
    assert classify_dimension("R19.86", line) == "RADIUS"
    assert classify_dimension(".32", "UP 19.86° AND .32") != "°"



def test_slightly_shifted_ocr_bbox_does_not_add_another_balloon():
    # Rendered glyph boxes and native CAD text rects are seldom identical.
    result = reconcile_characteristics([dim(n=6.0, x=60, y=80)], [dim(n=6.0, x=78, y=82)])
    assert len(result) == 1
    assert result[0].metadata["extraction_paths"] == ["native_pdf", "ocr"]


def test_same_nominal_repeated_on_drawing_remains_two_characteristics():
    results = reconcile_characteristics(
        [dim(n=6.0, x=60, y=80), dim(n=6.0, x=300, y=80)],
        [dim(n=6.0, x=74, y=83), dim(n=6.0, x=318, y=83)],
    )
    assert len(results) == 2
    assert all(item.metadata["extraction_paths"] == ["native_pdf", "ocr"] for item in results)
