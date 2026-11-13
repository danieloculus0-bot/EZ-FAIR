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
# EZ-FAIR

Local desktop application for building **review-required** First Article Inspection
(FAI) candidate characteristics, ballooned PDFs and editable FAI workbooks.

**Status: supervised technical beta.** An operator must verify every extracted
characteristic and tolerance against the original customer drawing before using
an FAI output. This is **not** unattended, customer-facing or automatically
certified inspection software. No actual measurements or acceptance decisions
are generated without review.

[Current GitHub Actions checks](https://github.com/danieloculus0-bot/EZ-FAIR/actions)
are the source of truth for CI status. The version recorded in
`pyproject.toml` is `0.2.0b1`; release readiness is a separate decision.

## What it can do

- Extract vector-text candidates, including dimensions and review-required
  fractional and weld callouts through the active desktop extraction pipeline.
- Generate a ballooned PDF, editable FAI workbook and extraction/debug reports.
- Offer an alternative enhanced Tk launcher with optional offline OCR for scanned
  PDFs, title-block settings and basic GD&T candidates.
- Validate controlled-file identity and hashes for a local ForgeVault-style
  integration handoff. **This is not an authenticated multi-user approval screen.**
- Work with synthetic demo inputs without publishing private drawings.

The polished Windows launcher, enhanced Tk GUI, base Python GUI and Python
batch entrypoint now share `hybrid_extraction.py`: the native PDF parser
and offline OCR run independently on each drawing when OCR is enabled, even
when native extraction finds dimensions. Matched same-location candidates retain
both sources; disagreements and OCR-only findings remain visible and are marked
review-required, rather than hiding native results. `extractor_active.py`
continues to compose the precision and fraction/weld parsers. The synthetic
local test runner still uses that native-only path to keep its baseline stable.

Controlled Excel templates with existing C/E tolerance formulas are handled
without changing their original formatting, merges, logos/images, sheet list,
print settings or unaffected formulas. Explicit drawing tolerances and verified title-block decimal/angle
rules adjust the C/E limit *formulas*, not the workbook design. Original
K-column pass/fail formulas are preserved byte-for-byte as Excel expressions,
and diagnostic warnings NEVER overwrite K or get exported into the Comments
column. Unknown and conflicting evidence stays in the separate extraction
debug/summary reports. The original master is never modified. The original template file is never overwritten. Master forms with
a fixed 25-row body never expand or move their footer. When more than 25
characteristics are selected, the desktop and Python batch exporters create
**one FAI Excel workbook** with additional original-layout sheets named
`FAI FORM 2`, `FAI FORM 3`, etc. Each new tab retains the same
logos, formulas, data validations, print settings and styles as the master.
Global characteristic numbers continue across all tabs and match the balloons. The polished Windows
workbench always releases its busy state and reports an error if an export
fails. A distinct PDF-originated title-block zone filter reduces balloons on
administrative tolerances while leaving drawing-area dimensions available.
Radius and angle classification uses each callout's own glyphs rather than a
neighboring dimension's degree sign.
Do not upload private employer/customer templates into this public repository.
These behaviors require an on-machine test with authorized local drawings and
templates before being considered production-verified.

## Built-in Excel form and private default override

**No Excel template needs to be selected to start an FAI.** On first use,
both desktop GUIs generate and select the original neutral
`local_templates/EZFAIR_Default_FAI.xlsx` master. This is a
full **Excel workbook**, not a dark-themed preview or substituted report.
It has 25 editable inspection rows, original Excel LSL/USL/acceptance
formulas, manual actual-value fields and dropdown lists. More than 25
reviewed characteristics add continuation sheets within the same output workbook.

The default is deliberately **unbranded** and independently created from
generic FAI concepts; no employer/customer template or logo is bundled or
republished. A site-controlled private Excel master can instead be placed at
`local_templates/FAI_MASTER.xlsx` on the operator's computer.
If it exists, EZ-FAIR selects it automatically. Alternatively, browse to a
site-approved workbook once: the app saves only its local path in
`~/.ezfair_default_template.json` and selects that file on subsequent
runs. Neither local file nor the preference is committed to GitHub.
Select **Use Built-In FAI** to return to the neutral template. Existing
source workbooks are never overwritten by export.

The Python command-line path can be used with only a drawing PDF:
`python ez_fai_builder.py drawing.pdf`. Supplying a template
as a second argument is still supported.

## Install locally

Requires Python 3.11+; Windows desktop is the primary target. In a fresh
folder containing this repository:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe polished_gui.py
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
The optional enhanced OCR/settings GUI can be started with
` .\.venv\Scripts\python.exe ez_fair.py ` (without the surrounding spaces).
On Linux/macOS replace the virtual-environment executable path with
`.venv/bin/python`; a graphical desktop and Tk support are needed to open
either GUI. All packages in `requirements.txt` are pinned for beta
reproducibility. To check Python components without opening windows, run
`python -m pytest -q` and `python tools/repo_health.py` in the venv.

### Scanned PDF OCR requires an extra Windows application

The Python package `pytesseract` is **only a wrapper**. For scanned or
flattened PDFs, install the separate [Tesseract OCR engine](https://tesseract-ocr.github.io/tessdoc/Installation.html)
with English language data, then restart EZ-FAIR. On Windows the usual
location is `C:\Program Files\Tesseract-OCR\tesseract.exe`. The enhanced
launcher checks the system PATH and common Windows install folders. You can
also set `EZFAIR_TESSERACT_CMD` to the full executable path:

```powershell
$env:EZFAIR_TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
.\.venv\Scripts\python.exe -c "import pytesseract; from ocr_support import configure_tesseract; print(configure_tesseract(pytesseract))"
```

No external OCR engine is needed for vector PDFs. The Windows setup scripts
warn if Tesseract is missing; OCR errors explain which installation is needed.

### Windows installation and update scripts

`install_windows.ps1` and `update_windows.ps1` target the versioned
`v0.2.0b1` archive, **not the moving main branch**. That tag must be
published after passing CI, and the scripts are intended to be run only from
an approved release. Optionally use `-ExpectedSha256 <verified-hash>` to
reject mismatched downloaded archives. See [release procedure](docs/RELEASE_PROCESS.md).
The update script preserves `local_inputs` and `local_outputs`.
Windows installer behavior still needs on-machine end-to-end verification.

## Testing, limitations and next steps

Run `python -m pytest -q`. CI additionally checks all tracked Python files,
headless GUI imports, a package installation, synthetic output generation,
benchmark reporting and Windows PowerShell syntax (not a full install).

[Local labeled accuracy benchmark](docs/BENCHMARK.md) supports evaluation of
precision, recall and source-rectangle provenance using synthetic or
**explicitly cleared** PDFs. The bundled demo is not a representative accuracy
benchmark. Vector-only GD&T/weld semantics, missing or assumed tolerances,
balloon location, false positives and actual FAI disposition all require
human checking. The benchmark does **not** validate balloon placement.

Open issues include editable balloon placement, exclusions and roadmap work.
Draft engineering parser PR #6 remains unmerged until behavior is verified on
held-out drawings. Extraction-module consolidation and authenticated release
approval are further development work. The [synthetic interactive demo,
maintained separately in BEAN](https://danieloculus0-bot.github.io/BEAN/portfolio/ez-fair/)
is not an EZ-FAIR release dependency.

**License:** no distribution license has yet been selected by the repository
owner; a public repository is not itself permission to redistribute.
Do not call this an approved redistributable installer until that decision
and the release review are complete.

## Documentation

- [Benchmark design and private testing](docs/BENCHMARK.md)
- [Release procedure](docs/RELEASE_PROCESS.md)
- [Local drawing test runner](run_local_test.ps1)
- [Archived engineering history and earlier install notes](docs/archive/README_2026-10-20_before_refresh.md)
- [Cross-app integration test in Axiom_Beta](https://github.com/danieloculus0-bot/Axiom_Beta/blob/main/integration_tests/test_controlled_fai_wiring.py)
