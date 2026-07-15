"""Enhanced EZ FAIR desktop launcher."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import ez_fai_builder as base
from ez_fair_enhancements import ExtractionSettings, extract_pdf_dimensions_enhanced


class EnhancedEZFAIBuilderApp(base.EZFAIBuilderApp):
    def __init__(self):
        self.settings = ExtractionSettings.load()
        super().__init__()
        self.title("EZ FAIR")

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        main_tab = ttk.Frame(notebook)
        settings_tab = ttk.Frame(notebook, padding=16)
        notebook.add(main_tab, text="FAI Builder")
        notebook.add(settings_tab, text="Settings")

        top = ttk.Frame(main_tab, padding=12)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Select PDF", command=self.select_pdf).grid(row=0, column=0, padx=4, pady=4)
        self.pdf_label = ttk.Label(top, text="No PDF selected")
        self.pdf_label.grid(row=0, column=1, sticky="w", padx=4)
        ttk.Button(top, text="Select Excel Template", command=self.select_template).grid(row=1, column=0, padx=4, pady=4)
        self.template_label = ttk.Label(top, text="No Excel template selected")
        self.template_label.grid(row=1, column=1, sticky="w", padx=4)
        ttk.Button(top, text="Extract Dimensions", command=self.extract_dimensions).grid(row=2, column=0, padx=4, pady=8)
        ttk.Button(top, text="Generate Ballooned PDF + FAI Excel", command=self.generate_outputs).grid(row=2, column=1, sticky="w", padx=4, pady=8)
        ttk.Button(top, text="Delete Selected Review Rows", command=self.delete_rows).grid(row=2, column=2, padx=4, pady=8)

        ttk.Label(main_tab, text="Review Table: double-click editable fields before export.", padding=(12, 0)).pack(fill=tk.X)
        self.review_table = base.ReviewTable(main_tab)
        self.review_table.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(main_tab, textvariable=self.status, relief=tk.SUNKEN, anchor="w").pack(fill=tk.X, side=tk.BOTTOM)

        self.two_place_var = tk.StringVar(value=str(self.settings.two_place))
        self.three_place_var = tk.StringVar(value=str(self.settings.three_place))
        self.angular_var = tk.StringVar(value=str(self.settings.angular))
        self.auto_title_var = tk.BooleanVar(value=self.settings.auto_detect_title_block)
        self.ocr_var = tk.BooleanVar(value=self.settings.enable_ocr_fallback)
        self.ocr_dpi_var = tk.StringVar(value=str(self.settings.ocr_dpi))

        fields = [
            ("Two-place decimal tolerance (±)", self.two_place_var),
            ("Three-place decimal tolerance (±)", self.three_place_var),
            ("Angular tolerance (± degrees)", self.angular_var),
            ("OCR render DPI", self.ocr_dpi_var),
        ]
        for row, (label, variable) in enumerate(fields):
            ttk.Label(settings_tab, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=6)
            ttk.Entry(settings_tab, textvariable=variable, width=16).grid(row=row, column=1, sticky="w", padx=6, pady=6)
        ttk.Checkbutton(settings_tab, text="Auto-detect tolerance box in bottom-right title block", variable=self.auto_title_var).grid(row=4, column=0, columnspan=2, sticky="w", padx=6, pady=8)
        ttk.Checkbutton(settings_tab, text="Use offline OCR fallback when vector extraction returns zero dimensions", variable=self.ocr_var).grid(row=5, column=0, columnspan=2, sticky="w", padx=6, pady=8)
        ttk.Button(settings_tab, text="Save Settings", command=self.save_settings).grid(row=6, column=0, sticky="w", padx=6, pady=12)
        ttk.Label(settings_tab, text="OCR is fully local. Tesseract must be installed on the Windows machine.", wraplength=650).grid(row=7, column=0, columnspan=2, sticky="w", padx=6, pady=6)

    def save_settings(self) -> None:
        try:
            self.settings.two_place = float(self.two_place_var.get())
            self.settings.three_place = float(self.three_place_var.get())
            self.settings.angular = float(self.angular_var.get())
            self.settings.ocr_dpi = int(self.ocr_dpi_var.get())
            if self.settings.ocr_dpi < 150 or self.settings.ocr_dpi > 600:
                raise ValueError("OCR DPI must be between 150 and 600.")
            self.settings.auto_detect_title_block = self.auto_title_var.get()
            self.settings.enable_ocr_fallback = self.ocr_var.get()
            self.settings.save()
            messagebox.showinfo("Settings saved", "EZ FAIR extraction settings were saved.")
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc))

    def extract_dimensions(self) -> None:
        if not self.pdf_path:
            messagebox.showwarning("Missing PDF", "Select a PDF blueprint first.")
            return
        try:
            self.save_settings_silent()
            self.status.set("Extracting vector text, title block, OCR fallback, and GD&T...")
            self.update_idletasks()
            self.characteristics = extract_pdf_dimensions_enhanced(self.pdf_path, self.settings)
            for characteristic in self.characteristics:
                characteristic.metadata["drawing_name"] = self.pdf_path.stem
            self.review_table.load(self.characteristics)
            methods = sorted({str(item.metadata.get("extraction", "VECTOR")) for item in self.characteristics})
            self.status.set(f"Extracted {len(self.characteristics)} characteristics using {', '.join(methods) or 'VECTOR'}. Review before export.")
        except Exception as exc:
            self.status.set("Extraction failed")
            messagebox.showerror("Extraction failed", str(exc))

    def save_settings_silent(self) -> None:
        self.settings.two_place = float(self.two_place_var.get())
        self.settings.three_place = float(self.three_place_var.get())
        self.settings.angular = float(self.angular_var.get())
        self.settings.ocr_dpi = int(self.ocr_dpi_var.get())
        self.settings.auto_detect_title_block = self.auto_title_var.get()
        self.settings.enable_ocr_fallback = self.ocr_var.get()
        self.settings.save()


def launch_gui() -> None:
    EnhancedEZFAIBuilderApp().mainloop()


if __name__ == "__main__":
    launch_gui()
