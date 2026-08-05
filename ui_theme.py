"""Configurable dark industrial theme for EZ FAIR."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import ttk

THEME_PATH = Path.home() / ".ez_fair_theme.json"

PRESETS = {
    "VenvWin Blue": "#2388FF",
    "Machine Green": "#24C66B",
    "Safety Orange": "#F28C28",
    "Inspection Yellow": "#E5B80B",
    "Steel Gray": "#7B8794",
}


@dataclass
class ThemeSettings:
    preset: str = "VenvWin Blue"
    accent: str = "#2388FF"
    primary_button: str = "#2388FF"
    danger: str = "#D44747"
    warning: str = "#E5B80B"
    success: str = "#24C66B"
    balloon: str = "#FF3B30"

    @classmethod
    def load(cls) -> "ThemeSettings":
        if not THEME_PATH.exists():
            return cls()
        try:
            data = json.loads(THEME_PATH.read_text(encoding="utf-8"))
            allowed = cls.__dataclass_fields__.keys()
            return cls(**{key: value for key, value in data.items() if key in allowed})
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self) -> None:
        THEME_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def apply_preset(self, name: str) -> None:
        if name not in PRESETS:
            raise ValueError(f"Unknown theme preset: {name}")
        self.preset = name
        self.accent = PRESETS[name]
        self.primary_button = PRESETS[name]


def apply_theme(root, settings: ThemeSettings) -> None:
    """Apply the sharp dark EZ FAIR theme to a Tk root."""
    root.configure(bg="#111417")
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", background="#191D21", foreground="#E8EDF2", fieldbackground="#111417", borderwidth=1)
    style.configure("TFrame", background="#191D21")
    style.configure("TLabel", background="#191D21", foreground="#E8EDF2")
    style.configure("TNotebook", background="#111417", borderwidth=0)
    style.configure("TNotebook.Tab", background="#252B31", foreground="#C8D0D8", padding=(12, 6), borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", settings.accent)], foreground=[("selected", "#FFFFFF")])
    style.configure("TButton", background="#2A3036", foreground="#FFFFFF", padding=(10, 6), borderwidth=1, relief="flat")
    style.map("TButton", background=[("active", "#353D45"), ("pressed", settings.accent)])
    style.configure("Primary.TButton", background=settings.primary_button, foreground="#FFFFFF")
    style.map("Primary.TButton", background=[("active", settings.accent), ("pressed", "#1266C4")])
    style.configure("Danger.TButton", background=settings.danger, foreground="#FFFFFF")
    style.configure("TEntry", fieldbackground="#0F1215", foreground="#FFFFFF", insertcolor="#FFFFFF", bordercolor="#434B54")
    style.configure("TCombobox", fieldbackground="#0F1215", foreground="#FFFFFF", arrowcolor="#FFFFFF")
    style.configure("Treeview", background="#14181C", fieldbackground="#14181C", foreground="#E8EDF2", rowheight=24, bordercolor="#343B43")
    style.configure("Treeview.Heading", background="#252B31", foreground="#FFFFFF", relief="flat")
    style.map("Treeview", background=[("selected", settings.accent)], foreground=[("selected", "#FFFFFF")])
    style.configure("Status.TLabel", background="#0D1013", foreground="#AEB8C2", padding=(8, 4))
