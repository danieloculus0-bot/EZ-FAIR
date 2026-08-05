"""Production Windows entry point for EZ FAIR."""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import ez_fai_builder as base
import ez_fair as app
from built_in_form_writer import write_inspection_workbook

BG = "#0B0B0B"
PANEL = "#141414"
PANEL_2 = "#222222"
PANEL_3 = "#2D2D2D"
TEXT = "#E6E6E6"
MUTED = "#8C8C8C"
ACCENT = "#F97316"
ACCENT_HOVER = "#FB923C"
DANGER = "#4A1F1F"
DANGER_HOVER = "#7A2D2D"


class EZFairProductionApp(app.EZFairApp):
    """Production-styled EZ FAIR application."""

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            ".",
            background=BG,
            foreground=TEXT,
            fieldbackground=PANEL,
            bordercolor=PANEL_3,
            darkcolor=PANEL,
            lightcolor=PANEL_3,
            troughcolor=PANEL,
            selectbackground=ACCENT,
            selectforeground=BG,
        )
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED)
        style.configure(
            "TButton",
            background=PANEL_3,
            foreground=TEXT,
            padding=(14, 8),
            borderwidth=1,
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("active", ACCENT), ("pressed", ACCENT_HOVER)],
            foreground=[("active", BG), ("pressed", BG)],
        )
        style.configure("Danger.TButton", background=DANGER, foreground=TEXT)
        style.map(
            "Danger.TButton",
            background=[("active", DANGER_HOVER), ("pressed", DANGER_HOVER)],
            foreground=[("active", TEXT), ("pressed", TEXT)],
        )
        style.configure(
            "TEntry",
            fieldbackground=PANEL_2,
            foreground=TEXT,
            insertcolor=ACCENT,
            bordercolor=PANEL_3,
            padding=6,
        )
        style.map("TEntry", bordercolor=[("focus", ACCENT)])
        style.configure("TCheckbutton", background=BG, foreground=TEXT)
        style.map("TCheckbutton", foreground=[("active", ACCENT)])
        style.configure("TLabelframe", background=BG, foreground=TEXT, bordercolor=PANEL_3)
        style.configure("TLabelframe.Label", background=BG, foreground=ACCENT)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 9), borderwidth=0)
        style.map(
            "TNotebook.Tab",
            background=[("selected", PANEL_2), ("active", PANEL_3)],
            foreground=[("selected", ACCENT), ("active", TEXT)],
        )
        style.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=TEXT,
            bordercolor=PANEL_3,
            rowheight=28,
        )
        style.configure("Treeview.Heading", background=PANEL_2, foreground=TEXT, relief="flat")
        style.map(
            "Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", BG)],
        )
        style.configure("TSeparator", background=PANEL_3)

    def _build_metadata_tab(self) -> None:
        container = ttk.Frame(self.metadata_tab, padding=18)
        container.pack(fill=tk.BOTH, expand=True)
        fields = [
            ("part_no", "Part No."), ("part_name", "Part Name"),
            ("drawing_no", "Drawing No."), ("revision", "Revision"),
            ("customer", "Customer"), ("material", "Material"),
            ("scale", "Scale"), ("units", "Units"),
            ("sheet", "Sheet"), ("drawing_date", "Drawing Date"),
            ("inspector", "Inspector"), ("item_no", "Item No."),
            ("po_no", "PO No."), ("order_no", "Order No."),
            ("reason_for_fai", "Reason for FAI"),
        ]
        for index, (key, label) in enumerate(fields):
            row, pair = divmod(index, 2)
            col = pair * 2
            ttk.Label(container, text=label).grid(row=row, column=col, sticky="w", padx=8, pady=6)
            var = tk.StringVar()
            self.metadata_vars[key] = var
            ttk.Entry(container, textvariable=var, width=38).grid(row=row, column=col + 1, sticky="ew", padx=8, pady=6)
        container.columnconfigure(1, weight=1)
        container.columnconfigure(3, weight=1)

    def _build_tooling_tab(self) -> None:
        top = ttk.Frame(self.tooling_tab, padding=12)
        top.pack(fill=tk.X)
        ttk.Button(top, text="ADD TOOL", command=self.add_tool).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="DELETE SELECTED", style="Danger.TButton", command=self.delete_tool).pack(side=tk.LEFT, padx=4)

        self.tool_tree = ttk.Treeview(
            self.tooling_tab,
            columns=("name", "id", "category", "cal", "active", "notes"),
            show="headings",
        )
        for key, label, width in [
            ("name", "Tool", 180),
            ("id", "Tool ID", 130),
            ("category", "Category", 130),
            ("cal", "Calibration Required", 150),
            ("active", "Active", 80),
            ("notes", "Notes", 360),
        ]:
            self.tool_tree.heading(key, text=label)
            self.tool_tree.column(key, width=width)
        self.tool_tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.tool_tree.bind("<Double-1>", self.edit_tool)
        self.refresh_tools()

    def generate_outputs(self) -> None:
        if not self.pdf_path:
            messagebox.showwarning("Missing Drawing", "Select a drawing PDF first.")
            return
        if not self.review_table.characteristics:
            messagebox.showwarning("No Characteristics", "Extract or manually add characteristics before export.")
            return

        folder = filedialog.askdirectory(title="Select packet output folder")
        if not folder:
            return

        try:
            self._sync_project_from_ui()
            output_dir = Path(folder)
            stem = self.project.metadata.drawing_no or self.pdf_path.stem
            ballooned = output_dir / f"{stem}_BALLOONED.pdf"
            workbook = output_dir / f"{stem}_INSPECTION_REPORT.xlsx"

            base.add_pdf_balloons(self.pdf_path, self.characteristics, ballooned)
            write_inspection_workbook(workbook, self.project.metadata, self.characteristics, self.form_config)

            self.project.status = "PACKET GENERATED"
            self.project_store.save(self.project)
            self.status.set(f"PACKET COMPLETE | {ballooned.name} | {workbook.name}")
            messagebox.showinfo("Packet Complete", f"Created:\n{ballooned}\n{workbook}")
        except Exception as exc:
            self.status.set("PACKET GENERATION FAILED")
            messagebox.showerror("Generation Failed", str(exc))


def launch_gui() -> None:
    EZFairProductionApp().mainloop()


if __name__ == "__main__":
    launch_gui()
