"""Static theme contract can be checked without a running Tk display."""
import polished_gui as gui

def test_lime_and_charcoal_tokens():
    assert gui.APP_BG == "#0F1113"
    assert gui.PANEL_BG == "#1A1D20"
    assert gui.CARD_BG == "#22282A"
    assert gui.TEXT == "#E6EAE7"
    assert gui.ACCENT == "#79DE4B"

def test_theme_keeps_desktop_review_and_export_actions():
    assert callable(gui.EzFairApp.extract_review)
    assert callable(gui.EzFairApp.generate_outputs)
