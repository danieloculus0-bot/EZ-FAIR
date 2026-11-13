"""Explicit extraction entrypoint used by the desktop workbench and local runner.

Do not silently downgrade to an older parser on import errors.
Fraction/weld and precision modules still compose over extractor_engine pending
a held-out drawing benchmark and safe consolidation.
"""
from extractor_fraction_weld_patch import (
    Characteristic, SkippedCandidate, TITLE_BLOCK_DEFAULTS, TOLERANCE_PATTERN,
    add_pdf_balloons, extract_pdf_dimensions, get_last_skipped_candidates,
    write_debug_report,
)

EXTRACTOR_VARIANT = "fraction_weld_precision"
