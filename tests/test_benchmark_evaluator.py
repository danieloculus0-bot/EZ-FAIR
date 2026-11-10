"""Synthetic proof that the benchmark reports actual errors without hidden data."""
import json
from types import SimpleNamespace

import pymupdf as fitz

from tools.evaluate_extraction import evaluate_manifest


def test_benchmark_counts_true_false_positives_and_false_negatives(tmp_path):
    pdf_path = tmp_path / "synthetic.pdf"
    with fitz.open() as doc:
        doc.new_page(width=300, height=300)
        doc.save(pdf_path)
    manifest = tmp_path / "labels.json"
    manifest.write_text(json.dumps({"cases": [{
        "name": "synthetic_only", "pdf": "synthetic.pdf",
        "expected": [{"page": 1, "type": "LINEAR", "nominal": 1.0},
                     {"page": 1, "type": "LINEAR", "nominal": 3.0}]
    }]}), encoding="utf-8")

    def fake_extractor(_):
        return [
            SimpleNamespace(page_index=0, type="LINEAR", nominal=1.0,
                            rect=(10, 10, 40, 20), raw_text="1.0", metadata={}),
            SimpleNamespace(page_index=0, type="LINEAR", nominal=2.0,
                            rect=(50, 10, 70, 20), raw_text="2.0", metadata={}),
        ]
    report = evaluate_manifest(manifest, extractor=fake_extractor)
    assert (report["tp"], report["fp"], report["fn"]) == (1, 1, 1)
    assert report["precision"] == 0.5
    assert report["recall"] == 0.5
    assert report["source_rectangle_traceability"] == 1.0


def test_benchmark_rejects_empty_labels(tmp_path):
    manifest = tmp_path / "labels.json"
    manifest.write_text('{"cases":[]}', encoding="utf-8")
    try:
        evaluate_manifest(manifest)
    except ValueError as exc:
        assert "nonempty" in str(exc)
    else:
        raise AssertionError("Empty benchmark must not silently pass")


def test_partial_labels_do_not_invent_false_positive_rate(tmp_path):
    pdf_path = tmp_path / "synthetic.pdf"
    with fitz.open() as pdf:
        pdf.new_page(width=300, height=300)
        pdf.save(pdf_path)
    manifest = tmp_path / "partial.json"
    manifest.write_text(json.dumps({"cases": [{
        "pdf": "synthetic.pdf", "fully_labeled": False,
        "expected": [{"page": 1, "type": "LINEAR", "nominal": 1.0}]
    }]}), encoding="utf-8")
    def fake(_):
        return [SimpleNamespace(page_index=0, type="LINEAR", nominal=v,
                                rect=(10, 10, 40, 20), raw_text=str(v), metadata={})
                for v in (1.0, 2.0)]
    report = evaluate_manifest(manifest, extractor=fake)
    assert report["precision"] is None
    assert report["recall"] is None
    assert report["fp"] is None
    assert report["labeled_example_match_rate"] == 1.0
