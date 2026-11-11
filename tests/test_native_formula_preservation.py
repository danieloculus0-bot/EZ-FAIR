"""Synthetic controlled-form tests: no business source files committed."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image as PILImage
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Font, PatternFill
from fai_template_writer import fill_fai_template


@dataclass
class Characteristic:
    char_number: int = 1
    reference_location: str = "P1-R1C1"
    nominal: float = 2.0
    lsl: float = 1.98
    usl: float = 2.02
    type: str = "LINEAR"
    tooling: str = "CALIPER"
    comments: str = ""
    metadata: dict = field(default_factory=lambda: {"tolerance_status": "explicit"})


def build_native_formula_form(path: Path) -> None:
    book = Workbook()
    ws = book.active
    ws.title = "FAI FORM"
    ws["A3"] = "FIRST ARTICLE INSPECTION (FAI)"
    ws["A22"] = "CHAR"
    ws["C22"] = "REQUIREMENT"
    ws["G22"] = "SUPPLIER INSPECTION RESULT"
    ws["J22"] = "INSPECTION RESULT"
    ws["A3"].fill = PatternFill("solid", fgColor="FFDDCC")
    ws["A3"].font = Font(bold=True, color="000099")
    ws["B8"] = "operator enters date"
    ws.merge_cells("A3:N3")
    ws.merge_cells("K6:N6")
    ws.print_area = "A1:N48"
    ws.page_setup.orientation = "portrait"
    for row in range(24, 49):
        ws[f"A{row}"] = row - 23
        ws[f"C{row}"] = f"=D{row}-0.06"
        ws[f"E{row}"] = f"=D{row}+0.06"
        ws[f"K{row}"] = f'=IF(AND(J{row}>C{row},J{row}<E{row}),"X","")'
    png = path.with_suffix(".png")
    PILImage.new("RGB", (4, 4), color=(255, 255, 255)).save(png)
    ws.add_image(ExcelImage(str(png)), "A1")
    book.save(path)
    book.close()


def test_native_master_keeps_its_image_styles_formulas_and_print_layout(tmp_path):
    original, output = tmp_path / "private_master.xlsx", tmp_path / "filled.xlsx"
    build_native_formula_form(original)
    source_hash = sha256(original.read_bytes()).hexdigest()
    fill_fai_template(original, [Characteristic()], output)
    assert source_hash == sha256(original.read_bytes()).hexdigest()
    source = load_workbook(original)
    changed = load_workbook(output, data_only=False)
    before, after = source["FAI FORM"], changed["FAI FORM"]
    assert changed.sheetnames == source.sheetnames
    assert {str(x) for x in after.merged_cells.ranges} == {str(x) for x in before.merged_cells.ranges}
    assert len(after._images) == len(before._images) == 1
    # openpyxl StyleProxy objects do not implement cross-cell equality.
    assert after["A3"].fill.patternType == before["A3"].fill.patternType
    assert after["A3"].fill.fgColor.rgb == before["A3"].fill.fgColor.rgb
    assert after["A3"].font.bold == before["A3"].font.bold
    assert after["A3"].font.color.rgb == before["A3"].font.color.rgb
    assert after.print_area == before.print_area
    assert after.page_setup.orientation == before.page_setup.orientation
    assert after["B8"].value == "operator enters date"
    assert after["B24"].value == "P1-R1C1"
    assert after["D24"].value == 2.0
    assert after["C24"].value == "=D24-0.02"
    assert after["E24"].value == "=D24+0.02"
    assert after["K24"].value == before["K24"].value
    assert after["C25"].value == before["C25"].value
    assert after["E25"].value == before["E25"].value
    assert after["K25"].value == before["K25"].value
    source.close()
    changed.close()


def test_unverified_limits_keep_formula_and_never_report_pass(tmp_path):
    original, output = tmp_path / "master.xlsx", tmp_path / "filled.xlsx"
    build_native_formula_form(original)
    char = Characteristic(metadata={"tolerance_status": "review_required", "review_required": True})
    fill_fai_template(original, [char], output)
    book = load_workbook(output, data_only=False)
    ws = book["FAI FORM"]
    assert ws["C24"].value == "=D24-0.06"
    assert ws["E24"].value == "=D24+0.06"
    assert ws["K24"].value.startswith('=IF(TRUE,"REVIEW REQUIRED",')
    assert "REVIEW REQUIRED" in ws["N24"].value
    book.close()


def test_native_master_is_not_reformatted_or_extended_for_overflow(tmp_path):
    original, output = tmp_path / "master.xlsx", tmp_path / "filled.xlsx"
    build_native_formula_form(original)
    with pytest.raises(ValueError, match="holds 25 characteristics"):
        fill_fai_template(original, [Characteristic(char_number=i) for i in range(26)], output)
    assert not output.exists()


def test_unverified_default_conflicting_with_master_is_not_a_false_pass(tmp_path):
    original, output = tmp_path / "master.xlsx", tmp_path / "filled.xlsx"
    build_native_formula_form(original)
    char = Characteristic(metadata={"tolerance_status": "default"})
    fill_fai_template(original, [char], output)
    book = load_workbook(output, data_only=False)
    ws = book["FAI FORM"]
    assert ws["C24"].value == "=D24-0.06"
    assert ws["E24"].value == "=D24+0.06"
    assert ws["K24"].value.startswith('=IF(TRUE,"REVIEW REQUIRED",')
    assert "Template limits differ" in ws["N24"].value
    book.close()
