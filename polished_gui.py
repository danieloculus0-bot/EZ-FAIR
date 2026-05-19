from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

try:
    from extractor_fraction_weld_patch import (
        Characteristic,
        add_pdf_balloons,
        extract_pdf_dimensions,
        get_last_skipped_candidates,
        write_debug_report,
    )
except Exception:
    try:
        from extractor_precision_patch import (
            Characteristic,
            add_pdf_balloons,
            extract_pdf_dimensions,
            get_last_skipped_candidates,
            write_debug_report,
        )
    except Exception:
        from extractor_engine import (
            Characteristic,
            add_pdf_balloons,
            extract_pdf_dimensions,
            get_last_skipped_candidates,
            write_debug_report,
        )
from fai_template_writer import fill_fai_template, template_row_capacity
from local_test_runner import write_extraction_summary

APP_NAME = "EZ-FAIR"
APP_SUBTITLE = "First Article Inspection Builder"
APP_BG = "#101820"
PANEL_BG = "#17232f"
CARD_BG = "#1d2c3a"
TEXT = "#edf4ff"
MUTED = "#9fb2c8"
ACCENT = "#0b3a75"
ACCENT_2 = "#1f6fbc"


class EzFairApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} - {APP_SUBTITLE}")
        self.geometry("1240x780")
        self.minsize(1040, 660)
        self.configure(bg=APP_BG)

        self.pdf_path = tk.StringVar()
        self.template_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "local_outputs"))
        self.status_text = tk.StringVar(value="Ready. Pick a PDF and FAI template, then extract.")
        self.characteristics: list[Characteristic] = []
        self.generated_outputs: dict[str, Path] = {}
        self._busy = False

        self._apply_icon()
        self._configure_style()
        self._build_ui()

    def _apply_icon(self) -> None:
        candidates = [
            Path(__file__).resolve().parent / "assets" / "EZ-FAIR.ico",
            Path(__file__).resolve().parent / "bin" / "EZ-FAIR.ico",
            Path(__file__).resolve().parent / "EZ-FAIR.ico",
        ]
        for candidate in candidates:
            if candidate.exists():
                try:
                    self.iconbitmap(str(candidate))
                    return
                except Exception:
                    pass

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Root.TFrame", background=APP_BG)
        style.configure("Panel.TFrame", background=PANEL_BG)
        style.configure("Title.TLabel", background=APP_BG, foreground=TEXT, font=("Segoe UI", 24, "bold"))
        style.configure("Subtitle.TLabel", background=APP_BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("PanelTitle.TLabel", background=PANEL_BG, foreground=TEXT, font=("Segoe UI", 11, "bold"))
        style.configure("Body.TLabel", background=PANEL_BG, foreground=TEXT, font=("Segoe UI", 9))
        style.configure("Muted.TLabel", background=PANEL_BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=APP_BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 9), padding=(12, 7))
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"), padding=(14, 8))
        style.map("Accent.TButton", background=[("active", ACCENT_2), ("!disabled", ACCENT)], foreground=[("!disabled", "white")])
        style.configure("Treeview", background="#f8fbff", foreground="#18212b", fieldbackground="#f8fbff", rowheight=25, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), padding=(6, 6))
        style.map("Treeview", background=[("selected", ACCENT_2)], foreground=[("selected", "white")])

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="Root.TFrame", padding=18)
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root, style="Root.TFrame")
        header.pack(fill=tk.X)
        title_box = ttk.Frame(header, style="Root.TFrame")
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_box, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text=APP_SUBTITLE + "   •   local PDF in, ballooned PDF + editable FAI out", style="Subtitle.TLabel").pack(anchor="w", pady=(0, 8))

        ttk.Button(header, text="Open Output Folder", command=self.open_output_folder).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(header, text="Open App Folder", command=self.open_app_folder).pack(side=tk.RIGHT)

        setup = ttk.Frame(root, style="Panel.TFrame", padding=14)
        setup.pack(fill=tk.X, pady=(10, 12))
        ttk.Label(setup, text="Job Setup", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        setup.columnconfigure(1, weight=1)
        self._path_row(setup, 1, "PDF blueprint", self.pdf_path, self.pick_pdf)
        self._path_row(setup, 2, "FAI Excel template", self.template_path, self.pick_template)
        self._path_row(setup, 3, "Output folder", self.output_dir, self.pick_output_dir)

        actions = ttk.Frame(setup, style="Panel.TFrame")
        actions.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="Extract + Review", style="Accent.TButton", command=self.extract_review).pack(side=tk.LEFT)
        ttk.Button(actions, text="Generate Outputs", command=self.generate_outputs).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Delete Selected Rows", command=self.delete_selected).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Clear", command=self.clear_table).pack(side=tk.LEFT, padx=(8, 0))

        mid = ttk.Frame(root, style="Root.TFrame")
        mid.pack(fill=tk.BOTH, expand=True)

        table_panel = ttk.Frame(mid, style="Panel.TFrame", padding=10)
        table_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        top_line = ttk.Frame(table_panel, style="Panel.TFrame")
        top_line.pack(fill=tk.X)
        ttk.Label(top_line, text="Extracted Characteristics", style="PanelTitle.TLabel").pack(side=tk.LEFT)
        ttk.Label(top_line, text="Double-click a cell to edit before export", style="Muted.TLabel").pack(side=tk.RIGHT)

        columns = ("char", "page", "ref", "raw", "lsl", "nominal", "usl", "type", "tooling", "comments")
        self.tree = ttk.Treeview(table_panel, columns=columns, show="headings", selectmode="extended")
        headings = {"char": "#", "page": "Pg", "ref": "Location", "raw": "Raw", "lsl": "LSL", "nominal": "Nominal", "usl": "USL", "type": "Type", "tooling": "Tooling", "comments": "Comments"}
        widths = {"char": 44, "page": 44, "ref": 92, "raw": 130, "lsl": 82, "nominal": 82, "usl": 82, "type": 82, "tooling": 120, "comments": 180}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], minwidth=40, stretch=col in {"comments", "raw"})
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(10, 0))
        scroll = ttk.Scrollbar(table_panel, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(10, 0))
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<Double-1>", self.begin_cell_edit)

        side = ttk.Frame(mid, style="Panel.TFrame", padding=10, width=300)
        side.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        side.pack_propagate(False)
        ttk.Label(side, text="Run Log", style="PanelTitle.TLabel").pack(anchor="w")
        self.log_box = tk.Text(side, height=20, bg="#0b1118", fg="#d7e6f8", insertbackground="white", relief=tk.FLAT, wrap=tk.WORD, font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True, pady=(10, 10))
        self.log_box.insert(tk.END, "EZ-FAIR ready.\n")
        self.log_box.configure(state=tk.DISABLED)
        ttk.Label(side, text="Outputs", style="PanelTitle.TLabel").pack(anchor="w", pady=(4, 0))
        self.output_list = tk.Listbox(side, height=5, bg="#0b1118", fg="#d7e6f8", selectbackground=ACCENT_2, relief=tk.FLAT, font=("Segoe UI", 9))
        self.output_list.pack(fill=tk.X, pady=(8, 0))
        self.output_list.bind("<Double-1>", self.open_selected_output)

        footer = ttk.Frame(root, style="Root.TFrame")
        footer.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(footer, textvariable=self.status_text, style="Status.TLabel").pack(side=tk.LEFT)

    def _path_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, command) -> None:
        ttk.Label(parent, text=label, style="Body.TLabel").grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2, sticky="e", pady=4, padx=(8, 0))

    def log(self, message: str) -> None:
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, message.rstrip() + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)
        self.status_text.set(message.rstrip())
        self.update_idletasks()

    def pick_pdf(self) -> None:
        path = filedialog.askopenfilename(title="Select PDF blueprint", filetypes=[("PDF drawings", "*.pdf"), ("All files", "*.*")])
        if path:
            self.pdf_path.set(path)
            if not self.output_dir.get():
                self.output_dir.set(str(Path(path).parent / "local_outputs"))

    def pick_template(self) -> None:
        path = filedialog.askopenfilename(title="Select FAI Excel template", filetypes=[("Excel templates", "*.xlsx *.xlsm"), ("All files", "*.*")])
        if path:
            self.template_path.set(path)

    def pick_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_dir.set(path)

    def _validate_inputs(self) -> tuple[Path, Path, Path] | None:
        pdf = Path(self.pdf_path.get())
        template = Path(self.template_path.get())
        output = Path(self.output_dir.get())
        if not pdf.exists():
            messagebox.showerror(APP_NAME, "Pick a valid PDF blueprint first.")
            return None
        if not template.exists():
            messagebox.showerror(APP_NAME, "Pick a valid Excel FAI template first.")
            return None
        output.mkdir(parents=True, exist_ok=True)
        return pdf, template, output

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.configure(cursor="watch" if busy else "")

    def extract_review(self) -> None:
        if self._busy:
            return
        validated = self._validate_inputs()
        if not validated:
            return
        pdf, template, output = validated
        self.set_busy(True)
        self.log(f"Extracting dimensions from {pdf.name}...")

        def worker() -> None:
            try:
                chars = extract_pdf_dimensions(pdf)
                for char in chars:
                    char.metadata.setdefault("drawing_name", pdf.stem)
                capacity = template_row_capacity(template)
                skipped = len(get_last_skipped_candidates())
                self.after(0, lambda: self._load_extraction(chars, capacity, skipped))
            except Exception as exc:
                self.after(0, lambda: self._show_error("Extraction failed", exc))

        threading.Thread(target=worker, daemon=True).start()

    def _load_extraction(self, chars: list[Characteristic], capacity: int | None, skipped: int) -> None:
        self.characteristics = chars
        self.refresh_table()
        self.set_busy(False)
        self.log(f"Extracted {len(chars)} characteristics. Skipped {skipped} candidates.")

    def refresh_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for char in self.characteristics:
            self.tree.insert("", tk.END, iid=str(char.char_number), values=(char.char_number, char.page_index + 1, char.reference_location, char.raw_text, char.lsl, char.nominal, char.usl, char.type, char.tooling, char.comments))

    def begin_cell_edit(self, event) -> None:
        editable = {"raw", "lsl", "nominal", "usl", "type", "tooling", "comments", "ref"}
        columns = ("char", "page", "ref", "raw", "lsl", "nominal", "usl", "type", "tooling", "comments")
        item = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)
        if not item or not column_id:
            return
        col_index = int(column_id.replace("#", "")) - 1
        col_name = columns[col_index]
        if col_name not in editable:
            return
        bbox = self.tree.bbox(item, column_id)
        if not bbox:
            return
        x, y, width, height = bbox
        current = self.tree.set(item, col_name)
        editor = ttk.Entry(self.tree)
        editor.insert(0, current)
        editor.select_range(0, tk.END)
        editor.focus_set()
        editor.place(x=x, y=y, width=width, height=height)

        def commit(_event=None) -> None:
            new_value: Any = editor.get()
            editor.destroy()
            index = int(item) - 1
            if not (0 <= index < len(self.characteristics)):
                return
            char = self.characteristics[index]
            try:
                if col_name in {"lsl", "nominal", "usl"}:
                    setattr(char, col_name, float(new_value))
                elif col_name == "ref":
                    char.reference_location = str(new_value)
                elif col_name == "raw":
                    char.raw_text = str(new_value)
                else:
                    setattr(char, col_name, str(new_value))
                self.refresh_table()
            except ValueError:
                messagebox.showerror(APP_NAME, f"{col_name} must be numeric.")

        editor.bind("<Return>", commit)
        editor.bind("<FocusOut>", commit)
        editor.bind("<Escape>", lambda _event=None: editor.destroy())

    def delete_selected(self) -> None:
        selected = set(self.tree.selection())
        if not selected:
            return
        self.characteristics = [c for c in self.characteristics if str(c.char_number) not in selected]
        for idx, char in enumerate(self.characteristics, start=1):
            char.char_number = idx
        self.refresh_table()
        self.log(f"Deleted selected rows. {len(self.characteristics)} characteristics remain.")

    def clear_table(self) -> None:
        self.characteristics = []
        self.generated_outputs = {}
        self.refresh_table()
        self.output_list.delete(0, tk.END)
        self.log("Cleared current review table.")

    def generate_outputs(self) -> None:
        if self._busy:
            return
        validated = self._validate_inputs()
        if not validated:
            return
        if not self.characteristics:
            messagebox.showerror(APP_NAME, "Extract characteristics before generating outputs.")
            return
        pdf, template, output_dir = validated
        self.set_busy(True)
        self.log("Generating ballooned PDF, filled FAI, debug report, and summary...")

        def worker() -> None:
            try:
                suffix = ".xlsm" if template.suffix.lower() == ".xlsm" else ".xlsx"
                ballooned = output_dir / f"{pdf.stem}_BALLOONED.pdf"
                fai = output_dir / f"{pdf.stem}_FAI{suffix}"
                debug = output_dir / "EZ_FAI_DEBUG_REPORT.txt"
                summary = output_dir / "EXTRACTION_SUMMARY.txt"
                add_pdf_balloons(pdf, self.characteristics, ballooned)
                fill_fai_template(template, self.characteristics, fai)
                write_debug_report(pdf, template, self.characteristics, debug)
                write_extraction_summary(summary, self.characteristics, get_last_skipped_candidates(), template_row_capacity(template))
                outputs = {"Ballooned PDF": ballooned, "FAI Excel": fai, "Debug report": debug, "Extraction summary": summary}
                self.after(0, lambda: self._outputs_done(outputs))
            except Exception as exc:
                self.after(0, lambda: self._show_error("Output generation failed", exc))

        threading.Thread(target=worker, daemon=True).start()

    def _outputs_done(self, outputs: dict[str, Path]) -> None:
        self.generated_outputs = outputs
        self.output_list.delete(0, tk.END)
        for label, path in outputs.items():
            self.output_list.insert(tk.END, f"{label}: {path.name}")
        self.set_busy(False)
        self.log("Outputs generated successfully. Double-click an output to open it.")

    def _show_error(self, title: str, exc: Exception) -> None:
        self.set_busy(False)
        self.log(f"{title}: {exc}")
        messagebox.showerror(APP_NAME, f"{title}:\n\n{exc}")

    def open_selected_output(self, _event=None) -> None:
        selection = self.output_list.curselection()
        if not selection:
            return
        key = list(self.generated_outputs.keys())[selection[0]]
        self._open_path(self.generated_outputs[key])

    def open_output_folder(self) -> None:
        path = Path(self.output_dir.get() or Path.cwd())
        path.mkdir(parents=True, exist_ok=True)
        self._open_path(path)

    def open_app_folder(self) -> None:
        self._open_path(Path(__file__).resolve().parent)

    def _open_path(self, path: Path) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not open path:\n{path}\n\n{exc}")


def main() -> None:
    EzFairApp().mainloop()


if __name__ == "__main__":
    main()
