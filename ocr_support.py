"""Find and validate the offline Tesseract OCR executable."""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_tesseract() -> str | None:
    """Honor an explicit override, PATH, then common Windows install locations."""
    configured = os.environ.get("EZFAIR_TESSERACT_CMD", "").strip().strip('"')
    if configured:
        candidate = Path(configured).expanduser()
        return str(candidate) if candidate.is_file() else shutil.which(configured)

    resolved = shutil.which("tesseract")
    if resolved:
        return resolved
    if os.name == "nt":
        for key in ("ProgramFiles", "ProgramFiles(x86)"):
            root = os.environ.get(key)
            if root:
                candidate = Path(root) / "Tesseract-OCR" / "tesseract.exe"
                if candidate.is_file():
                    return str(candidate)
    return None


def configure_tesseract(pytesseract_module) -> str:
    """Fail with a useful message if the OCR engine is absent or unusable."""
    executable = find_tesseract()
    if not executable:
        raise RuntimeError(
            "Tesseract OCR engine not found. Scanned PDFs need the separate Tesseract "
            "application, not just the pytesseract Python package. Install Tesseract "
            "with English language data, restart EZ-FAIR, or set EZFAIR_TESSERACT_CMD "
            "to the full path of tesseract.exe. Vector PDFs do not require OCR."
        )
    pytesseract_module.pytesseract.tesseract_cmd = executable
    try:
        pytesseract_module.get_tesseract_version()
    except Exception as exc:
        raise RuntimeError(
            f"Tesseract was found at {executable!r} but could not be started. "
            "Check the executable and permissions, then retry."
        ) from exc
    return executable
