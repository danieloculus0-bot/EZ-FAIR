# EZ-FAIR

**Working Python desktop application** for First Article Inspection drawing extraction and FAI document building.

**[Try the interactive EZ-FAIR demo](https://danieloculus0-bot.github.io/BEAN/portfolio/ez-fair/)** · **[View The Workshop](https://danieloculus0-bot.github.io/BEAN/portfolio/)**

The public demo provides a synthetic drawing walkthrough; the real PDF extraction and FAI document generation run in the desktop Python application. It produces reviewable candidate characteristics from PDFs, not automatically certified measurements.

## Current build state

**Reviewed:** 2026-10-20 · **Inspected main:** `223ad25777d6` · **Stage:** working desktop application under active engineering refinement; individual workflow evidence below.

- [EZ-FAIR tests](https://github.com/danieloculus0-bot/EZ-FAIR/actions/runs/39502697068) — **Passed** at inspected `main`.

[Live CI and build history](https://github.com/danieloculus0-bot/EZ-FAIR/actions) takes precedence over this dated snapshot.

## Working capabilities

- PyMuPDF vector extraction, optional offline OCR, title-block tolerance and GD&T candidates, ballooned PDF plus editable FAI workbook.
- Charcoal/steel/lime desktop presentation (Tkinter workbench); characteristic editing and source-specific comments.
- Controlled ForgeVault released-PDF handoff validates identity, revision and SHA-256 before extracting review-required characteristics; Axiom integration exercised against real source on Windows/Linux.

## Install and run

`python -m venv .venv`, install `requirements.txt`, then `python ez_fair.py` for the enhanced desktop application. The optional Tk workbench also lives in `polished_gui.py`. Run `python -m pytest -q` for automated checks. [Full instructions and drawing-testing walkthrough](docs/archive/README_2026-10-20_before_refresh.md).

## Known engineering limits

- OCR and GD&T candidates may be incomplete or incorrect; humans must review characteristics, tolerance interpretation, and file-to-balloon correspondence.
- Extracted inspection proposals contain no measured values or implicit passes. The controlled file integration is not yet an authenticated shared-user release screen.
- Current automated tests do not constitute a broad representative customer-drawing accuracy benchmark.

## Next priorities

Build a representative held-out drawing set, score recall/false positives and source-to-balloon traceability, and improve the controlled-review UX.

## Documentation

- [Cross-app FAI test](https://github.com/danieloculus0-bot/Axiom_Beta/blob/main/integration_tests/test_controlled_fai_wiring.py)
- [Local drawing test runner](run_local_test.ps1)
- [**Full earlier README: setup, feature history, experiments and rationale**](docs/archive/README_2026-10-20_before_refresh.md)

Historical details are archived, not discarded. Unverified planned features are not silently described as shipped.
