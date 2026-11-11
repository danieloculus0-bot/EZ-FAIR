"""Neutral, locally generated default FAI workbook.

The source of the public template is this original, synthetic design.
Employer-specific inspection workbooks, branding, logos and private templates
are never bundled into the public repo or copied into source control.
Operators may keep a private FAI_MASTER.xlsx locally as their default.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties

BUILTIN_NAME = "EZFAIR_Default_FAI.xlsx"
LOCAL_OVERRIDE_NAME = "FAI_MASTER.xlsx"
PREFERENCE_NAME = ".ezfair_default_template.json"
BODY_START = 24
BODY_END = 48


def _app_dir(app_dir: str | Path | None = None) -> Path:
    return Path(app_dir) if app_dir is not None else Path(__file__).resolve().parent


def _preferences(home: str | Path | None = None) -> Path:
    return (Path(home) if home is not None else Path.home()) / PREFERENCE_NAME


def create_neutral_fai_template(path: str | Path) -> Path:
    """Create an original unbranded, Excel-native 25-characteristic master."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        # Do not overwrite an operator's controlled master or edited default.
        return target
    workbook = Workbook()
    form = workbook.active
    form.title = "FAI FORM"
    white = "FFFFFF"
    ink = "26344A"
    blue = "28527A"
    mist = "EAF1F6"
    rule = Side(style="thin", color="B5C1CA")

    form.sheet_view.showGridLines = False
    for col, width in {
        "A": 8, "B": 21, "C": 13, "D": 14, "E": 13,
        "F": 15, "G": 14, "H": 8, "I": 8, "J": 14,
        "K": 13, "L": 3, "M": 19, "N": 28,
    }.items():
        form.column_dimensions[col].width = width

    form.merge_cells("A3:N4")
    form["A3"] = "FIRST ARTICLE INSPECTION (FAI)"
    form["A3"].font = Font(name="Aptos", size=18, bold=True, color=white)
    form["A3"].fill = PatternFill("solid", fgColor=blue)
    form["A3"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    form.row_dimensions[3].height = 24
    form.row_dimensions[4].height = 19

    for cell, title in {
        "A6": "Part No:", "J6": "Part Name:", "A8": "Date:",
        "J8": "Drawing No:", "A10": "Inspected by:",
        "J10": "Revision:", "A12": "Item No:", "J12": "PO No:",
        "A14": "Order No:", "J14": "FAI Reason:",
    }.items():
        form[cell] = title
        form[cell].font = Font(name="Aptos", size=9, color=ink, bold=True)
    for ref in ["B6:E6", "K6:N6", "B8:E8", "K8:N8", "B10:E10",
                "K10:N10", "B12:E12", "K12:N12", "B14:E14", "K14:N14"]:
        form.merge_cells(ref)
        upper_left = form[ref.split(":")[0]]
        upper_left.border = Border(bottom=rule)
        upper_left.alignment = Alignment(vertical="center", wrap_text=True)

    form.merge_cells("A17:N17")
    form["A17"] = (
        "Enter actual measurements only after inspection. "
        "All extracted requirements must be checked against the customer drawing."
    )
    form["A17"].font = Font(name="Aptos", size=9, italic=True, color=ink)
    form["A17"].alignment = Alignment(wrap_text=True, vertical="center")
    form.row_dimensions[17].height = 28

    form["A22"] = "CHAR."
    form["B22"] = "REFERENCE"
    form["C22"] = "REQUIREMENT"
    form["F22"] = "TYPE"
    form["G22"] = "SUPPLIER INSPECTION RESULT"
    form["J22"] = "INSPECTION RESULT"
    form["M22"] = "TOOLING"
    form["N22"] = "COMMENTS"
    for c, title in {"A23": "#", "B23": "Location", "C23": "LSL",
                     "D23": "Nominal", "E23": "USL", "F23": "Type",
                     "G23": "Supplier Actual", "H23": "Yes", "I23": "No",
                     "J23": "Actual", "K23": "In Spec?", "M23": "Used",
                     "N23": "Notes / Review flags"}.items():
        form[c] = title
    for row in (22, 23):
        form.row_dimensions[row].height = 28 if row == 22 else 24
        for col in range(1, 15):
            cell = form.cell(row, col)
            cell.fill = PatternFill("solid", fgColor=blue if row == 22 else mist)
            cell.font = Font(name="Aptos", size=8, bold=True, color=white if row == 22 else ink)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = Border(bottom=rule)

    for row in range(BODY_START, BODY_END + 1):
        form.row_dimensions[row].height = 19
        form[f"A{row}"] = row - BODY_START + 1
        form[f"C{row}"] = f"=D{row}-0.02"
        form[f"E{row}"] = f"=D{row}+0.02"
        form[f"K{row}"] = (
            f'=IF(J{row}="","",IF(AND(J{row}>=C{row},J{row}<=E{row}),"X",""))'
        )
        for col in range(1, 15):
            cell = form.cell(row, col)
            cell.fill = PatternFill("solid", fgColor=white if row % 2 == 0 else "F4F7FA")
            cell.font = Font(name="Aptos", size=9, color=ink)
            cell.border = Border(bottom=rule)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        form[f"N{row}"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        for col in ("C", "D", "E", "G", "J"):
            form[f"{col}{row}"].number_format = "0.0000"

    for name, choices in {
        "CHARACTERISTICS": ["LINEAR", "DIAMETER", "RADIUS", "ANGLE", "GD&T", "WELD", "THREAD", "NOTE"],
        "TOOLING": ["CALIPER", "MICROMETER", "TAPE", "HEIGHT GAGE", "CMM", "GO/NO-GO", "VISUAL", "OTHER"],
        "ATTRIBUTE": ["PASS", "FAIL"],
    }.items():
        ws = workbook.create_sheet(name)
        for row, value in enumerate(choices, start=1):
            ws.cell(row, 1, value)

    for ref, formula in [
        ("F24:F48", "'CHARACTERISTICS'!$A$1:$A$8"),
        ("M24:M48", "'TOOLING'!$A$1:$A$8"),
        ("H24:I48", "'ATTRIBUTE'!$A$1:$A$2"),
    ]:
        validation = DataValidation(type="list", formula1=formula, allow_blank=True)
        form.add_data_validation(validation)
        validation.add(ref)
    form.freeze_panes = "A24"
    form.print_area = "A1:N48"
    form.print_title_rows = "1:23"
    form.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    form.page_setup.orientation = "landscape"
    form.page_setup.paperSize = form.PAPERSIZE_LETTER
    form.page_setup.fitToWidth = 1
    form.page_setup.fitToHeight = 1
    form.page_margins.left = form.page_margins.right = 0.25
    form.page_margins.top = form.page_margins.bottom = 0.4
    workbook.save(target)
    workbook.close()
    return target


def builtin_template_path(app_dir: str | Path | None = None) -> Path:
    return create_neutral_fai_template(_app_dir(app_dir) / "local_templates" / BUILTIN_NAME)


def resolve_default_template(
    app_dir: str | Path | None = None,
    home: str | Path | None = None,
) -> Path:
    """Local private preference > private master > generated built-in neutral form."""
    override = os.environ.get("EZFAIR_TEMPLATE", "").strip().strip('"')
    if override and Path(override).is_file():
        return Path(override)
    pref = _preferences(home)
    if pref.is_file():
        try:
            selection = Path(json.loads(pref.read_text(encoding="utf-8"))["template"])
            if selection.is_file():
                return selection
        except (OSError, KeyError, TypeError, ValueError):
            pass
    local_master = _app_dir(app_dir) / "local_templates" / LOCAL_OVERRIDE_NAME
    if local_master.is_file():
        return local_master
    return builtin_template_path(app_dir)


def save_default_template(path: str | Path, home: str | Path | None = None) -> Path:
    """Remember only the local path; never publish or copy the selected master."""
    target = Path(path).expanduser().resolve()
    if not target.is_file() or target.suffix.lower() not in {".xlsx", ".xlsm"}:
        raise ValueError("Choose a readable .xlsx or .xlsm Excel template.")
    pref = _preferences(home)
    pref.write_text(json.dumps({"template": str(target)}, indent=2), encoding="utf-8")
    return target


def reset_default_template(app_dir: str | Path | None = None, home: str | Path | None = None) -> Path:
    """Restore generated neutral template, overriding a private selection."""
    return save_default_template(builtin_template_path(app_dir), home)
