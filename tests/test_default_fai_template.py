"""Public-safe tests for a built-in original neutral Excel inspection form."""
from __future__ import annotations

from hashlib import sha256

from openpyxl import load_workbook
import pymupdf as fitz

from default_fai_template import (
    BUILTIN_NAME, builtin_template_path, create_neutral_fai_template,
    reset_default_template, resolve_default_template, save_default_template,
)
from fai_template_writer import fill_fai_template_pages, template_row_capacity
from ez_fai_builder import generate_outputs_for_files


def test_builtin_neutral_form_requires_no_uploaded_template(tmp_path, monkeypatch):
    monkeypatch.delenv("EZFAIR_TEMPLATE", raising=False)
    path = resolve_default_template(app_dir=tmp_path / "app", home=tmp_path / "user")
    assert path.exists()
    assert path.name == BUILTIN_NAME
    assert template_row_capacity(path) == 25
    wb = load_workbook(path, data_only=False)
    form = wb["FAI FORM"]
    assert form["A3"].value == "FIRST ARTICLE INSPECTION (FAI)"
    assert form["C24"].value == "=D24-0.02"
    assert form["E24"].value == "=D24+0.02"
    assert form["K24"].data_type == "f"
    assert form["J24"].value is None
    assert len(wb.sheetnames) == 4
    assert form.sheet_view.showGridLines is False
    assert form.page_setup.orientation == "landscape"
    wb.close()


def test_defaults_are_reusable_without_rewriting_source(tmp_path, monkeypatch):
    monkeypatch.delenv("EZFAIR_TEMPLATE", raising=False)
    app_dir, home = tmp_path / "app", tmp_path / "user"
    home.mkdir()
    path = resolve_default_template(app_dir, home)
    digest = sha256(path.read_bytes()).hexdigest()
    assert resolve_default_template(app_dir, home) == path
    assert sha256(path.read_bytes()).hexdigest() == digest


def test_private_local_master_can_be_default_without_publishing(tmp_path, monkeypatch):
    monkeypatch.delenv("EZFAIR_TEMPLATE", raising=False)
    app_dir, home = tmp_path / "app", tmp_path / "user"
    home.mkdir()
    master = app_dir / "local_templates" / "FAI_MASTER.xlsx"
    create_neutral_fai_template(master)
    assert resolve_default_template(app_dir, home) == master
    other = create_neutral_fai_template(tmp_path / "another.xlsx")
    assert save_default_template(other, home) == other
    assert resolve_default_template(app_dir, home) == other
    reset = reset_default_template(app_dir, home)
    assert reset.name == BUILTIN_NAME
    assert resolve_default_template(app_dir, home) == reset
    assert master.exists()


def test_builtin_master_paginates_and_keeps_formula_logic(tmp_path):
    from dataclasses import dataclass, field

    @dataclass
    class Candidate:
        char_number: int
        reference_location: str = "P1-R1C1"
        nominal: float = 3.5
        lsl: float = 3.48
        usl: float = 3.52
        type: str = "LINEAR"
        tooling: str = "CALIPER"
        comments: str = ""
        metadata: dict = field(default_factory=lambda: {"tolerance_status": "explicit"})

    source = builtin_template_path(tmp_path / "app")
    files = fill_fai_template_pages(
        source, [Candidate(char_number=n) for n in range(1, 28)], tmp_path / "demo_FAI.xlsx"
    )
    assert len(files) == 2
    first = load_workbook(files[0], data_only=False)["FAI FORM"]
    second = load_workbook(files[1], data_only=False)["FAI FORM"]
    assert first["A24"].value == 1
    assert first["A48"].value == 25
    assert second["A24"].value == 26
    assert second["A25"].value == 27
    assert second["C24"].data_type == "f"
    assert second["E24"].data_type == "f"
    assert second["K24"].data_type == "f"


def test_batch_mode_can_use_builtin_without_template_argument(tmp_path, monkeypatch):
    import ez_fai_builder

    built = builtin_template_path(tmp_path / "app")
    monkeypatch.setattr(ez_fai_builder, "resolve_default_template", lambda: built)
    pdf = tmp_path / "synthetic.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=792, height=612)
        page.insert_text((80, 100), "17.000", fontsize=12)
        doc.save(pdf)
    monkeypatch.setenv("EZFAIR_TEMPLATE", str(built))
    balloon, form, debug, chars = generate_outputs_for_files(pdf)
    assert balloon.exists()
    assert form.exists()
    assert debug.exists()
    assert any(c.nominal == 17.0 for c in chars)
    with load_workbook(form, data_only=False) as book:
        assert book["FAI FORM"]["K24"].data_type == "f"
