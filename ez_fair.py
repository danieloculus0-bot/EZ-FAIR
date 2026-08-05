"""EZ FAIR industrial desktop application."""
from __future__ import annotations

import webbrowser
from dataclasses import asdict
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import ez_fai_builder as base
from app_version import APP_VERSION
from built_in_form_writer import write_inspection_workbook
from ez_fair_enhancements import ExtractionSettings, extract_pdf_dimensions_enhanced
from form_profiles import FormConfiguration, FormConfigurationStore, build_default_configuration, get_profile
from gdt_control_candidates import GeometricControlCandidate, partition_geometric_controls
from project_store import ProjectMetadata, ProjectRecord, ProjectStore
from title_block_metadata import extract_title_block_metadata
from tooling_store import QualifiedTool, QualifiedToolStore
from update_manager import check_for_updates, download_and_launch_installer

BG = "#101419"
PANEL = "#1A2027"
PANEL_2 = "#242C35"
TEXT = "#F2F5F8"
MUTED = "#AAB4C0"
ACCENT = "#00A7FF"
BUTTON = "#1473E6"
DANGER = "#A33A3A"


class EZFairApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"EZ FAIR {APP_VERSION}")
        self.geometry("1500x880")
        self.minsize(1150, 700)
        self.configure(bg=BG)

        self.settings = ExtractionSettings.load()
        self.project_store = ProjectStore()
        self.tool_store = QualifiedToolStore()
        self.form_store = FormConfigurationStore()
        self.form_config = self.form_store.load()
        self.project = ProjectRecord(form_configuration=asdict(self.form_config))
        self.pdf_path: Path | None = None
        self.characteristics: list[base.Characteristic] = []
        self.gdt_controls: list[GeometricControlCandidate] = []
        self.metadata_vars: dict[str, tk.StringVar] = {}
        self.section_vars: dict[str, tk.BooleanVar] = {}
        self.column_vars: dict[str, tk.BooleanVar] = {}

        self._configure_style()
        self._build_ui()
        self._load_project_into_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=BG, foreground=TEXT, fieldbackground=PANEL, bordercolor=PANEL_2)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("TButton", background=BUTTON, foreground="white", padding=(12, 8), borderwidth=0)
        style.map("TButton", background=[("active", ACCENT), ("pressed", PANEL_2)])
        style.configure("Danger.TButton", background=DANGER)
        style.configure("TEntry", fieldbackground=PANEL_2, foreground=TEXT, insertcolor=TEXT, padding=6)
        style.configure("TCheckbutton", background=BG, foreground=TEXT)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 9))
        style.map("TNotebook.Tab", background=[("selected", PANEL_2)], foreground=[("selected", TEXT)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=28)
        style.configure("Treeview.Heading", background=PANEL_2, foreground=TEXT, relief="flat")
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self, style="Panel.TFrame", padding=8)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="NEW", command=self.new_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="OPEN", command=self.open_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="SAVE", command=self.save_project).pack(side=tk.LEFT, padx=3)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(toolbar, text="SELECT DRAWING", command=self.select_pdf).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="EXTRACT + REVIEW", command=self.extract_dimensions).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="GENERATE PACKET", command=self.generate_outputs).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="DELETE ROW", style="Danger.TButton", command=self.delete_rows).pack(side=tk.LEFT, padx=3)
        self.project_label = ttk.Label(toolbar, text="Untitled Project", style="Muted.TLabel")
        self.project_label.pack(side=tk.RIGHT, padx=8)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.review_tab = ttk.Frame(notebook)
        self.metadata_tab = ttk.Frame(notebook)
        self.form_tab = ttk.Frame(notebook)
        self.tooling_tab = ttk.Frame(notebook)
        self.settings_tab = ttk.Frame(notebook)
        notebook.add(self.review_tab, text="DRAWING REVIEW")
        notebook.add(self.metadata_tab, text="DRAWING DATA")
        notebook.add(self.form_tab, text="FORM CONFIGURATION")
        notebook.add(self.tooling_tab, text="QUALIFIED TOOLING")
        notebook.add(self.settings_tab, text="SETTINGS")

        review_top = ttk.Frame(self.review_tab, style="Panel.TFrame", padding=10)
        review_top.pack(fill=tk.X)
        self.pdf_label = ttk.Label(review_top, text="No drawing selected", style="Muted.TLabel")
        self.pdf_label.pack(side=tk.LEFT)
        self.gdt_label = ttk.Label(review_top, text="GD&T unresolved: 0", style="Muted.TLabel")
        self.gdt_label.pack(side=tk.RIGHT)
        self.review_table = base.ReviewTable(self.review_tab)
        self.review_table.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._build_metadata_tab()
        self._build_form_tab()
        self._build_tooling_tab()
        self._build_settings_tab()

        self.status = tk.StringVar(value="READY")
        ttk.Label(self, textvariable=self.status, relief=tk.SUNKEN, anchor="w", padding=(8, 5)).pack(fill=tk.X, side=tk.BOTTOM)

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
        ttk.Label(container, text="Auto-populated values are candidates. Verify before releasing the packet.", style="Muted.TLabel").grid(
            row=9, column=0, columnspan=4, sticky="w", padx=8, pady=16
        )

    def _build_form_tab(self) -> None:
        profile = get_profile(self.form_config.profile_key)
        sections = ttk.LabelFrame(self.form_tab, text="Approved Sections", padding=14)
        sections.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12, pady=12)
        for section in profile.sections:
            var = tk.BooleanVar(value=section.key in self.form_config.enabled_sections)
            self.section_vars[section.key] = var
            ttk.Checkbutton(sections, text=section.label, variable=var).pack(anchor="w", pady=5)

        columns = ttk.LabelFrame(self.form_tab, text="Approved Columns", padding=14)
        columns.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12, pady=12)
        for column in profile.columns:
            var = tk.BooleanVar(value=column.key in self.form_config.enabled_columns)
            self.column_vars[column.key] = var
            checkbox = ttk.Checkbutton(columns, text=column.label, variable=var)
            checkbox.pack(anchor="w", pady=3)
            if column.required:
                var.set(True)
                checkbox.state(["disabled"])
        ttk.Button(columns, text="SAVE FORM CONFIGURATION", command=self.save_form_configuration).pack(anchor="w", pady=16)

    def _build_tooling_tab(self) -> None:
        top = ttk.Frame(self.tooling_tab, padding=12)
        top.pack(fill=tk.X)
        ttk.Button(top, text="ADD TOOL", command=self.add_tool).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="DELETE SELECTED", style="Danger.TButton", command=self.delete_tool).pack(side=tk.LEFT, padx=4)
        ttk.Label(top, text="Qualified tooling is intentionally editable. Add shop-specific IDs and methods here.", style="Muted.TLabel").pack(side=tk.LEFT, padx=12)
        self.tool_tree = ttk.Treeview(self.tooling_tab, columns=("name", "id", "category", "cal", "active", "notes"), show="headings")
        for key, label, width in [
            ("name", "Tool", 180), ("id", "Tool ID", 130), ("category", "Category", 130),
            ("cal", "Calibration Required", 150), ("active", "Active", 80), ("notes", "Notes", 360),
        ]:
            self.tool_tree.heading(key, text=label)
            self.tool_tree.column(key, width=width)
        self.tool_tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.tool_tree.bind("<Double-1>", self.edit_tool)
        self.refresh_tools()

    def _build_settings_tab(self) -> None:
        frame = ttk.Frame(self.settings_tab, padding=18)
        frame.pack(fill=tk.BOTH, expand=True)
        self.two_place_var = tk.StringVar(value=str(self.settings.two_place))
        self.three_place_var = tk.StringVar(value=str(self.settings.three_place))
        self.angular_var = tk.StringVar(value=str(self.settings.angular))
        self.ocr_dpi_var = tk.StringVar(value=str(self.settings.ocr_dpi))
        self.auto_title_var = tk.BooleanVar(value=self.settings.auto_detect_title_block)
        self.ocr_var = tk.BooleanVar(value=self.settings.enable_ocr_fallback)
        for row, (label, var) in enumerate([
            ("Two-place default ±", self.two_place_var),
            ("Three-place default ±", self.three_place_var),
            ("Angular default ± degrees", self.angular_var),
            ("OCR DPI", self.ocr_dpi_var),
        ]):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=6)
            ttk.Entry(frame, textvariable=var, width=16).grid(row=row, column=1, sticky="w", padx=6, pady=6)
        ttk.Checkbutton(frame, text="Auto-detect title block", variable=self.auto_title_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=6)
        ttk.Checkbutton(frame, text="Use local OCR fallback", variable=self.ocr_var).grid(row=5, column=0, columnspan=2, sticky="w", pady=6)
        ttk.Button(frame, text="SAVE SETTINGS", command=self.save_settings).grid(row=6, column=0, sticky="w", pady=14)
        ttk.Button(frame, text="CHECK FOR UPDATES", command=self.check_updates).grid(row=6, column=1, sticky="w", pady=14)
        ttk.Label(frame, text=f"Installed version: {APP_VERSION}", style="Muted.TLabel").grid(row=7, column=0, columnspan=2, sticky="w")

    def new_project(self) -> None:
        if self.characteristics and not messagebox.askyesno("New Project", "Start a new project? Unsaved edits will be lost."):
            return
        self.project = ProjectRecord(form_configuration=asdict(self.form_config))
        self.pdf_path = None
        self.characteristics = []
        self.gdt_controls = []
        self.review_table.load([])
        self._load_project_into_ui()
        self.status.set("NEW PROJECT")

    def open_project(self) -> None:
        recent = self.project_store.recent(30)
        if not recent:
            messagebox.showinfo("Open Project", "No saved projects exist yet.")
            return
        choices = "\n".join(f"{index + 1}. {item['name']} [{item['status']}]" for index, item in enumerate(recent))
        selected = simpledialog.askinteger("Open Project", f"Enter project number:\n\n{choices}", minvalue=1, maxvalue=len(recent))
        if not selected:
            return
        self.project = self.project_store.load(recent[selected - 1]["id"])
        self.pdf_path = Path(self.project.source_pdf) if self.project.source_pdf else None
        self.characteristics = [base.Characteristic(**item) for item in self.project.characteristics]
        self.gdt_controls = [GeometricControlCandidate(**item) for item in self.project.gdt_controls]
        self._load_project_into_ui()
        self.status.set(f"OPENED {self.project.name}")

    def _sync_project_from_ui(self) -> None:
        self.characteristics = self.review_table.characteristics
        self.project.metadata = ProjectMetadata(**{key: var.get().strip() for key, var in self.metadata_vars.items()})
        self.project.source_pdf = str(self.pdf_path or "")
        self.project.characteristics = [asdict(item) for item in self.characteristics]
        self.project.gdt_controls = [asdict(item) for item in self.gdt_controls]
        self.project.form_configuration = asdict(self.form_config)
        if self.project.metadata.drawing_no:
            self.project.name = f"{self.project.metadata.drawing_no} Rev {self.project.metadata.revision or '-'}"
        elif self.pdf_path:
            self.project.name = self.pdf_path.stem

    def _load_project_into_ui(self) -> None:
        for key, var in self.metadata_vars.items():
            var.set(getattr(self.project.metadata, key, ""))
        self.review_table.load(self.characteristics)
        self.pdf_label.config(text=str(self.pdf_path) if self.pdf_path else "No drawing selected")
        self.gdt_label.config(text=f"GD&T unresolved: {len(self.gdt_controls)}")
        self.project_label.config(text=self.project.name)

    def save_project(self) -> None:
        try:
            self._sync_project_from_ui()
            self.project_store.save(self.project)
            self.project_label.config(text=self.project.name)
            self.status.set(f"SAVED {self.project.name}")
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc))

    def select_pdf(self) -> None:
        filename = filedialog.askopenfilename(title="Select drawing PDF", filetypes=[("PDF drawings", "*.pdf")])
        if not filename:
            return
        self.pdf_path = Path(filename)
        self.project.source_pdf = filename
        self.pdf_label.config(text=filename)
        try:
            metadata = extract_title_block_metadata(self.pdf_path)
            self.project.metadata = metadata
            for key, var in self.metadata_vars.items():
                var.set(getattr(metadata, key, ""))
            self.project.name = metadata.drawing_no or self.pdf_path.stem
            self.project_label.config(text=self.project.name)
            self.status.set("DRAWING LOADED | TITLE BLOCK CANDIDATES READY FOR REVIEW")
        except Exception as exc:
            self.status.set(f"DRAWING LOADED | METADATA WARNING: {exc}")

    def extract_dimensions(self) -> None:
        if not self.pdf_path:
            messagebox.showwarning("Missing Drawing", "Select a drawing PDF first.")
            return
        try:
            self.save_settings(silent=True)
            self.status.set("EXTRACTING VECTOR TEXT, OCR CANDIDATES, TOLERANCES, AND GD&T")
            self.update_idletasks()
            extracted = extract_pdf_dimensions_enhanced(self.pdf_path, self.settings)
            self.characteristics, self.gdt_controls = partition_geometric_controls(extracted)
            for item in self.characteristics:
                item.metadata["drawing_name"] = self.project.metadata.drawing_no or self.pdf_path.stem
            self.review_table.load(self.characteristics)
            self.gdt_label.config(text=f"GD&T unresolved: {len(self.gdt_controls)}")
            self.save_project()
            self.status.set(f"EXTRACTED {len(self.characteristics)} FEATURES | {len(self.gdt_controls)} GD&T CONTROLS HELD FOR REVIEW")
        except Exception as exc:
            self.status.set("EXTRACTION FAILED")
            messagebox.showerror("Extraction Failed", str(exc))

    def delete_rows(self) -> None:
        self.review_table.delete_selected()
        self.characteristics = self.review_table.characteristics
        self.status.set(f"{len(self.characteristics)} CHARACTERISTICS REMAIN")

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
            base.generate_ballooned_pdf(self.pdf_path, self.characteristics, ballooned)
            write_inspection_workbook(workbook, self.project.metadata, self.characteristics, self.form_config)
            self.project.status = "PACKET GENERATED"
            self.project_store.save(self.project)
            self.status.set(f"PACKET COMPLETE | {ballooned.name} | {workbook.name}")
            messagebox.showinfo("Packet Complete", f"Created:\n{ballooned}\n{workbook}")
        except Exception as exc:
            self.status.set("PACKET GENERATION FAILED")
            messagebox.showerror("Generation Failed", str(exc))

    def save_form_configuration(self) -> None:
        try:
            config = FormConfiguration(
                profile_key=self.form_config.profile_key,
                enabled_sections=[key for key, var in self.section_vars.items() if var.get()],
                enabled_columns=[key for key, var in self.column_vars.items() if var.get()],
                column_order=[key for key in get_profile(self.form_config.profile_key).approved_column_keys if self.column_vars.get(key, tk.BooleanVar(value=False)).get()],
                accent_color=ACCENT,
                button_color=BUTTON,
            ).validated(get_profile(self.form_config.profile_key))
            self.form_config = config
            self.form_store.save(config)
            self.status.set("FORM CONFIGURATION SAVED")
        except Exception as exc:
            messagebox.showerror("Form Configuration", str(exc))

    def refresh_tools(self) -> None:
        self.tool_tree.delete(*self.tool_tree.get_children())
        for index, tool in enumerate(self.tool_store.load()):
            self.tool_tree.insert("", tk.END, iid=str(index), values=(tool.name, tool.tool_id, tool.category, "YES" if tool.calibration_required else "NO", "YES" if tool.active else "NO", tool.notes))

    def add_tool(self) -> None:
        name = simpledialog.askstring("Add Qualified Tool", "Tool name:")
        if not name:
            return
        tool_id = simpledialog.askstring("Add Qualified Tool", "Tool ID or asset number (optional):") or ""
        category = simpledialog.askstring("Add Qualified Tool", "Category:", initialvalue="VARIABLE") or "VARIABLE"
        tools = self.tool_store.load()
        tools.append(QualifiedTool(name=name, tool_id=tool_id, category=category, calibration_required=True))
        try:
            self.tool_store.save(tools)
            self.refresh_tools()
        except Exception as exc:
            messagebox.showerror("Tooling", str(exc))

    def edit_tool(self, _event=None) -> None:
        selected = self.tool_tree.selection()
        if not selected:
            return
        index = int(selected[0])
        tools = self.tool_store.load()
        tool = tools[index]
        tool.name = simpledialog.askstring("Edit Tool", "Tool name:", initialvalue=tool.name) or tool.name
        tool.tool_id = simpledialog.askstring("Edit Tool", "Tool ID:", initialvalue=tool.tool_id) or tool.tool_id
        tool.category = simpledialog.askstring("Edit Tool", "Category:", initialvalue=tool.category) or tool.category
        tool.notes = simpledialog.askstring("Edit Tool", "Notes:", initialvalue=tool.notes) or tool.notes
        try:
            self.tool_store.save(tools)
            self.refresh_tools()
        except Exception as exc:
            messagebox.showerror("Tooling", str(exc))

    def delete_tool(self) -> None:
        selected = self.tool_tree.selection()
        if not selected:
            return
        tools = self.tool_store.load()
        tools.pop(int(selected[0]))
        self.tool_store.save(tools)
        self.refresh_tools()

    def save_settings(self, silent: bool = False) -> None:
        try:
            self.settings.two_place = float(self.two_place_var.get())
            self.settings.three_place = float(self.three_place_var.get())
            self.settings.angular = float(self.angular_var.get())
            self.settings.ocr_dpi = int(self.ocr_dpi_var.get())
            if not 150 <= self.settings.ocr_dpi <= 600:
                raise ValueError("OCR DPI must be between 150 and 600.")
            self.settings.auto_detect_title_block = self.auto_title_var.get()
            self.settings.enable_ocr_fallback = self.ocr_var.get()
            self.settings.save()
            if not silent:
                self.status.set("SETTINGS SAVED")
        except Exception as exc:
            if silent:
                raise
            messagebox.showerror("Settings", str(exc))

    def check_updates(self) -> None:
        self.status.set("CHECKING FOR UPDATES")
        self.update_idletasks()
        try:
            info = check_for_updates()
            if not info.available:
                messagebox.showinfo("EZ FAIR Update", f"Version {APP_VERSION} is current.")
                self.status.set("CURRENT VERSION INSTALLED")
                return
            if not messagebox.askyesno("Update Available", f"Install EZ FAIR {info.latest_version} now?"):
                return
            if not info.download_url:
                webbrowser.open(info.release_url)
                return
            installer = download_and_launch_installer(info)
            self.status.set(f"UPDATE INSTALLER STARTED | {installer.name}")
        except Exception as exc:
            self.status.set("UPDATE CHECK FAILED")
            messagebox.showerror("Update Check Failed", str(exc))

    def _on_close(self) -> None:
        try:
            if self.characteristics or self.pdf_path:
                self.save_project()
        finally:
            self.destroy()


def launch_gui() -> None:
    EZFairApp().mainloop()


if __name__ == "__main__":
    launch_gui()
