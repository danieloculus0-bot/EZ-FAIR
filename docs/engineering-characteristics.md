# Engineering characteristic interpretation (experimental)

This feature is used by the installed Windows `polished_gui.py` launcher and `local_test_runner.py`. It runs **after** the existing vector-PDF numeric extractor, not instead of it. Original drawings stay local.

## Behaviors

- Classifies common bottom title/revision regions, right-hand document-control stamps, BOM rows and scale labels as non-characteristics. Geometry is layout-dependent and must be reviewed on different customer templates.
- Reads title-block defaults per sheet, including .XX, .XXX, fractional X/Y and an indicated angular value. Unknown tolerance cases produce **blank limits** and a review note rather than using unverified hard-coded defaults.
- Uses exact +/− asymmetric limits and readable symmetric callouts before general tolerance defaults. Neighboring tolerance numerals are suppressed as standalone characteristics. If a CAD font omits ± from the text layer, a nearby unsigned tolerance is **provisional** and marked for manual inspection.
- Groups recognizable UNC/UNF/NPT thread specifications into one categorical requirement, including their class where present. Generates `THREAD` rows with no fabricated numeric limits.
- Preserves clearly readable manufacturing instructions as `NOTE` requirements, and recognized GD&T text as `GD&T` requirements with human-review flags. Weld-symbol/leader interpretation is **not certified**. Do not assume vector-only FCFs, weld symbols, datum association or leader geometry have been fully parsed.
- Preserves the sheet drawing-number association in each characteristic's metadata when legible.

## Test

```powershell
python -m pytest -q tests/test_engineering_characteristics.py
```

To run the optional real drawing regression, copy the controlled 11-sheet file to `fixtures/016858_REV_D_NDM_3-5-25_BALLOONED.pdf`. This fixture **is not committed** because it contains customer proprietary material. The synthetic tests run without it. Local results must be checked against the **original unballooned** source before deployment; the supplied ballooned document is used only as an intermediate regression reference.

## Known boundaries

The parser is not a standards-compliant GD&T semantic engine. The current text-based grouping cannot establish leader connectivity across vector graphics, interpret all weld symbols or fully distinguish every crowded drawing table. `review_required`, `tolerance_source` and `sheet_rules` in characteristic metadata record those uncertainties. QA/QE approval of the generated FAI is mandatory.

**Do not automatically accept or reject product on inferred/unverified acceptance limits.**
