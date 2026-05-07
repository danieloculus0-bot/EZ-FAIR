from __future__ import annotations

import argparse
from pathlib import Path

import fitz
from openpyxl import Workbook


def make_demo_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    rows = [
        (72, 72, 'DEMO DRAWING'),
        (72, 120, '16.00'),
        (140, 120, '76.00 deg'),
        (220, 120, 'DIA .810'),
        (72, 170, '4.69 +.13 -.03'),
        (72, 220, 'WELD SIZE .25'),
        (72, 270, '13.53'),
        (72, 420, 'DIMENSIONS ARE IN INCHES'),
        (72, 440, 'TWO PLACE DECIMAL 0.02'),
        (72, 460, 'THREE PLACE DECIMAL 0.005'),
        (72, 480, 'ANGULAR 2'),
        (72, 500, 'ALL METAL PARTS TO BE COATED'),
    ]
    for x, y, text in rows:
        page.insert_text((x, y), text, fontsize=10)
    doc.save(path)
    doc.close()
    return path


def make_demo_template(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = 'FAI'
    headers = [
        'Char Number', 'Reference Location', 'Requirement LSL',
        'Requirement Nominal', 'Requirement USL', 'Type',
        'EZ Fabricating Actual', 'In Spec', 'Tooling Used', 'Comments',
    ]
    for col, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col).value = header
    wb.save(path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description='Create synthetic EZ-FAIR demo inputs.')
    parser.add_argument('--output-dir', default='demo_inputs')
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    pdf = make_demo_pdf(output_dir / 'demo_drawing.pdf')
    template = make_demo_template(output_dir / 'demo_template.xlsx')
    print(f'Demo PDF: {pdf}')
    print(f'Demo template: {template}')


if __name__ == '__main__':
    main()
