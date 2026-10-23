"""Fractions cannot inherit explicit limits from a different nominal's PDF line."""
import fitz
import pytest

import extractor_fraction_weld_patch as fractions
from local_test_runner import _has_explicit_tolerance


@pytest.mark.parametrize("line,has_explicit", [
    ("PLATE 1/4 +.010/-.005", True),
    ("PLATE 1/4", False),
    ("PLATE 1/4 LENGTH 2.00 +.050/-.025", True),
])
def test_fraction_never_silently_auto_passes_unassociated_limits(tmp_path, line, has_explicit):
    pdf = tmp_path / "fraction-print.pdf"
    with fitz.open() as document:
        page = document.new_page(width=792, height=612)
        page.insert_text((70, 100), line, fontsize=12)
        document.save(pdf)
    chars = fractions.extract_pdf_dimensions(pdf)
    frac = next(c for c in chars if isinstance(c.nominal, (int, float))
                and c.nominal == pytest.approx(0.25) and "fraction_value" in c.metadata)
    assert frac.metadata["tolerance_review_required"] is True
    assert frac.metadata["tolerance_status"] == "review_required"
    assert _has_explicit_tolerance(frac) is False
    assert "VERIFY TOLERANCE" in frac.comments or "REVIEW REQUIRED" in frac.comments
    if has_explicit:
        assert frac.lsl is None and frac.usl is None
    else:
        assert (frac.lsl, frac.usl) == pytest.approx((0.21875, 0.28125))
