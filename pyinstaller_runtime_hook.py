"""PyInstaller runtime configuration for the bundled Tesseract engine."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))


root = _bundle_root()
tesseract_dir = root / "tesseract"
tesseract_exe = tesseract_dir / "tesseract.exe"
tessdata = tesseract_dir / "tessdata"

if tesseract_exe.exists():
    os.environ["TESSERACT_CMD"] = str(tesseract_exe)
    os.environ["TESSDATA_PREFIX"] = str(tessdata)
    os.environ["PATH"] = str(tesseract_dir) + os.pathsep + os.environ.get("PATH", "")
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_exe)
    except Exception:
        pass
