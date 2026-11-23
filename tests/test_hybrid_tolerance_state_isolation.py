"""Synthetic regression tests for per-drawing tolerance state isolation.

No production drawings, customer tolerances, or real business records.
"""
import pytest

import extractor_active as native
import extractor_engine
import ez_fai_builder as legacy
import ez_fair_enhancements as enhanced
import hybrid_extraction as hybrid


def _settings():
    return enhanced.ExtractionSettings(
        auto_detect_title_block=True,
        enable_ocr_fallback=False,
    )


def _fake_dimension():
    return native.Characteristic(
        char_number=1,
        reference_location="P1-R1C1",
        nominal=1.234,
        lsl=None,
        usl=None,
        type="LINEAR",
        page_index=0,
        rect=(10, 10, 35, 20),
        raw_text="1.234",
        metadata={"tolerance_status": "default"},
    )


def _install_synthetic_extractors(monkeypatch, detection, fail=False):
    monkeypatch.setattr(enhanced, "detect_title_block_defaults", lambda *_: detection)
    if fail:
        def raise_on_native(_source):
            raise RuntimeError("synthetic extraction failure")
        monkeypatch.setattr(native, "extract_pdf_dimensions", raise_on_native)
    else:
        monkeypatch.setattr(native, "extract_pdf_dimensions", lambda _source: [_fake_dimension()])
    monkeypatch.setattr(hybrid, "_remove_title_block_candidates",
                        lambda _source, vectors, ocrs: (vectors, ocrs))
    monkeypatch.setattr(enhanced, "extract_gdt_characteristics", lambda *_: [])


def _assert_restored(settings, expected, original_legacy, original_engine):
    assert (settings.two_place, settings.three_place, settings.angular) == expected
    assert legacy.TITLE_BLOCK_DEFAULTS == original_legacy
    assert extractor_engine.TITLE_BLOCK_DEFAULTS == original_engine


def test_sequential_drawings_do_not_inherit_tolerance_defaults(monkeypatch):
    settings = _settings()
    expected = (settings.two_place, settings.three_place, settings.angular)
    original_legacy = dict(legacy.TITLE_BLOCK_DEFAULTS)
    original_engine = dict(extractor_engine.TITLE_BLOCK_DEFAULTS)

    _install_synthetic_extractors(monkeypatch, {"three_place": 0.007})
    first = hybrid.extract_pdf_dimensions_hybrid("fictional-alpha.pdf", settings)
    assert first[0].lsl == pytest.approx(1.227)
    assert first[0].usl == pytest.approx(1.241)
    assert first[0].metadata["tolerance_source"] == "drawing_title_block"
    _assert_restored(settings, expected, original_legacy, original_engine)

    _install_synthetic_extractors(monkeypatch, {})
    second = hybrid.extract_pdf_dimensions_hybrid("fictional-beta.pdf", settings)
    assert second[0].lsl is None and second[0].usl is None
    assert second[0].metadata["tolerance_source"] == "unknown"
    assert second[0].metadata["title_block_detected"] == {}
    _assert_restored(settings, expected, original_legacy, original_engine)


def test_exception_restores_all_shared_defaults(monkeypatch):
    settings = _settings()
    expected = (settings.two_place, settings.three_place, settings.angular)
    original_legacy = dict(legacy.TITLE_BLOCK_DEFAULTS)
    original_engine = dict(extractor_engine.TITLE_BLOCK_DEFAULTS)

    _install_synthetic_extractors(monkeypatch, {"three_place": 0.009}, fail=True)
    with pytest.raises(RuntimeError, match="synthetic extraction failure"):
        hybrid.extract_pdf_dimensions_hybrid("fictional-failure.pdf", settings)
    _assert_restored(settings, expected, original_legacy, original_engine)
