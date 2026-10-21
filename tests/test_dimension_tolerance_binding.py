"""Regression coverage for tolerance-to-characteristic identity, not just totals."""
from __future__ import annotations

import fitz
import pytest

from dimension_tolerance import bind_tolerances, tolerance_for_candidate
import extractor_engine as base
import extractor_precision_patch as precision
import ez_fai_builder as desktop


def _by_number(chars, value):
    return [c for c in chars if c.nominal == pytest.approx(value)]


def test_each_nominal_gets_its_own_bilateral_tolerance():
    line = "WIDTH 2.00 +.02 -.01 LENGTH 4.00 +.10 -.05 HEIGHT 6.00"
    bound = bind_tolerances(line, base.DIMENSION_PATTERN)
    assert [x.match.group("num") for x in bound] == ["2.00", "4.00", "6.00"]
    assert [x.status for x in bound] == ["explicit", "explicit", "default"]
    assert base.calculate_tolerance_limits(2, "2.00", "LINEAR", bound[0].context) == (1.99, 2.02)
    assert base.calculate_tolerance_limits(4, "4.00", "LINEAR", bound[1].context) == (3.95, 4.10)
    assert base.calculate_tolerance_limits(6, "6.00", "LINEAR", bound[2].context) == (5.98, 6.02)


def test_unassigned_or_competing_tolerance_requires_review():
    for line in (
        "+.02 -.01 WIDTH 2.00",
        "WIDTH 2.00 +.02 -.01 +.10 -.05",
        "WIDTH 2.00 PER PRINT +.02 -.01",
    ):
        bound = bind_tolerances(line, base.DIMENSION_PATTERN)
        assert len(bound) == 1
        assert bound[0].status == "review_required"
        assert bound[0].context == ""


def test_symmetric_notation_and_repeated_nominal_are_conservative():
    line = "WIDTH 2.00 ±.03 LENGTH 4.00 ±.01"
    bound = bind_tolerances(line, base.DIMENSION_PATTERN)
    assert [x.match.group("num") for x in bound] == ["2.00", "4.00"]
    assert [x.context for x in bound] == ["+.03 -.03", "+.01 -.01"]
    assert tolerance_for_candidate(line, base.DIMENSION_PATTERN, "4.00") == ("+.01 -.01", "explicit")
    repeat = "WIDTH 2.00 +.03 -.01 LENGTH 2.00 +.04 -.02"
    assert tolerance_for_candidate(repeat, base.DIMENSION_PATTERN, "2.00") == ("", "review_required")


@pytest.mark.parametrize("extractor", [base.extract_pdf_dimensions, precision.extract_pdf_dimensions, desktop.extract_pdf_dimensions])
def test_pdf_multi_tolerance_never_leaks_to_other_characteristic(tmp_path, extractor):
    drawing = tmp_path / "independent-tolerances.pdf"
    with fitz.open() as document:
        page = document.new_page(width=792, height=612)
        page.insert_text((72, 120), "WIDTH 2.00 +.02 -.01 LENGTH 4.00 +.10 -.05", fontsize=12)
        page.insert_text((72, 165), "HEIGHT 6.00", fontsize=12)
        document.save(drawing)

    chars = extractor(drawing)
    a = _by_number(chars, 2.0)
    b = _by_number(chars, 4.0)
    assert a and b
    assert (a[0].lsl, a[0].usl) == (1.99, 2.02)
    assert (b[0].lsl, b[0].usl) == (3.95, 4.1)
    assert a[0].metadata["tolerance_status"] == "explicit"
    assert b[0].metadata["tolerance_status"] == "explicit"
    assert not any(c.nominal == pytest.approx(.01) or c.nominal == pytest.approx(.02)
                   or c.nominal == pytest.approx(.05) or c.nominal == pytest.approx(.10)
                   for c in chars)
