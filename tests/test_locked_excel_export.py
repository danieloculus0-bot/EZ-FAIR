"""A locked Excel FAI report must not stop new output generation."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from openpyxl import Workbook, load_workbook

from default_fai_template import create_neutral_fai_template
from fai_template_writer import (
    _save_workbook_with_locked_fallback,
    fill_fai_template,
    fill_fai_template_pages,
)


def simulate_excel_lock(monkeypatch, locked_name: Path):
    """Imitate Windows PermissionError when replacing an open workbook."""
    replace_original = os.replace

    def win_replace(source, destination):
        if Path(destination) == locked_name:
            raise PermissionError(13, "Permission denied", str(destination))
        return replace_original(source, destination)

    monkeypatch.setattr(os, "replace", win_replace)


def test_locked_form_creates_one_new_file_without_touching_open_report(monkeypatch, tmp_path):
    master = create_neutral_fai_template(tmp_path / "master.xlsx")
    wanted = tmp_path / "example_FAI.xlsx"
    wanted.write_bytes(b"previous operator report must stay unchanged")
    simulate_excel_lock(monkeypatch, wanted)
    items = [
        SimpleNamespace(
            char_number=i, nominal=float(i), lsl=i - .01, usl=i + .01,
            reference_location="P1-R1C1", raw_text=f"{i}.000",
            type="LINEAR", tooling="CALIPER", metadata={
                "tolerance_status": "explicit"
            }
        )
        for i in range(1, 28)
    ]
    outputs = fill_fai_template_pages(master, items, wanted)
    assert outputs == [tmp_path / "example_FAI_02.xlsx"]
    assert wanted.read_bytes() == b"previous operator report must stay unchanged"
    assert len(list(tmp_path.glob("example_FAI_*.xlsx"))) == 1
    assert not list(tmp_path.glob(".example_FAI_*"))
    book = load_workbook(outputs[0], data_only=False)
    assert book.sheetnames[:2] == ["FAI FORM", "FAI FORM 2"]
    assert book["FAI FORM"]["D24"].value == 1.0
    assert book["FAI FORM 2"]["D24"].value == 26.0
    book.close()


def test_locked_simple_export_chooses_next_unused_filename(monkeypatch, tmp_path):
    master = create_neutral_fai_template(tmp_path / "master.xlsx")
    wanted = tmp_path / "example_FAI.xlsx"
    wanted.write_bytes(b"protected")
    (tmp_path / "example_FAI_02.xlsx").write_bytes(b"prior run")
    simulate_excel_lock(monkeypatch, wanted)
    saved = fill_fai_template(
        master,
        [SimpleNamespace(
            char_number=1, nominal=17.0, lsl=16.99, usl=17.01,
            raw_text="17.000", type="LINEAR", tooling="CALIPER",
            metadata={"tolerance_status": "explicit"}
        )],
        wanted
    )
    assert saved.name == "example_FAI_03.xlsx"
    assert wanted.read_bytes() == b"protected"
    assert (tmp_path / "example_FAI_02.xlsx").read_bytes() == b"prior run"
    assert load_workbook(saved, data_only=False)["FAI FORM"]["D24"].value == 17


def test_permission_error_on_new_file_is_not_mislabeled_as_excel_lock(monkeypatch, tmp_path):
    book = Workbook()
    denied = tmp_path / "no-write.xlsx"
    simulate_excel_lock(monkeypatch, denied)
    with pytest.raises(PermissionError):
        _save_workbook_with_locked_fallback(book, denied)
    assert not list(tmp_path.glob(".no-write_*"))
    assert not denied.exists()
