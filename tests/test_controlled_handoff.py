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
