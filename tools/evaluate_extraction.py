"""Local-only benchmark of manually labeled, cleared/synthetic PDF drawings.

Usage: python tools/evaluate_extraction.py --manifest docs/examples/demo_benchmark.json
No drawings or results are uploaded by this tool. The benchmark must include
human-labeled expected characteristics; the synthetic demo is not a validity claim.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Callable

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from extractor_active import extract_pdf_dimensions


def _matches(actual, expected: dict) -> bool:
    if actual.page_index + 1 != int(expected["page"]):
        return False
    if str(actual.type).casefold() != str(expected["type"]).casefold():
        return False
    left = actual.nominal
    right = expected["nominal"]
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if not math.isclose(left, right, rel_tol=0, abs_tol=float(expected.get("abs_tol", 1e-5))):
            return False
    elif str(left).strip().casefold() != str(right).strip().casefold():
        return False
    needle = str(expected.get("source_contains", "")).strip().casefold()
    if needle:
        context = " ".join((str(actual.raw_text), str(actual.metadata.get("source", "")))).casefold()
        if needle not in context:
            return False
    return True


def _source_traceable(actual, pages: list[tuple[float, float]]) -> bool:
    """Check source page, finite drawing rectangle and a nonempty provenance string."""
    index = actual.page_index
    if not isinstance(index, int) or not 0 <= index < len(pages):
        return False
    try:
        x0, y0, x1, y1 = (float(v) for v in actual.rect)
    except (TypeError, ValueError):
        return False
    width, height = pages[index]
    valid_rect = all(math.isfinite(n) for n in (x0, y0, x1, y1))
    valid_rect &= 0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height
    provenance = str(actual.raw_text or actual.metadata.get("source") or "").strip()
    return bool(valid_rect and provenance)


def evaluate_manifest(manifest_path: Path, extractor: Callable = extract_pdf_dimensions) -> dict:
    manifest_path = Path(manifest_path).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Benchmark needs a nonempty cases list with labeled drawings.")
    aggregate = dict(tp=0, fp=0, fn=0, traceable=0, produced=0)
    results = []
    for case in cases:
        expected = case.get("expected", [])
        if not isinstance(expected, list) or not expected:
            raise ValueError("Each drawing needs human-labeled expected characteristics.")
        path = (manifest_path.parent / case["pdf"]).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Benchmark PDF missing: {path}")
        with fitz.open(path) as pdf:
            pages = [(page.rect.width, page.rect.height) for page in pdf]
        actual = list(extractor(path))
        used: set[int] = set()
        tp = 0
        for target in expected:
            match_index = next((i for i, item in enumerate(actual)
                                if i not in used and _matches(item, target)), None)
            if match_index is not None:
                used.add(match_index)
                tp += 1
        fp, fn = len(actual) - tp, len(expected) - tp
        traceable = sum(_source_traceable(item, pages) for item in actual)
        for name, count in (("tp", tp), ("fp", fp), ("fn", fn),
                            ("traceable", traceable), ("produced", len(actual))):
            aggregate[name] += count
        results.append(dict(case=case.get("name", path.name), expected=len(expected),
                            produced=len(actual), tp=tp, fp=fp, fn=fn,
                            traceable=traceable))
    precision = aggregate["tp"] / (aggregate["tp"] + aggregate["fp"]) if aggregate["produced"] else 0.0
    recall = aggregate["tp"] / (aggregate["tp"] + aggregate["fn"]) if (aggregate["tp"] + aggregate["fn"]) else 0.0
    traceability = aggregate["traceable"] / aggregate["produced"] if aggregate["produced"] else 0.0
    return dict(**aggregate, precision=round(precision, 4), recall=round(recall, 4),
                source_rectangle_traceability=round(traceability, 4), cases=results,
                warning="Human labels required. Source rectangle checks do not verify balloon placement.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-precision", type=float)
    parser.add_argument("--min-recall", type=float)
    parser.add_argument("--min-traceability", type=float)
    args = parser.parse_args()
    result = evaluate_manifest(args.manifest)
    body = json.dumps(result, indent=2, sort_keys=True)
    print(body)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body + "\n", encoding="utf-8")
    for name, key in (("min_precision", "precision"), ("min_recall", "recall"),
                      ("min_traceability", "source_rectangle_traceability")):
        minimum = getattr(args, name)
        if minimum is not None and result[key] < minimum:
            raise SystemExit(f"Benchmark FAILED: {key}={result[key]} < {minimum}")


if __name__ == "__main__":
    main()
