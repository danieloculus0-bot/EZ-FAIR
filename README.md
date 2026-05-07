# EZ FAI Builder

Local Windows-friendly Python desktop MVP for creating a ballooned PDF and FAI Excel workbook from a PDF blueprint.

## Features

- Select a PDF blueprint and Excel FAI template from a simple tkinter GUI.
- Extract likely dimensional characteristics with PyMuPDF (`fitz`), including:
  - Linear decimal dimensions such as `16.00`, `10.62`, `.97`, and `2.72`.
  - Angular dimensions such as `76.00°`.
  - Diameter dimensions marked with `Ø` or `⌀`.
  - Basic weld callout candidates near weld-related text/symbols.
  - Explicit bilateral tolerances such as `+.13 / -.03`.
- Apply title block default tolerances when no explicit tolerance is detected:
  - Two-place decimals: `±0.02`.
  - Three-place decimals: `±0.005`.
  - Angular dimensions: `±2`.
- Review extracted rows before export and edit nominal, LSL, USL, type, tooling, and comments.
- Generate outputs without overwriting the source PDF or Excel template:
  - `[drawing name]_BALLOONED.pdf`
  - `[drawing name]_FAI.xlsx`
  - `EZ_FAI_DEBUG_REPORT.txt` with extracted rows and skipped candidates

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python ez_fai_builder.py
```

For a batch/debug run without opening the GUI, pass the PDF and template paths:

```bash
python ez_fai_builder.py path\to\DVM-AE.pdf path\to\EZ_FAB_FAI_TEMPLATE.xlsx
```


## Local real drawing test

Use this workflow for real customer drawings and corrected FAI templates without committing proprietary files.

1. Put exactly one real blueprint PDF and exactly one real FAI Excel template (`.xlsx` or `.xlsm`) in `local_inputs/`.
2. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\\run_local_test.ps1
```

3. Open `local_outputs/` and review:
   - `[drawing name]_BALLOONED.pdf`
   - `[drawing name]_FAI.xlsx`
   - `EZ_FAI_DEBUG_REPORT.txt`
   - `EXTRACTION_SUMMARY.txt`
4. Do not commit `local_inputs/` or `local_outputs/`; they are intentionally ignored.

## Notes

This is an MVP extraction engine, not a commercial-grade drawing parser. The review table is intentionally part of the workflow so users can delete false positives and correct extracted values before generating the final files.
# EZ-FAIR

Local first article builder for EZ Fabricating.

## What it does

- Reads a PDF blueprint
- Extracts likely dimensions
- Creates a ballooned PDF
- Fills an EZ FAB first article Excel template
- Leaves admin fields blank for manual entry
- Uses inclusive tolerance logic: Actual >= LSL and Actual <= USL

## Local real drawing test

Put exactly one customer PDF and exactly one Excel FAI template in `local_inputs/`.

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_local_test.ps1
```

Outputs appear in `local_outputs/`:

- `[drawing]_BALLOONED.pdf`
- `[drawing]_FAI.xlsx`
- `EZ_FAI_DEBUG_REPORT.txt`
- `EXTRACTION_SUMMARY.txt`

Do not commit customer PDFs or FAI templates.
