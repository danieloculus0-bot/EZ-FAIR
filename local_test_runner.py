"""Local-only real drawing test runner for EZ FAI Builder.

This helper is intentionally filesystem-only: it reads a PDF drawing and Excel
FAI template from local disk and writes generated artifacts to a local output
folder. It does not use cloud services, pandas, or a database.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Iterable

from ez_fai_builder import (
    Characteristic,
    SkippedCandidate,
    TITLE_BLOCK_DEFAULTS,
    TOLERANCE_PATTERN,
    add_pdf_balloons,
    extract_pdf_dimensions,
    get_last_skipped_candidates,
    write_debug_report,
)
from fai_template_writer import fill_fai_template, template_row_capacity

LOCAL_INPUTS_DIR = Path("local_inputs")
LOCAL_OUTPUTS_DIR = Path("local_outputs")
SUMMARY_FILENAME = "EXTRACTION_SUMMARY.txt"
DEBUG_REPORT_FILENAME = "EZ_FAI_DEBUG_REPORT.txt"


def _has_explicit_tolerance(characteristic: Characteristic) -> bool:
    context = " ".join(
        str(characteristic.metadata.get(key, ""))
        for key in ("source", "nearby")
    )
    return bool(TOLERANCE_PATTERN.search(context))


def _likely_false_positives(characteristics: Iterable[Characteristic]) -> list[Characteristic]:
    flagged: list[Characteristic] = []
    noise_words = ("DATE", "DWG", "DRAWING", "REV", "SHEET", "PAGE", "PHONE", "FAX", "SCALE")
    for characteristic in characteristics:
        context = " ".join(
            str(characteristic.metadata.get(key, ""))
            for key in ("source", "nearby")
        ).upper()
        if any(word in context for word in noise_words):
            flagged.append(characteristic)
        elif characteristic.type == "LINEAR" and abs(characteristic.nominal) > 100:
            flagged.append(characteristic)
    return flagged


def _likely_duplicates(characteristics: Iterable[Characteristic]) -> list[Characteristic]:
    seen: dict[tuple[str, float, str], Characteristic] = {}
    duplicates: list[Characteristic] = []
    for characteristic in characteristics:
        key = (characteristic.type, round(characteristic.nominal, 4), characteristic.reference_location)
        if key in seen:
            duplicates.append(characteristic)
        else:
            seen[key] = characteristic
    return duplicates


def write_extraction_summary(
    output_path: str | Path,
    characteristics: list[Characteristic],
    skipped_candidates: list[SkippedCandidate] | None = None,
    template_capacity: int | None = None,
) -> Path:
    """Write a concise extraction and skipped-candidate summary."""
    output_path = Path(output_path)
    skipped_candidates = skipped_candidates if skipped_candidates is not None else get_last_skipped_candidates()
    type_counts = Counter(characteristic.type for characteristic in characteristics)
    explicit_tolerance = [c for c in characteristics if _has_explicit_tolerance(c)]
    guessed_tolerance = [c for c in characteristics if not _has_explicit_tolerance(c)]
    likely_false_positives = _likely_false_positives(characteristics)
    likely_duplicates = _likely_duplicates(characteristics)
    skipped_by_reason = Counter(skipped.reason for skipped in skipped_candidates)

    lines = [
        "EZ FAI Extraction Summary",
        "=========================",
        f"Total extracted characteristics: {len(characteristics)}",
    ]
    if template_capacity is not None:
        lines.append(f"Template row capacity: {template_capacity}")
        if len(characteristics) > template_capacity:
            lines.append(f"WARNING: Only the first {template_capacity} characteristics fit on this exact form. Extra characteristics need a continuation sheet or manual handling.")
    lines.extend([
        "",
        "Count by type:",
        f"  LINEAR: {type_counts.get('LINEAR', 0)}",
        f"  Ø: {type_counts.get('Ø', 0)}",
        f"  °: {type_counts.get('°', 0)}",
        f"  WELD: {type_counts.get('WELD', 0)}",
        f"  other: {sum(count for dim_type, count in type_counts.items() if dim_type not in {'LINEAR', 'Ø', '°', 'WELD'})}",
        "",
        f"Count of skipped candidates: {len(skipped_candidates)}",
        "Skipped-candidate summary:",
    ])
    if skipped_by_reason:
        for reason, count in skipped_by_reason.most_common():
            lines.append(f"  {reason}: {count}")
    else:
        lines.append("  (none)")

    def add_characteristic_list(title: str, items: list[Characteristic]) -> None:
        lines.extend(["", f"{title}: {len(items)}"])
        if not items:
            lines.append("  (none)")
            return
        for item in items:
            lines.append(
                f"  Char {item.char_number}: {item.raw_text} | type={item.type} | "
                f"nominal={item.nominal} | LSL={item.lsl} | USL={item.usl} | {item.reference_location}"
            )

    add_characteristic_list("Likely false positives", likely_false_positives)
    add_characteristic_list("Likely duplicate dimensions", likely_duplicates)
    add_characteristic_list("Dimensions with missing or guessed tolerance", guessed_tolerance)
    add_characteristic_list("Dimensions with explicit tolerance", explicit_tolerance)

    lines.extend(
        [
            "",
            "Title block tolerance defaults used:",
            f"  two place decimal: ±{TITLE_BLOCK_DEFAULTS['two_place']}",
            f"  three place decimal: ±{TITLE_BLOCK_DEFAULTS['three_place']}",
            f"  angular: ±{TITLE_BLOCK_DEFAULTS['angular']}",
            "",
            "Review note: guessed tolerances, likely false positives, and likely duplicates should be checked before using the FAI.",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def run_local_test(pdf_path: str | Path, template_path: str | Path, output_dir: str | Path = LOCAL_OUTPUTS_DIR) -> dict[str, Path | int]:
    """Run extraction and write all local test artifacts to output_dir."""
    pdf_path = Path(pdf_path)
    template_path = Path(template_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    characteristics = extract_pdf_dimensions(pdf_path)
    for characteristic in characteristics:
        characteristic.metadata["drawing_name"] = pdf_path.stem

    capacity = template_row_capacity(template_path)

    ballooned_pdf = output_dir / f"{pdf_path.stem}_BALLOONED.pdf"
    suffix = ".xlsm" if template_path.suffix.lower() == ".xlsm" else ".xlsx"
    fai_excel = output_dir / f"{pdf_path.stem}_FAI{suffix}"
    debug_report = output_dir / DEBUG_REPORT_FILENAME
    extraction_summary = output_dir / SUMMARY_FILENAME

    add_pdf_balloons(pdf_path, characteristics, ballooned_pdf)
    fill_fai_template(template_path, characteristics, fai_excel)
    write_debug_report(pdf_path, template_path, characteristics, debug_report)
    write_extraction_summary(extraction_summary, characteristics, get_last_skipped_candidates(), capacity)

    return {
        "ballooned_pdf": ballooned_pdf,
        "fai_excel": fai_excel,
        "debug_report": debug_report,
        "extraction_summary": extraction_summary,
        "characteristic_count": len(characteristics),
        "skipped_count": len(get_last_skipped_candidates()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local-only EZ FAI Builder sample test.")
    parser.add_argument("--pdf", required=True, help="Path to the local PDF drawing.")
    parser.add_argument("--template", required=True, help="Path to the local Excel FAI template (.xlsx or .xlsm).")
    parser.add_argument("--output-dir", default=str(LOCAL_OUTPUTS_DIR), help="Directory where generated artifacts should be written.")
    args = parser.parse_args()

    outputs = run_local_test(args.pdf, args.template, args.output_dir)
    print("EZ FAI local test complete")
    print(f"Extracted characteristics: {outputs['characteristic_count']}")
    print(f"Skipped candidates: {outputs['skipped_count']}")
    print(f"Ballooned PDF: {outputs['ballooned_pdf']}")
    print(f"FAI Excel: {outputs['fai_excel']}")
    print(f"Debug report: {outputs['debug_report']}")
    print(f"Extraction summary: {outputs['extraction_summary']}")


if __name__ == "__main__":
    main()
