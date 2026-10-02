"""Generate the neutral built-in first article inspection workbook."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties

from form_profiles import FormConfiguration
from project_store import ProjectMetadata

THIN = Side(style="thin", color="000000")
MEDIUM = Side(style="medium", color="000000")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FILL = PatternFill("solid", fgColor="F2F2F2")
WHITE_FILL = PatternFill("solid", fgColor="FFFFFF")

START_ROW = 24
COLUMNS = {
    "char_number": 1,
    "reference_location": 2,
    "lsl": 3,
    "nominal": 4,
    "usl": 5,
    "feature_type": 6,
    "supplier_actual": 7,
    "supplier_yes": 8,
    "supplier_no": 9,
    "internal_actual": 10,
    "in_spec": 11,
    "tooling": 13,
    "comments": 14,
}

TYPE_VALUES = [
    "LINEAR", "DIAMETER", "RADIUS", "ANGLE", "CHAMFER", "THREAD", "WELD",
    "SURFACE FINISH", "NOTE", "MATERIAL", "GD&T CONTROL",
]
TOOL_VALUES = [
    "VISUAL", "CALIPER", "MICROMETER", "HEIGHT GAGE", "PIN GAGE", "THREAD GAGE",
    "CMM", "SURFACE PLATE", "PROTRACTOR", "ANGLE GAGE", "TAPE", "CERTIFICATION",
    "FITMENT/NHA", "HARDWARE",
]


def _value(item: Any, *names: str, default: Any = "") -> Any:
    if isinstance(item, dict):
        for name in names:
            if name in item:
                return item[name]
        return default
    for name in names:
        if hasattr(item, name):
            return getattr(item, name)
    return default


def _meta(metadata: ProjectMetadata | dict[str, Any]) -> dict[str, Any]:
    return metadata if isinstance(metadata, dict) else metadata.__dict__


def _set_box(ws, label_cell: str, value_range: str, label: str, value: Any) -> None:
    ws[label_cell] = label
    ws[label_cell].font = Font(bold=True, size=11)
    ws[label_cell].alignment = Alignment(vertical="center")
    ws.merge_cells(value_range)
    target = ws[value_range.split(":")[0]]
    target.value = value or ""
    target.alignment = Alignment(vertical="center")
    for row in ws[value_range]:
        for cell in row:
            cell.border = Border(left=MEDIUM, right=MEDIUM, top=MEDIUM, bottom=MEDIUM)
            cell.fill = WHITE_FILL


def _add_list_validation(ws, cell_range: str, values: list[str]) -> None:
    formula = '"' + ",".join(values) + '"'
    dv = DataValidation(type="list", formula1=formula, allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(cell_range)


def _style_data_row(ws, row: int) -> None:
    ws.merge_cells(start_row=row, start_column=11, end_row=row, end_column=12)
    for col in range(1, 15):
        cell = ws.cell(row, col)
        cell.border = BORDER
        cell.fill = WHITE_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.font = Font(size=10)
    ws.row_dimensions[row].height = 18


def _supplier_result(item: Any) -> str:
    return str(_value(item, "supplier_result", default="") or "").strip().upper()


def write_inspection_workbook(
    output_path: str | Path,
    metadata: ProjectMetadata | dict[str, Any],
    characteristics: Iterable[Any],
    configuration: FormConfiguration | None = None,
) -> Path:
    """Create the built-in neutral FAI workbook.

    The layout intentionally follows a conventional shop-floor first article form:
    compact drawing header, supplier/internal result blocks, tooling, comments, and
    an unlimited characteristic table. Company identity is never injected.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = list(characteristics)
    meta = _meta(metadata)

    wb = Workbook()
    ws = wb.active
    ws.title = "FAI FORM"
    ws.sheet_view.showGridLines = False

    widths = {
        "A": 11, "B": 15, "C": 9, "D": 10, "E": 9, "F": 15,
        "G": 15, "H": 8, "I": 8, "J": 15, "K": 8, "L": 8,
        "M": 17, "N": 30,
    }
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    ws.merge_cells("A3:N3")
    ws["A3"] = "FIRST ARTICLE INSPECTION (FAI)"
    ws["A3"].font = Font(bold=True, size=18)
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 28

    _set_box(ws, "A6", "B6:E6", "Part No:", meta.get("part_no", ""))
    _set_box(ws, "J6", "K6:N6", "Part Name:", meta.get("part_name", ""))
    _set_box(ws, "A8", "B8:E8", "Date:", meta.get("drawing_date", ""))
    _set_box(ws, "J8", "K8:N8", "Drawing No:", meta.get("drawing_no", ""))
    _set_box(ws, "A10", "B10:E10", "Insp. by:", meta.get("inspector", ""))
    _set_box(ws, "J10", "K10:N10", "Revision:", meta.get("revision", ""))
    _set_box(ws, "A12", "B12:E12", "Item No:", meta.get("item_no", ""))
    _set_box(ws, "J12", "K12:N12", "PO No:", meta.get("po_no", ""))
    _set_box(ws, "A14", "B14:E14", "Order No:", meta.get("order_no", ""))
    _set_box(ws, "J14", "K14:N14", "Reason for FAI:", meta.get("reason_for_fai", ""))

    ws["C16"] = "USL = Upper Spec Limit"
    ws["G16"] = "Nominal = Spec target"
    ws["J16"] = "Pass/Fail"
    for cell in ("C16", "G16", "J16"):
        ws[cell].font = Font(bold=True, size=10)
        ws[cell].alignment = Alignment(horizontal="center")

    ws.merge_cells("B18:E20")
    ws["B18"] = "This area may be completed by the entity submitting the inspection."
    ws["B18"].font = Font(bold=True, size=11)
    ws["B18"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.merge_cells("G18:I20")
    ws["G18"] = "SUPPLIER"
    ws["G18"].font = Font(bold=True, size=16)
    ws["G18"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("J18:L20")
    ws["J18"] = "INTERNAL"
    ws["J18"].font = Font(bold=True, size=16)
    ws["J18"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("N18:N23")
    ws["N18"] = "COMMENTS"
    ws["N18"].font = Font(bold=True, size=14)
    ws["N18"].alignment = Alignment(horizontal="center", vertical="center")

    for rng in ("B18:E20", "G18:I20", "J18:L20", "N18:N23"):
        for row_cells in ws[rng]:
            for cell in row_cells:
                cell.border = BORDER

    ws["M20"] = "TOOLING"
    ws["M20"].font = Font(bold=True, size=10)
    ws["M20"].alignment = Alignment(horizontal="center")

    # Main header, intentionally close to a traditional FAI worksheet.
    ws.merge_cells("A22:A23")
    ws.merge_cells("B22:B23")
    ws.merge_cells("C22:E22")
    ws.merge_cells("F22:F23")
    ws.merge_cells("G22:G23")
    ws.merge_cells("H22:I22")
    ws.merge_cells("J22:J23")
    ws.merge_cells("K22:L22")
    ws.merge_cells("M22:M23")

    headers = {
        "A22": "CHAR.\nNUMBER",
        "B22": "REFERENCE\nLOCATION",
        "C22": "REQUIREMENT",
        "F22": "TYPE",
        "G22": "Inspection Result\nActual",
        "H22": "In Spec?",
        "J22": "Inspection Result\nActual",
        "K22": "In Spec?",
        "M22": "TOOLING\nUSED",
        "C23": "LSL",
        "D23": "Nominal",
        "E23": "USL",
        "H23": "Yes",
        "I23": "No",
        "K23": "X = Yes",
    }
    for cell_ref, text in headers.items():
        cell = ws[cell_ref]
        cell.value = text
        cell.font = Font(bold=True, size=10)
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row in range(22, 24):
        for col in range(1, 15):
            ws.cell(row, col).border = BORDER
            if col != 14:
                ws.cell(row, col).fill = HEADER_FILL

    end_row = START_ROW + max(len(rows), 1) - 1
    for row in range(START_ROW, end_row + 1):
        _style_data_row(ws, row)
        ws.cell(row, COLUMNS["char_number"], row - START_ROW + 1)
        ws.cell(row, COLUMNS["in_spec"], f'=IF(J{row}="","",IF(AND(J{row}>=C{row},J{row}<=E{row}),"X",""))')

    for offset, item in enumerate(rows):
        row = START_ROW + offset
        ws.cell(row, COLUMNS["char_number"], _value(item, "char_number", "Char Number", default=offset + 1))
        ws.cell(row, COLUMNS["reference_location"], _value(item, "reference_location", "Reference Location"))
        ws.cell(row, COLUMNS["lsl"], _value(item, "lsl", "Requirement LSL"))
        ws.cell(row, COLUMNS["nominal"], _value(item, "nominal", "Requirement Nominal"))
        ws.cell(row, COLUMNS["usl"], _value(item, "usl", "Requirement USL"))
        ws.cell(row, COLUMNS["feature_type"], _value(item, "type", "feature_type", "Type"))
        ws.cell(row, COLUMNS["supplier_actual"], _value(item, "supplier_actual"))
        supplier_result = _supplier_result(item)
        if supplier_result in {"PASS", "YES", "Y", "X"}:
            ws.cell(row, COLUMNS["supplier_yes"], "X")
        elif supplier_result in {"FAIL", "NO", "N"}:
            ws.cell(row, COLUMNS["supplier_no"], "X")
        ws.cell(row, COLUMNS["internal_actual"], _value(item, "actual", "ez_actual", "Inspection Actual"))
        ws.cell(row, COLUMNS["tooling"], _value(item, "tooling", "qualified_tooling", "Tooling Used"))
        ws.cell(row, COLUMNS["comments"], _value(item, "comments", "Comments"))

    # Keep the form usable at large row counts without imposing a characteristic cap.
    _add_list_validation(ws, f"F{START_ROW}:F{end_row}", TYPE_VALUES)
    _add_list_validation(ws, f"M{START_ROW}:M{end_row}", TOOL_VALUES)

    ws.freeze_panes = "A24"
    ws.print_title_rows = "1:23"
    ws.print_area = f"A1:N{end_row}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.35
    ws.page_margins.bottom = 0.35

    wb.save(output)
    wb.close()
    return output
