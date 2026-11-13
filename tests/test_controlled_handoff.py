"""Cross-project handoff uses the actual EZ-FAIR PDF extraction engine."""
import hashlib
import unittest
import fitz
from controlled_handoff import inspect_released_pdf

class ReleasedDrawingTests(unittest.TestCase):
    def sample(self):
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 75), "WIDTH 20.00", fontsize=14)
        page.insert_text((50, 120), "HEIGHT 11.500", fontsize=14)
        pdf = doc.tobytes()
        doc.close()
        source = {"schema": "forgevault.released_drawing.v1",
            "record_id": "FV-42", "file_version_id": "version-42",
            "release_package_number": "RPK-42", "customer_part_number": "B-42",
            "customer_revision": "B", "internal_revision": "02", "version_number": 1,
            "filename": "drawing.pdf", "lifecycle": "Released",
            "sha256": hashlib.sha256(pdf).hexdigest(), "byte_size": len(pdf)}
        return source, pdf

    def test_real_pdf_extraction_preserves_source(self):
        manifest, pdf = self.sample()
        result = inspect_released_pdf(manifest, pdf)
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["source_drawing"]["customer_revision"], "B")
        self.assertEqual(result["source_drawing"]["sha256"], manifest["sha256"])
        self.assertGreater(result["characteristic_count"], 0)
        self.assertTrue(all("actual" not in row for row in result["characteristics"]))

    def test_fabrication_evidence_export_reuses_reviewed_characteristics(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        manifest, pdf = self.sample()
        def characteristic(kind, text, page):
            return SimpleNamespace(type=kind, raw_text=text,
                metadata={"source": text}, page_index=page,
                reference_location="synthetic page annotation",
                char_number=1, nominal=0, lsl=0, usl=0,
                tooling="VISUAL", comments="")
        observed = [characteristic("WELD", "3/16 FILLET WELD", 0),
                    characteristic("LINEAR", "BEND R.125 90 DEG", 0)]
        with patch("controlled_handoff.extract_pdf_dimensions", return_value=observed):
            result = inspect_released_pdf(manifest, pdf)
        self.assertEqual([f["process"] for f in result["fabrication_features"]],
                         ["welding", "bending"])
        self.assertTrue(all(f["schema"] == "axiom.fabrication_feature.v1"
                            and f["needs_review"] for f in result["fabrication_features"]))
        self.assertTrue(all(f["source"] == "drawing.pdf" for f in result["fabrication_features"]))

    def test_tampering_and_unreleased_rejected(self):
        manifest, pdf = self.sample()
        with self.assertRaisesRegex(ValueError, "digest"):
            inspect_released_pdf(manifest, pdf + b"tampered")
        with self.assertRaisesRegex(ValueError, "not released"):
            inspect_released_pdf(dict(manifest, lifecycle="In Work"), pdf)
        with self.assertRaisesRegex(ValueError, "missing controlled"):
            inspect_released_pdf(dict(manifest, file_version_id=""), pdf)

if __name__ == "__main__":
    unittest.main()
