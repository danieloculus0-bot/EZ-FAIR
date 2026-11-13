"""Tesseract is separate from the Python pytesseract package."""
from types import SimpleNamespace

import pytest
import ocr_support


def test_missing_ocr_executable_is_actionable(monkeypatch):
    monkeypatch.setattr(ocr_support, "find_tesseract", lambda: None)
    fake = SimpleNamespace(pytesseract=SimpleNamespace(tesseract_cmd="unused"))
    with pytest.raises(RuntimeError, match="separate Tesseract"):
        ocr_support.configure_tesseract(fake)


def test_discovered_ocr_executable_is_configured(monkeypatch):
    monkeypatch.setattr(ocr_support, "find_tesseract", lambda: "/opt/bin/tesseract")
    fake = SimpleNamespace(pytesseract=SimpleNamespace(tesseract_cmd="unused"),
                           get_tesseract_version=lambda: "5.0")
    assert ocr_support.configure_tesseract(fake) == "/opt/bin/tesseract"
    assert fake.pytesseract.tesseract_cmd == "/opt/bin/tesseract"


def test_unusable_ocr_executable_is_actionable(monkeypatch):
    monkeypatch.setattr(ocr_support, "find_tesseract", lambda: "tesseract")
    def broken_engine():
        raise OSError("not executable")
    fake = SimpleNamespace(pytesseract=SimpleNamespace(tesseract_cmd="unused"),
                           get_tesseract_version=broken_engine)
    with pytest.raises(RuntimeError, match="could not be started"):
        ocr_support.configure_tesseract(fake)
