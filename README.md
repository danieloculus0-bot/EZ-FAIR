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
