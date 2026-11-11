from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any, Iterable

from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties

EXACT_R3_SHEET = "FAI FORM"
R3_START_ROW = 24
R3_TEMPLATE_END_ROW = 48
R3_TEMPLATE_CAPACITY = R3_TEMPLATE_END_ROW - R3_START_ROW + 1
R3_BODY_ROW_HEIGHT = 17.0
R3_HEADER_ROW_HEIGHT = 15.0

R3_HEADER_METADATA = {
    "part_no": "B6",
    "part_name": "K6",
    "drawing_no": "K8",
    "revision": "K10",
}

R3_COLUMNS = {
    "Char Number": 1,
    "Reference Location": 2,
    "Requirement LSL": 3,
    "Requirement Nominal": 4,
    "Requirement USL": 5,
    "Type": 6,
    "Supplier Actual": 7,
    "Supplier Yes": 8,
    "Supplier No": 9,
    "Inspection Actual": 10,
    "In Spec": 11,
    "Tooling Used": 13,
    "Comments": 14,
}

GENERIC_HEADERS = [
    "Char Number", "Reference Location", "Requirement LSL", "Requirement Nominal", "Requirement USL",
    "Type", "Inspection Actual", "In Spec", "Tooling Used", "Comments",
]

HEADER_ALIASES = {
    "Char Number": ["char", "char number", "char no", "characteristic", "balloon", "balloon no"],
    "Reference Location": ["reference location", "ref location", "location", "zone"],
    "Requirement LSL": ["requirement lsl", "lsl", "lower spec limit", "lower limit", "minimum", "min"],
    "Requirement Nominal": ["requirement nominal", "nominal", "requirement", "dimension", "specified requirement"],
    "Requirement USL": ["requirement usl", "usl", "upper spec limit", "upper limit", "maximum", "max"],
    "Type": ["type", "characteristic type", "dim type"],
    "Inspection Actual": ["Inspection Actual", "actual", "actual result", "measured actual", "measurement"],
    "In Spec": ["in spec", "inspec", "pass fail", "pass/fail", "accept", "result"],
    "Tooling Used": ["tooling used", "tooling", "tool used", "gage", "gauge", "inspection tool"],
    "Comments": ["comments", "comment", "notes", "remark", "remarks"],
}

LIST_SHEET_SPECS = {
    "CHARACTERISTICS": [
        "NOTE", "TOLERANCE", "FINISH", "WELD", "MATERIAL", "RADIUS", "LINEAR", "DIAMETER", "Ø", "▱", "◯", "⌭",
        "∩", "⌓", "∠", "⊥", "//", "⌖", "◎", "⌯", "⌰", "Ⓕ", "Ⓛ", "°", "±",
        "↧", "≥", "≤", "⌴", "⌵", "µ", "✓", "℄",
    ],
    "TOOLING": ["VISUAL", "CALIPER", "CERTIFICATION", "TAPE ", "PROTRACTOR", "ANGLE GAGE", "THREAD GAGE", "HARDWARE", "FITMENT/NHA", "MICROMETER"],
    "ATTRIBUTE": ["PASS", "FAIL"],
}


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _safe_cell_value(characteristic: Any, attr: str, default: Any = "") -> Any:
    return getattr(characteristic, attr, default)


def _characteristic_metadata(characteristic: Any) -> dict[str, Any]:
    metadata = getattr(characteristic, "metadata", {}) or {}
    return metadata if isinstance(metadata, dict) else {}


def _row_values(characteristic: Any) -> dict[str, Any]:
    return {
        "Char Number": _safe_cell_value(characteristic, "char_number"),
        "Reference Location": _safe_cell_value(characteristic, "reference_location"),
        "Requirement LSL": _safe_cell_value(characteristic, "lsl"),
        "Requirement Nominal": _safe_cell_value(characteristic, "nominal"),
        "Requirement USL": _safe_cell_value(characteristic, "usl"),
        "Type": _safe_cell_value(characteristic, "type"),
        "Inspection Actual": _safe_cell_value(characteristic, "actual", ""),
        "Tooling Used": _safe_cell_value(characteristic, "tooling", ""),
        # Extraction/operator notes are diagnostics, NEVER inserted in the FAI report.\n        "Comments": "",
    }


def _tolerance_needs_review(characteristic: Any, values: dict[str, Any]) -> bool:
    """A flagged or missing tolerance must never be silently formula-passable.

    Ambiguous explicit tolerances can carry numerical *default* limits, so
    checking for missing limits alone is insufficient after positional binding.
    """
    metadata = _characteristic_metadata(characteristic)
    return (
        values["Requirement LSL"] is None
        or values["Requirement USL"] is None
        or metadata.get("tolerance_review_required") is True
        or metadata.get("review_required") is True
        or metadata.get("tolerance_status") == "review_required"
    )


def _pick_sheet(wb):
    return wb[EXACT_R3_SHEET] if EXACT_R3_SHEET in wb.sheetnames else wb.active


def _is_r3_form(ws) -> bool:
    markers = [str(ws[cell].value or "").upper() for cell in ("A3", "A22", "C22", "G22", "J22")]
    joined = " ".join(markers)
    return "FIRST ARTICLE" in joined and "CHAR" in joined and "REQUIREMENT" in joined and "INSPECTION RESULT" in joined


def _copy_row_style(ws, source_row: int, target_row: int) -> None:
    for col in range(1, ws.max_column + 1):
        src = ws.cell(row=source_row, column=col)
        dst = ws.cell(row=target_row, column=col)
        if src.has_style:
            dst._style = copy.copy(src._style)
        if src.number_format:
            dst.number_format = src.number_format
        if src.alignment:
            dst.alignment = copy.copy(src.alignment)
        if src.border:
            dst.border = copy.copy(src.border)
        if src.fill:
            dst.fill = copy.copy(src.fill)
        if src.font:
            dst.font = copy.copy(src.font)
    ws.row_dimensions[target_row].height = ws.row_dimensions[source_row].height or R3_BODY_ROW_HEIGHT


def _copy_merged_ranges_for_row(ws, source_row: int, target_row: int) -> None:
    existing = {str(rng) for rng in ws.merged_cells.ranges}
    for merged in list(ws.merged_cells.ranges):
        if merged.min_row == source_row and merged.max_row == source_row:
            row_delta = target_row - source_row
            ref = f"{get_column_letter(merged.min_col)}{merged.min_row + row_delta}:{get_column_letter(merged.max_col)}{merged.max_row + row_delta}"
            if ref not in existing:
                ws.merge_cells(ref)
                existing.add(ref)


def _ensure_list_sheets(wb) -> None:
    for sheet_name, values in LIST_SHEET_SPECS.items():
        ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.create_sheet(sheet_name)
        for row, value in enumerate(values, start=1):
            ws.cell(row=row, column=1).value = value


def _add_list_validation(ws, range_ref: str, formula1: str) -> None:
    validation = DataValidation(type="list", formula1=formula1, allow_blank=True)
    validation.error = "Choose a listed value or leave blank."
    validation.errorTitle = "Invalid selection"
    validation.prompt = "Choose from the list."
    validation.promptTitle = "EZ FAI"
    ws.add_data_validation(validation)
    validation.add(range_ref)


def _r3_inclusive_formula(row: int) -> str:
    return f'=IF(J{row}="","",IF(AND(J{row}>=C{row},J{row}<=E{row}),"X",""))'


def _required_r3_end_row(characteristic_count: int) -> int:
    return max(R3_TEMPLATE_END_ROW, R3_START_ROW + max(characteristic_count, 1) - 1)


def _ensure_r3_row_capacity(ws, characteristic_count: int) -> int:
    required_end_row = _required_r3_end_row(characteristic_count)
    if required_end_row <= R3_TEMPLATE_END_ROW:
        return R3_TEMPLATE_END_ROW
    extra_rows = required_end_row - R3_TEMPLATE_END_ROW
    insert_at = R3_TEMPLATE_END_ROW + 1
    ws.insert_rows(insert_at, amount=extra_rows)
    for row in range(insert_at, required_end_row + 1):
        _copy_row_style(ws, R3_TEMPLATE_END_ROW, row)
        _copy_merged_ranges_for_row(ws, R3_TEMPLATE_END_ROW, row)
    return required_end_row


def _reset_r3_rows(ws, start_row: int, end_row: int) -> None:
    for row in range(start_row, end_row + 1):
        ws.cell(row=row, column=R3_COLUMNS["Char Number"]).value = row - start_row + 1
        for header in ["Reference Location", "Requirement LSL", "Requirement Nominal", "Requirement USL", "Type", "Supplier Actual", "Supplier Yes", "Supplier No", "Inspection Actual", "Tooling Used", "Comments"]:
            ws.cell(row=row, column=R3_COLUMNS[header]).value = None
        # Keep the form designer's native pass/fail formula when present.
        disposition = ws.cell(row=row, column=R3_COLUMNS["In Spec"])
        if not (isinstance(disposition.value, str) and disposition.value.startswith("=")):
            disposition.value = _r3_inclusive_formula(row)


def _apply_r3_editable_layout(ws, end_row: int) -> None:
    if ws.sheet_properties.pageSetUpPr is None:
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    else:
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_area = f"A1:N{end_row}"
    ws.print_title_rows = "1:23"
    ws.freeze_panes = "A24"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.page_setup.scale = None
    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.25
    ws.page_margins.bottom = 0.25
    ws.page_margins.header = 0.1
    ws.page_margins.footer = 0.1
    ws.sheet_view.view = "normal"
    ws.sheet_view.showGridLines = False
    for row in range(22, 24):
        ws.row_dimensions[row].height = R3_HEADER_ROW_HEIGHT
    for row in range(R3_START_ROW, end_row + 1):
        ws.row_dimensions[row].height = R3_BODY_ROW_HEIGHT
        for col in range(1, 15):
            cell = ws.cell(row=row, column=col)
            existing = cell.alignment or Alignment()
            cell.alignment = Alignment(horizontal=existing.horizontal or "center", vertical="center", text_rotation=existing.textRotation, wrap_text=True, shrink_to_fit=False, indent=existing.indent)


def _fill_r3_header_metadata(ws, characteristics: list[Any]) -> None:
    if not characteristics:
        return
    metadata = _characteristic_metadata(characteristics[0])
    for key, cell_ref in R3_HEADER_METADATA.items():
        value = metadata.get(key)
        if value not in (None, ""):
            ws[cell_ref] = value


def _fill_r3_form(ws, characteristics: list[Any]) -> int:
    _fill_r3_header_metadata(ws, characteristics)
    end_row = _ensure_r3_row_capacity(ws, len(characteristics))
    _reset_r3_rows(ws, R3_START_ROW, end_row)
    for offset, characteristic in enumerate(characteristics):
        row = R3_START_ROW + offset
        values = _row_values(characteristic)
        ws.cell(row=row, column=R3_COLUMNS["Char Number"]).value = offset + 1
        ws.cell(row=row, column=R3_COLUMNS["Reference Location"]).value = values["Reference Location"]
        ws.cell(row=row, column=R3_COLUMNS["Requirement LSL"]).value = values["Requirement LSL"]
        ws.cell(row=row, column=R3_COLUMNS["Requirement Nominal"]).value = values["Requirement Nominal"]
        ws.cell(row=row, column=R3_COLUMNS["Requirement USL"]).value = values["Requirement USL"]
        ws.cell(row=row, column=R3_COLUMNS["Type"]).value = values["Type"]
        ws.cell(row=row, column=R3_COLUMNS["Inspection Actual"]).value = None
        # Never replace a formula with review diagnostics or altered pass/fail logic.
        disposition = ws.cell(row=row, column=R3_COLUMNS["In Spec"])
        if not (isinstance(disposition.value, str) and disposition.value.startswith("=")):
            disposition.value = _r3_inclusive_formula(row)
        ws.cell(row=row, column=R3_COLUMNS["Tooling Used"]).value = values["Tooling Used"]
        ws.cell(row=row, column=R3_COLUMNS["Comments"]).value = values["Comments"]
    _add_list_validation(ws, f"F{R3_START_ROW}:F{end_row}", "'CHARACTERISTICS'!$A$1:$A$33")
    _add_list_validation(ws, f"M{R3_START_ROW}:M{end_row}", "'TOOLING'!$A$1:$A$10")
    _add_list_validation(ws, f"H{R3_START_ROW}:I{end_row}", "'ATTRIBUTE'!$A$1:$A$2")
    _apply_r3_editable_layout(ws, end_row)
    return len(characteristics)


def _is_formula_master(ws) -> bool:
    """A controlled form with existing tolerance and disposition formulas.

    Detect the *structure*, not an employer name or filename. Avoid the R3
    restyling/reset routine for forms that already encode their own logic.
    """
    if not _is_r3_form(ws):
        return False
    # K-column pass/fail formulas also occur in ordinary R3 templates; only
    # pre-existing paired C/E limit formulas identify the native formula master.
    return any(
        isinstance(ws.cell(row, 3).value, str)
        and ws.cell(row, 3).value.startswith("=")
        and isinstance(ws.cell(row, 5).value, str)
        and ws.cell(row, 5).value.startswith("=")
        for row in range(R3_START_ROW, min(ws.max_row, R3_TEMPLATE_END_ROW) + 1)
    )


def _update_native_bound_formula(ws, row: int, column: int, nominal: Any, limit: Any, status: str) -> None:
    """Keep tolerance bounds as native Excel formulas, never static substitutes.

    Source-confirmed explicit tolerances can adjust the offset without changing
    cell formatting. For unverified defaults, retain the template's own formula.
    """
    cell = ws.cell(row, column)
    if status != "explicit" or not isinstance(nominal, (float, int)) or not isinstance(limit, (float, int)):
        return
    offset = nominal - limit if column == 3 else limit - nominal
    if offset < 0:
        return
    if offset == 0:
        proposed = f"=D{row}"
    else:
        proposed = f"=D{row}{'-' if column == 3 else '+'}{offset:.10g}"
    old = cell.value
    if isinstance(old, str) and old.startswith("="):
        native = re.fullmatch(rf"=D{row}\s*([+-])\s*(\d+(?:\.\d+)?)", old, re.I)
        if native:
            current = float(native.group(2)) * (1 if native.group(1) == ("-" if column == 3 else "+") else -1)
            if abs(current - offset) < 1e-8:
                return
    cell.value = proposed


def _template_formula_disagrees(ws, row: int, column: int, nominal: Any, limit: Any) -> bool:
    """Safely detect unverified mismatch between master formulas and candidate limits."""
    if not isinstance(nominal, (int, float)) or not isinstance(limit, (int, float)):
        return True
    original = ws.cell(row, column).value
    if not isinstance(original, str) or not original.startswith("="):
        return True
    if original.strip().upper() == f"=D{row}":
        master_offset = 0.0
    else:
        matched = re.fullmatch(rf"=D{row}\s*([+-])\s*(\d+(?:\.\d+)?)", original, re.I)
        if not matched:
            return True
        sign = 1 if matched.group(1) == ("-" if column == 3 else "+") else -1
        master_offset = float(matched.group(2)) * sign
    expected = nominal - limit if column == 3 else limit - nominal
    return abs(master_offset - expected) > 0.000001


def _verified_title_default(characteristic: Any, metadata: dict[str, Any]) -> bool:
    """Only adjust native bound formulas for a source-confirmed precision rule."""
    detected = metadata.get("title_block_detected", {}) or {}
    raw = str(_safe_cell_value(characteristic, "raw_text", "") or "")
    dim_type = str(_safe_cell_value(characteristic, "type", "") or "").upper()
    if dim_type in {"°", "ANGLE", "ANGULAR"}:
        return "angular" in detected or "angular_bend" in detected or "angular_mach" in detected
    if "/" in raw and "." not in raw:
        return "fractional" in detected
    decimal = re.search(r"\\.(\\d+)", raw)
    if decimal:
        return ("three_place" if len(decimal.group(1)) >= 3 else "two_place") in detected
    return False


def _fill_formula_master(ws, characteristics: list[Any]) -> int:
    """Fill ONLY inspection data in a native formula-bearing Excel form.

    Preserve the source drawing/image, merged cells, styles, original workbook
    sheets, print settings, validations, and all unaffected cell formulas.
    Never insert rows into a controlled master, which could move its footer.
    """
    if len(characteristics) > R3_TEMPLATE_CAPACITY:
        raise ValueError(
            f"The controlled Excel form holds {R3_TEMPLATE_CAPACITY} characteristics; "
            "split the inspection into additional forms rather than altering its layout."
        )
    _fill_r3_header_metadata(ws, characteristics)
    for offset, characteristic in enumerate(characteristics):
        row = R3_START_ROW + offset
        values = _row_values(characteristic)
        metadata = _characteristic_metadata(characteristic)
        ws.cell(row, R3_COLUMNS["Char Number"]).value = _safe_cell_value(characteristic, "char_number", offset + 1)
        ws.cell(row, R3_COLUMNS["Reference Location"]).value = values["Reference Location"]
        ws.cell(row, R3_COLUMNS["Requirement Nominal"]).value = values["Requirement Nominal"]
        ws.cell(row, R3_COLUMNS["Type"]).value = values["Type"]
        ws.cell(row, R3_COLUMNS["Tooling Used"]).value = values["Tooling Used"]
        # Never fill inspection measurements or acceptance decisions from OCR.
        ws.cell(row, R3_COLUMNS["Inspection Actual"]).value = None
        tolerance_status = str(metadata.get("tolerance_status", "default"))
        # Only write an Excel tolerance formula when supported by explicit
        # dimensional tolerance evidence or the correct title-block precision
        # rule. For unknown rules leave the original formula untouched and
        # report uncertainty outside the FAI workbook (debug/summary only).
        source_default = _verified_title_default(characteristic, metadata)
        if tolerance_status == "explicit" or (tolerance_status == "default" and source_default):
            for column, limit_header in (
                (R3_COLUMNS["Requirement LSL"], "Requirement LSL"),
                (R3_COLUMNS["Requirement USL"], "Requirement USL"),
            ):
                _update_native_bound_formula(
                    ws, row, column, values["Requirement Nominal"],
                    values[limit_header], "explicit",
                )
        # Original K-column pass/fail formula is intentionally never touched.
        # No comments, review notes, or extraction warnings inside the FAI form.
        ws.cell(row, R3_COLUMNS["Comments"]).value = None
    return len(characteristics)


def _header_targets() -> dict[str, str]:
    targets: dict[str, str] = {}
    for canonical, aliases in HEADER_ALIASES.items():
        targets[_norm(canonical)] = canonical
        for alias in aliases:
            targets[_norm(alias)] = canonical
    return targets


def _find_generic_header_row(ws) -> tuple[int, dict[str, int]]:
    targets = _header_targets()
    best_row = 1
    best_mapping: dict[str, int] = {}
    for row in range(1, min(ws.max_row, 80) + 1):
        mapping: dict[str, int] = {}
        for col in range(1, min(ws.max_column, 80) + 1):
            value = _norm(ws.cell(row=row, column=col).value)
            if value in targets:
                mapping.setdefault(targets[value], col)
        if len(mapping) > len(best_mapping):
            best_row, best_mapping = row, mapping
    if len(best_mapping) < 4:
        best_row = 1
        best_mapping = {header: col for col, header in enumerate(GENERIC_HEADERS, start=1)}
        for header, col in best_mapping.items():
            ws.cell(row=best_row, column=col).value = header
    else:
        for header in GENERIC_HEADERS:
            if header not in best_mapping:
                col = ws.max_column + 1
                ws.cell(row=best_row, column=col).value = header
                best_mapping[header] = col
    return best_row, best_mapping


def _fill_generic(ws, characteristics: list[Any]) -> int:
    header_row, columns = _find_generic_header_row(ws)
    start_row = header_row + 1
    for offset, characteristic in enumerate(characteristics):
        row = start_row + offset
        if offset > 0:
            _copy_row_style(ws, start_row, row)
        values = _row_values(characteristic)
        for header, value in values.items():
            if header == "Inspection Actual":
                value = None
            ws.cell(row=row, column=columns[header]).value = value
        actual_col = get_column_letter(columns["Inspection Actual"])
        lsl_col = get_column_letter(columns["Requirement LSL"])
        usl_col = get_column_letter(columns["Requirement USL"])
        in_spec_col = columns["In Spec"]
        formula_cell = ws.cell(row=row, column=in_spec_col)
        if not (isinstance(formula_cell.value, str) and formula_cell.value.startswith("=")):
            formula_cell.value = f'=IF({actual_col}{row}="","",IF(AND({actual_col}{row}>={lsl_col}{row},{actual_col}{row}<={usl_col}{row}),"X",""))'
    return len(characteristics)


def template_row_capacity(template_path: str | Path) -> int | None:
    wb = load_workbook(template_path, read_only=True, data_only=False)
    try:
        ws = _pick_sheet(wb)
        if _is_r3_form(ws):
            return R3_TEMPLATE_CAPACITY

        targets = _header_targets()
        best_row = None
        best_count = 0
        for row in range(1, min(ws.max_row, 80) + 1):
            found=set()
            for col in range(1, min(ws.max_column, 80) + 1):
                normalized=_norm(ws.cell(row=row,column=col).value)
                if normalized in targets:
                    found.add(targets[normalized])
            if len(found)>best_count:
                best_row=row
                best_count=len(found)
        if best_row is not None and best_count>=4:
            return max(0,ws.max_row-best_row)
        return None
    finally:
        wb.close()


def fill_fai_template(template_path: str | Path, characteristics: Iterable[Any], output_path: str | Path | None = None) -> Path:
    template_path = Path(template_path)
    characteristics = list(characteristics)
    if output_path is None:
        drawing_name = "FAI"
        if characteristics:
            metadata = _characteristic_metadata(characteristics[0])
            drawing_name = metadata.get("drawing_name", drawing_name)
        suffix = ".xlsm" if template_path.suffix.lower() == ".xlsm" else ".xlsx"
        output_path = template_path.with_name(f"{drawing_name}_FAI{suffix}")
    output_path = Path(output_path)
    if output_path.resolve() == template_path.resolve():
        raise ValueError("FAI Excel output cannot overwrite the original template.")
    keep_vba = template_path.suffix.lower() == ".xlsm"
    wb = load_workbook(template_path, keep_vba=keep_vba)
    ws = _pick_sheet(wb)
    if _is_formula_master(ws):
        _fill_formula_master(ws, characteristics)
    elif _is_r3_form(ws):
        _ensure_list_sheets(wb)
        _fill_r3_form(ws, characteristics)
    else:
        _fill_generic(ws, characteristics)
    wb.save(output_path)
    wb.close()
    return output_path



def _image_from_bytes(original: Any, content: bytes) -> Any:
    """Give each copied Excel image its own independent, still-open stream."""
    from io import BytesIO
    from openpyxl.drawing.image import Image

    fresh = Image(BytesIO(content))
    fresh.anchor = copy.deepcopy(original.anchor)
    fresh.width = original.width
    fresh.height = original.height
    return fresh


def _copy_controlled_form_sheet(book: Any, master: Any, part: int, image_bytes: list[tuple[Any, bytes]]) -> Any:
    """Clone a pristine blank Excel form, including features copy_worksheet omits.

    openpyxl's copy_worksheet copies styled cells, merged ranges, row/column
    dimensions, and more, but deliberately skips images/charts, validations,
    conditional formatting and some printing properties. Preserve them here
    because inspection forms can contain their own logo and native formulas.
    """
    continuation = book.copy_worksheet(master)
    continuation.title = f"{master.title} {part}"
    # Group all FAI pages as adjacent tabs, ahead of auxiliary list sheets.
    book.move_sheet(
        continuation,
        offset=(book.index(master) + part - 1) - book.index(continuation),
    )
    continuation.data_validations = copy.deepcopy(master.data_validations)
    continuation.conditional_formatting = copy.deepcopy(master.conditional_formatting)
    continuation.page_margins = copy.deepcopy(master.page_margins)
    continuation.page_setup = copy.deepcopy(master.page_setup)
    continuation.print_options = copy.deepcopy(master.print_options)
    continuation.sheet_properties = copy.deepcopy(master.sheet_properties)
    continuation.protection = copy.deepcopy(master.protection)
    continuation.auto_filter = copy.deepcopy(master.auto_filter)
    continuation.row_breaks = copy.deepcopy(master.row_breaks)
    continuation.col_breaks = copy.deepcopy(master.col_breaks)
    continuation.freeze_panes = master.freeze_panes
    if master.print_area:
        # Same fixed geometry, different tab name.
        continuation.print_area = "A1:N48"
    if master.print_title_rows:
        continuation.print_title_rows = master.print_title_rows
    if master.print_title_cols:
        continuation.print_title_cols = master.print_title_cols
    for graphic, blob in image_bytes:
        continuation.add_image(_image_from_bytes(graphic, blob))
    for chart in master._charts:
        continuation.add_chart(copy.deepcopy(chart))
    return continuation


def fill_fai_template_pages(
    template_path: str | Path,
    characteristics: Iterable[Any],
    output_path: str | Path,
) -> list[Path]:
    """Produce exactly ONE Excel file containing all FAI continuation forms.

    Controlled 25-row templates become one workbook with tabs FAI FORM,
    FAI FORM 2, FAI FORM 3... . Each tab begins as a copy of the original
    unmodified blank template, retaining formatting, merged cells, formulas,
    images, validations and print layout. Characteristic numbers stay global.
    The list return type remains for compatibility, but contains ONE path.
    """
    template_path = Path(template_path)
    output_path = Path(output_path)
    chars = list(characteristics)
    if output_path.resolve() == template_path.resolve():
        raise ValueError("FAI Excel output cannot overwrite the original template.")
    if not output_path.suffix.lower() in {".xlsx", ".xlsm"}:
        raise ValueError("FAI output must be an Excel .xlsx or .xlsm workbook.")
    book = load_workbook(
        template_path, data_only=False, keep_vba=template_path.suffix.lower() == ".xlsm"
    )
    try:
        master = _pick_sheet(book)
        if not _is_r3_form(master):
            _fill_generic(master, chars)
        else:
            native_master = _is_formula_master(master)
            count = max(1, (len(chars) + R3_TEMPLATE_CAPACITY - 1) // R3_TEMPLATE_CAPACITY)
            # Every image must have a distinct underlying byte stream.
            # openpyxl closes image streams while saving; a shallow copy would
            # leave later images pointing to closed streams.
            image_bytes = [(graphic, graphic._data()) for graphic in master._images]
            if image_bytes:
                master._images.clear()
                for graphic, blob in image_bytes:
                    master.add_image(_image_from_bytes(graphic, blob))
            # Clone before filling any pages, so later tabs remain pristine
            # instead of inheriting the first page's entered inspection data.
            sheets = [master] + [
                _copy_controlled_form_sheet(book, master, part, image_bytes)
                for part in range(2, count + 1)
            ]
            for index, sheet in enumerate(sheets):
                batch = chars[
                    index * R3_TEMPLATE_CAPACITY:(index + 1) * R3_TEMPLATE_CAPACITY
                ]
                if native_master:
                    _fill_formula_master(sheet, batch)
                else:
                    # Ordinary R3-based sheets also use fixed page geometry;
                    # never append body rows into a controlled form's footer.
                    _fill_r3_form(sheet, batch)
                # A controlled master may pre-number all 25 empty body rows.
                # Empty slots must not carry phantom balloon numbers,
                # especially on the final continuation tab.
                for unused in range(R3_START_ROW + len(batch), R3_TEMPLATE_END_ROW + 1):
                    sheet.cell(unused, R3_COLUMNS["Char Number"]).value = None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        book.save(output_path)
    finally:
        book.close()
    return [output_path]
