from pathlib import Path

import fitz

import ez_fai_builder as base
import pyinstaller_runtime_hook  # noqa: F401 - installs packaged compatibility aliases


def test_runtime_exposes_balloon_generator_and_writes_pdf(tmp_path: Path) -> None:
    source = tmp_path / "drawing.pdf"
    output = tmp_path / "drawing_BALLOONED.pdf"

    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((100, 100), ".375")
    document.save(source)
    document.close()

    characteristic = base.Characteristic(
        char_number=1,
        reference_location="P1-R1C1",
        nominal=0.375,
        lsl=0.370,
        usl=0.380,
        type="LINEAR",
        page_index=0,
        rect=(95.0, 85.0, 135.0, 105.0),
        raw_text=".375",
        tooling="CALIPER",
    )

    assert callable(base.generate_ballooned_pdf)
    result = base.generate_ballooned_pdf(source, [characteristic], output)
    assert result == output
    assert output.exists()
    with fitz.open(output) as ballooned:
        assert ballooned.page_count == 1
