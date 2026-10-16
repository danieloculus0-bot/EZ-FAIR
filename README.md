# EZ FAIR

Local Windows-friendly Python desktop application for creating a ballooned PDF and FAI Excel workbook from a PDF blueprint.

## Features

- Select a PDF blueprint and Excel FAI template from a tkinter GUI.
- Extract likely dimensional characteristics with PyMuPDF (`fitz`), including linear, angular, diameter, weld, and explicit bilateral tolerances.
- Fall back to fully offline Tesseract OCR when a scanned or flattened PDF returns zero vector dimensions.
- Detect common title-block default tolerance formats in the bottom-right corner of the drawing.
- Save shop-specific two-place, three-place, and angular default tolerances in the Settings tab.
- Recognize common GD&T symbols and text for position, flatness, parallelism, profile, perpendicularity, angularity, straightness, circularity, cylindricity, concentricity, and runout.
- Review extracted rows before export and edit nominal, LSL, USL, type, tooling, and comments.
- Generate outputs without overwriting the source PDF or Excel template:
  - `[drawing name]_BALLOONED.pdf`
  - `[drawing name]_FAI.xlsx`
  - `EZ_FAI_DEBUG_REPORT.txt`

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

OCR also requires the offline Windows Tesseract engine. Install Tesseract and ensure `tesseract.exe` is available on PATH. No drawing data is sent to a cloud service.

## Run

Launch the installed Windows workflow with the new engineering interpretation layer:

```bash
python polished_gui.py
```

`install_windows.ps1` uses this launcher. `ez_fair.py` is the older settings/OCR launcher and does not yet use the same engineering parser.

The original MVP launcher remains available as:

```bash
python ez_fai_builder.py
```

## Extraction behavior

For `polished_gui.py`:

1. It runs the numeric vector PDF extractor and the engineering interpretation layer.
2. It filters template/revision/BOM clutter and groups technical callouts before numbering balloons.
3. It reads sheet-specific title-block tolerance rules, applying explicit symmetric/asymmetric limits first.
4. It records thread specifications and readable manufacturing notes as single categorical requirements, and flags incomplete GD&T/weld interpretations for QE review.
5. Every result remains editable in the review table before export. See [engineering parser notes](docs/engineering-characteristics.md).

The legacy `ez_fair.py` path retains its separate settings/OCR and GD&T behavior; the newer engineering parsing is not yet wired into that interface.

Default settings are saved locally in `~/.ez_fair_settings.json`.

## Local real drawing test

Use this workflow for real customer drawings and corrected FAI templates without committing proprietary files.

1. Put exactly one real blueprint PDF and exactly one FAI Excel template (`.xlsx` or `.xlsm`) in `local_inputs/`.
2. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_local_test.ps1
```

3. Review the generated files in `local_outputs/`.
4. Do not commit `local_inputs/` or `local_outputs/`; they are intentionally ignored.

## Notes

This remains a review-assisted extraction engine. OCR and GD&T recognition can produce false positives on degraded scans or proprietary CAD fonts, so the editable review table remains part of the controlled workflow.
