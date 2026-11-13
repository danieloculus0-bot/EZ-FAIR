"""Synthetic isolation regressions for issue #25. No real drawings or business records."""
from __future__ import annotations

import pytest

import extractor_active as native
import extractor_engine
import ez_fai_builder
import ez_fair_enhancements as enhanced
import hybrid_extraction as hybrid


@pytest.mark.parametrize("fail_native", [False, True])
def test_hybrid_restores_caller_and_module_tolerances(monkeypatch, fail_native):
    """One drawing must not change settings or module defaults for the next."""
    settings = enhanced.ExtractionSettings(
        auto_detect_title_block=True, enable_ocr_fallback=False
    )
    before_settings = {
        key: getattr(settings, key)
        for key in ("two_place", "three_place", "angular")
    }
    before_legacy = dict(ez_fai_builder.TITLE_BLOCK_DEFAULTS)
    before_engine = dict(extractor_engine.TITLE_BLOCK_DEFAULTS)

    monkeypatch.setattr(
        enhanced, "detect_title_block_defaults",
        lambda *_args: {"two_place": 0.017, "three_place": 0.004, "angular": 2.0},
    )

    def vector(_source):
        if fail_native:
            raise RuntimeError("synthetic vector failure")
        return []

    monkeypatch.setattr(native, "extract_pdf_dimensions", vector)
    monkeypatch.setattr(
        hybrid, "_remove_title_block_candidates", lambda _source, v, o: (v, o)
    )
    monkeypatch.setattr(enhanced, "extract_gdt_characteristics", lambda *_args: [])

    if fail_native:
        with pytest.raises(RuntimeError, match="synthetic vector failure"):
            hybrid.extract_pdf_dimensions_hybrid("fictional-drawing.pdf", settings)
    else:
        assert hybrid.extract_pdf_dimensions_hybrid("fictional-drawing.pdf", settings) == []

    assert {
        key: getattr(settings, key)
        for key in before_settings
    } == before_settings
    assert ez_fai_builder.TITLE_BLOCK_DEFAULTS == before_legacy
    assert extractor_engine.TITLE_BLOCK_DEFAULTS == before_engine
