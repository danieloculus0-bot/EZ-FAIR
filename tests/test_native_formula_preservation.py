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
from fai_template_writer import fill_fai_template, fill_fai_template_pages


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
    raw_text: str = ""
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
    assert before["K24"].value[1:] in after["K24"].value
    assert 'OR(J24="",C24="",E24=""' in after["K24"].value
    assert after["C25"].value is None  # no default on unpopulated rows
    assert after["E25"].value is None  # master itself keeps its formulas
    assert after["K25"].value is None
    assert before["K25"].data_type == "f"
    source.close()
    changed.close()


def test_unverified_limits_keep_formula_and_never_report_pass(tmp_path):
    original, output = tmp_path / "master.xlsx", tmp_path / "filled.xlsx"
    build_native_formula_form(original)
    char = Characteristic(metadata={"tolerance_status": "review_required", "review_required": True})
    fill_fai_template(original, [char], output)
    book = load_workbook(output, data_only=False)
    ws = book["FAI FORM"]
    assert ws["C24"].value is None
    assert ws["E24"].value is None
    assert ws["K24"].value.endswith('IF(AND(J24>C24,J24<E24),"X",""))')
    assert 'NOT(ISNUMBER(J24))' in ws["K24"].value
    assert ws["N24"].value is None
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
    assert ws["C24"].value is None
    assert ws["E24"].value is None
    assert ws["K24"].value.endswith('IF(AND(J24>C24,J24<E24),"X",""))')
    assert 'NOT(ISNUMBER(J24))' in ws["K24"].value
    assert ws["N24"].value is None
    book.close()



def test_more_than_25_characteristics_produces_one_workbook_with_form_tabs(tmp_path):
    master = tmp_path / "controlled_template.xlsx"
    build_native_formula_form(master)
    original_hash = sha256(master.read_bytes()).hexdigest()
    candidates = [
        Characteristic(char_number=i, reference_location=f"P1-Z{i}", nominal=float(i),
                       lsl=float(i) - 0.02, usl=float(i) + 0.02)
        for i in range(1, 59)
    ]
    target = tmp_path / "part_FAI.xlsx"
    forms = fill_fai_template_pages(master, candidates, target)
    assert forms == [target]
    assert target.exists()
    assert sorted(path.name for path in tmp_path.glob("part_FAI*.xlsx")) == ["part_FAI.xlsx"]
    assert sha256(master.read_bytes()).hexdigest() == original_hash

    book = load_workbook(target, data_only=False)
    tabs = ["FAI FORM", "FAI FORM 2", "FAI FORM 3"]
    assert book.sheetnames[:3] == tabs
    for tab, expected_first, expected_last in zip(
        tabs, [1, 26, 51], [25, 50, 58]
    ):
        ws = book[tab]
        # Empty unused rows need no cells; preserve the full printed form area.
        assert (24 + expected_last - expected_first) <= ws.max_row <= 48
        assert len(ws._images) == 1
        assert ws["A24"].value == expected_first
        assert ws[f"A{24 + expected_last - expected_first}"].value == expected_last
        assert ws["C24"].data_type == "f"
        assert ws["E24"].data_type == "f"
        assert ws["K24"].data_type == "f"
        assert "review" not in str(ws["K24"].value).lower()
        assert ws.print_area == f"'{tab}'!$A$1:$N$48"
        assert ws["A3"].fill.fgColor.rgb == book["FAI FORM"]["A3"].fill.fgColor.rgb
    assert book["FAI FORM 2"]["C24"].value == "=D24-0.02"
    assert book["FAI FORM 3"]["D24"].value == 51
    assert book["FAI FORM 3"]["A31"].value == 58
    assert book["FAI FORM 3"]["A32"].value is None
    book.close()


def test_single_page_export_name_remains_stable(tmp_path):
    master = tmp_path / "master.xlsx"
    build_native_formula_form(master)
    target = tmp_path / "output.xlsx"
    files = fill_fai_template_pages(
        master, [Characteristic(char_number=1)], target
    )
    assert files == [target]
    assert target.exists()


def test_varied_nominals_preserve_second_page_formula_offsets(tmp_path):
    master = tmp_path / "master.xlsx"
    build_native_formula_form(master)
    candidates = [
        Characteristic(char_number=i, nominal=100 + i,
                       lsl=99.98 + i, usl=100.02 + i)
        for i in range(1, 27)
    ]
    files = fill_fai_template_pages(master, candidates, tmp_path / "out.xlsx")
    assert files == [tmp_path / "out.xlsx"]
    book = load_workbook(files[0], data_only=False)
    second = book["FAI FORM 2"]
    assert second["A24"].value == 26
    assert second["D24"].value == 126
    assert second["C24"].value == "=D24-0.02"
    assert second["E24"].value == "=D24+0.02"
    book.close()



def test_detected_three_place_print_tolerance_updates_only_limit_formulas(tmp_path):
    original, output = tmp_path / "master.xlsx", tmp_path / "filled.xlsx"
    build_native_formula_form(original)
    before = sha256(original.read_bytes()).hexdigest()
    source_rules = {"two_place": .06, "three_place": .01,
                    "angular": 1.0, "angular_bend": 1.0}
    chars = [
        Characteristic(char_number=1, nominal=17.000, lsl=16.990,
                       usl=17.010, raw_text="17.000", comments="BAD DIAGNOSTIC",
                       metadata={"tolerance_status": "default", "title_block_detected": source_rules,
                                 "review_required": True, "tolerance_source": "drawing_title_block"}),
        Characteristic(char_number=2, nominal=.320, lsl=.310, usl=.330,
                       type="RADIUS", raw_text="R.320",
                       metadata={"tolerance_status": "default", "title_block_detected": source_rules,
                                 "tolerance_source": "drawing_title_block"}),
        Characteristic(char_number=3, nominal=135.0, lsl=134.0, usl=136.0,
                       type="°", raw_text="135.000°",
                       metadata={"tolerance_status": "default", "title_block_detected": source_rules,
                                 "tolerance_source": "drawing_title_block"}),
        Characteristic(char_number=4, nominal=2.25, lsl=2.19, usl=2.31,
                       raw_text="2.25",
                       metadata={"tolerance_status": "default", "title_block_detected": source_rules,
                                 "tolerance_source": "drawing_title_block"}),
    ]
    fill_fai_template(original, chars, output)
    assert before == sha256(original.read_bytes()).hexdigest()
    original_book = load_workbook(original, data_only=False)
    output_book = load_workbook(output, data_only=False)
    source, form = original_book["FAI FORM"], output_book["FAI FORM"]
    assert [(form[f"C{row}"].value, form[f"E{row}"].value)
            for row in range(24, 28)] == [
        ("=D24-0.01", "=D24+0.01"),
        ("=D25-0.01", "=D25+0.01"),
        ("=D26-1", "=D26+1"),
        ("=D27-0.06", "=D27+0.06"),
    ]
    for row in range(24, 28):
        assert source[f"K{row}"].value[1:] in form[f"K{row}"].value
        assert f'J{row}=""' in form[f"K{row}"].value
        assert form[f"N{row}"].value is None
        assert form[f"J{row}"].value is None
    assert form["D24"].value == 17.0
    original_book.close()
    output_book.close()



def test_no_inherited_tolerances_on_any_report_row_if_unknown(tmp_path):
    source = tmp_path / "master.xlsx"
    output = tmp_path / "filled.xlsx"
    build_native_formula_form(source)
    original_hash = sha256(source.read_bytes()).hexdigest()
    char = Characteristic(nominal=17.0, lsl=16.94, usl=17.06,
                          raw_text="17.000",
                          metadata={"tolerance_status": "default",
                                    "title_block_detected": {},
                                    "tolerance_source": "unknown"})
    fill_fai_template(source, [char], output)
    wb = load_workbook(output, data_only=False)
    ws = wb["FAI FORM"]
    for row in range(24, 49):
        assert ws[f"C{row}"].value is None
        assert ws[f"E{row}"].value is None
        assert ws[f"K{row}"].data_type == ("f" if row == 24 else "n")
        assert ws[f"N{row}"].value is None
    assert ws["D24"].value == 17.0
    wb.close()
    assert sha256(source.read_bytes()).hexdigest() == original_hash



def test_twelve_characteristics_leave_rest_of_original_fai_visibly_blank(tmp_path):
    original = tmp_path / "source_master.xlsx"
    output = tmp_path / "single_fai.xlsx"
    build_native_formula_form(original)
    before = sha256(original.read_bytes()).hexdigest()
    chars = [
        Characteristic(char_number=i, nominal=float(i), lsl=float(i) - 0.01,
                       usl=float(i) + 0.01, reference_location=f"P1-R{i}",
                       raw_text=f"{i}.000", comments="DO NOT EXPORT",
                       metadata={"tolerance_status": "explicit"})
        for i in range(1, 13)
    ]
    fill_fai_template_pages(original, chars, output)
    assert sha256(original.read_bytes()).hexdigest() == before
    source = load_workbook(original, data_only=False)
    generated = load_workbook(output, data_only=False)
    out = generated["FAI FORM"]
    assert len(out._images) == len(source["FAI FORM"]._images)
    assert {str(m) for m in out.merged_cells.ranges} == {
        str(m) for m in source["FAI FORM"].merged_cells.ranges
    }
    for row in range(24, 36):
        assert out[f"D{row}"].value == row - 23
        assert out[f"C{row}"].value == f"=D{row}-0.01"
        assert out[f"E{row}"].value == f"=D{row}+0.01"
        formula = out[f"K{row}"].value
        assert formula.startswith(f'=IF(OR(J{row}="",C{row}="",E{row}=""')
        assert source["FAI FORM"][f"K{row}"].value[1:] in formula
        assert out[f"J{row}"].value is None
        assert out[f"N{row}"].value is None
    for row in range(36, 49):
        for col in ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "M", "N"):
            assert out[f"{col}{row}"].value is None, f"{col}{row} leaked content"
    assert source["FAI FORM"]["K36"].data_type == "f"
    source.close()
    generated.close()
