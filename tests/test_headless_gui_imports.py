"""Both GUI modules must import headlessly; runner and GUI share the parser."""
import extractor_active
import ez_fair
import ez_fair_enhancements
import local_test_runner
import polished_gui


def test_both_gui_entrypoints_import_headlessly():
    assert callable(ez_fair.launch_gui)
    assert callable(polished_gui.main)
    assert hasattr(ez_fair_enhancements, "ExtractionSettings")


def test_runner_and_workbench_use_explicit_extractor():
    assert polished_gui.extract_pdf_dimensions is extractor_active.extract_pdf_dimensions
    assert local_test_runner.extract_pdf_dimensions is extractor_active.extract_pdf_dimensions
    assert extractor_active.EXTRACTOR_VARIANT == "fraction_weld_precision"
