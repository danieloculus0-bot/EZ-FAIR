"""Synthetic regression: source-tolerance provenance survives empty metadata."""
import unittest
from types import SimpleNamespace

from hybrid_extraction import _apply_source_tolerances


class ToleranceProvenanceTests(unittest.TestCase):
    def test_empty_metadata_records_title_block_source(self):
        item = SimpleNamespace(metadata={}, raw_text="12.34", type="LINEAR", nominal=12.34, lsl=None, usl=None)
        _apply_source_tolerances([item], {"two_place": 0.02})
        self.assertEqual(item.metadata["tolerance_source"], "drawing_title_block")
        self.assertEqual(item.metadata["tolerance_rule"], "two_place")
        self.assertEqual(item.metadata["tolerance_value"], 0.02)
        self.assertAlmostEqual(item.lsl, 12.32)
        self.assertAlmostEqual(item.usl, 12.36)

    def test_empty_metadata_records_unknown_without_inventing_limits(self):
        item = SimpleNamespace(metadata={}, raw_text="12.34", type="LINEAR", nominal=12.34, lsl=12, usl=13)
        _apply_source_tolerances([item], {})
        self.assertEqual(item.metadata["tolerance_source"], "unknown")
        self.assertIsNone(item.lsl)
        self.assertIsNone(item.usl)

    def test_explicit_limits_and_provenance_are_preserved(self):
        item = SimpleNamespace(metadata={"tolerance_status": "explicit"}, raw_text="12.34", type="LINEAR", nominal=12.34, lsl=12.3, usl=12.4)
        _apply_source_tolerances([item], {"two_place": 0.02})
        self.assertEqual(item.metadata["tolerance_source"], "dimension_explicit")
        self.assertEqual((item.lsl, item.usl), (12.3, 12.4))

    def test_missing_metadata_is_initialized(self):
        item = SimpleNamespace(raw_text="12.34", type="LINEAR", nominal=12.34, lsl=None, usl=None)
        _apply_source_tolerances([item], {})
        self.assertEqual(item.metadata["tolerance_source"], "unknown")


if __name__ == "__main__":
    unittest.main()
