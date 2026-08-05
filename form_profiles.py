"""Controlled built-in inspection form profiles for EZ FAIR.

Users may enable, disable, and reorder approved sections and columns. They may
not invent arbitrary fields, formulas, or workbook structures.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

PROFILE_PATH = Path.home() / ".ez_fair_form_configuration.json"


@dataclass(frozen=True)
class FormField:
    key: str
    label: str
    field_type: str = "text"
    required: bool = False
    auto_source: str | None = None


@dataclass(frozen=True)
class FormColumn:
    key: str
    label: str
    width: int
    required: bool = False
    enabled_by_default: bool = True
    editable: bool = True
    formula: str | None = None
    validation_list: tuple[str, ...] = ()


@dataclass(frozen=True)
class FormSection:
    key: str
    label: str
    enabled_by_default: bool = True
    fields: tuple[FormField, ...] = ()


@dataclass(frozen=True)
class FormProfile:
    key: str
    label: str
    sections: tuple[FormSection, ...]
    columns: tuple[FormColumn, ...]
    dark_ui_only: bool = True

    @property
    def approved_section_keys(self) -> set[str]:
        return {item.key for item in self.sections}

    @property
    def approved_column_keys(self) -> set[str]:
        return {item.key for item in self.columns}


@dataclass
class FormConfiguration:
    profile_key: str = "ez_fair_r3"
    enabled_sections: list[str] = field(default_factory=list)
    enabled_columns: list[str] = field(default_factory=list)
    column_order: list[str] = field(default_factory=list)
    accent_color: str = "#00A7FF"
    button_color: str = "#1473E6"

    def validated(self, profile: FormProfile) -> "FormConfiguration":
        bad_sections = set(self.enabled_sections) - profile.approved_section_keys
        bad_columns = set(self.enabled_columns) - profile.approved_column_keys
        bad_order = set(self.column_order) - profile.approved_column_keys
        if bad_sections or bad_columns or bad_order:
            raise ValueError(
                "Only pre-approved form components may be configured. "
                f"Unknown sections={sorted(bad_sections)}, "
                f"columns={sorted(bad_columns | bad_order)}"
            )

        sections = list(dict.fromkeys(self.enabled_sections))
        columns = list(dict.fromkeys(self.enabled_columns))
        order = list(dict.fromkeys(self.column_order))

        if not sections:
            sections = [item.key for item in profile.sections if item.enabled_by_default]
        if not columns:
            columns = [item.key for item in profile.columns if item.enabled_by_default]

        for column in profile.columns:
            if column.required and column.key not in columns:
                columns.append(column.key)
        order = [key for key in order if key in columns]
        order.extend(key for key in columns if key not in order)

        return FormConfiguration(
            profile_key=self.profile_key,
            enabled_sections=sections,
            enabled_columns=columns,
            column_order=order,
            accent_color=self.accent_color,
            button_color=self.button_color,
        )


HEADER_FIELDS = (
    FormField("part_no", "Part No.", required=True, auto_source="title_block.part_no"),
    FormField("part_name", "Part Name", auto_source="title_block.part_name"),
    FormField("drawing_no", "Drawing No.", required=True, auto_source="title_block.drawing_no"),
    FormField("revision", "Revision", auto_source="title_block.revision"),
    FormField("date", "Date", field_type="date"),
    FormField("inspector", "Inspector"),
    FormField("item_no", "Item No.", auto_source="erp.item_no"),
    FormField("po_no", "PO No.", auto_source="erp.po_no"),
    FormField("order_no", "Order No.", auto_source="erp.order_no"),
    FormField("reason_for_fai", "Reason for FAI", field_type="choice"),
)

CORE_COLUMNS = (
    FormColumn("char_number", "Char. Number", 11, required=True, editable=False),
    FormColumn("reference_location", "Reference Location", 16, required=True),
    FormColumn("lsl", "LSL", 12, required=True),
    FormColumn("nominal", "Nominal", 12, required=True),
    FormColumn("usl", "USL", 12, required=True),
    FormColumn("feature_type", "Type", 16, required=True, validation_list=(
        "LINEAR", "DIAMETER", "RADIUS", "ANGLE", "CHAMFER", "THREAD", "WELD",
        "SURFACE FINISH", "NOTE", "MATERIAL", "GD&T CONTROL",
    )),
    FormColumn("supplier_actual", "Supplier Actual", 14),
    FormColumn("supplier_result", "Supplier Pass/Fail", 14, validation_list=("PASS", "FAIL")),
    FormColumn("ez_actual", "EZ FAIR Actual", 14),
    FormColumn("in_spec", "In Spec", 10, editable=False, formula="inclusive_limits"),
    FormColumn("qualified_tooling", "Qualified Tooling", 18, validation_list=(
        "VISUAL", "CALIPER", "MICROMETER", "HEIGHT GAGE", "PIN GAGE", "THREAD GAGE",
        "CMM", "SURFACE PLATE", "PROTRACTOR", "ANGLE GAGE", "TAPE", "CERTIFICATION",
        "FITMENT/NHA", "HARDWARE",
    )),
    FormColumn("comments", "Comments", 24),
)

EZ_FAIR_R3_PROFILE = FormProfile(
    key="ez_fair_r3",
    label="EZ FAIR R3",
    sections=(
        FormSection("header", "Part and Drawing Information", True, HEADER_FIELDS),
        FormSection("supplier", "Supplier Inspection Results", True),
        FormSection("internal", "EZ FAIR Inspection Results", True),
        FormSection("tooling", "Qualified Tooling", True),
        FormSection("comments", "Comments", True),
    ),
    columns=CORE_COLUMNS,
)

PROFILES = {EZ_FAIR_R3_PROFILE.key: EZ_FAIR_R3_PROFILE}


def get_profile(key: str = "ez_fair_r3") -> FormProfile:
    try:
        return PROFILES[key]
    except KeyError as exc:
        raise ValueError(f"Unknown approved form profile: {key}") from exc


def build_default_configuration(key: str = "ez_fair_r3") -> FormConfiguration:
    profile = get_profile(key)
    return FormConfiguration(profile_key=key).validated(profile)


def resolve_columns(config: FormConfiguration) -> list[FormColumn]:
    profile = get_profile(config.profile_key)
    clean = config.validated(profile)
    lookup = {column.key: column for column in profile.columns}
    return [lookup[key] for key in clean.column_order]


def validate_requested_keys(
    profile_key: str,
    section_keys: Iterable[str],
    column_keys: Iterable[str],
) -> None:
    profile = get_profile(profile_key)
    bad_sections = set(section_keys) - profile.approved_section_keys
    bad_columns = set(column_keys) - profile.approved_column_keys
    if bad_sections or bad_columns:
        raise ValueError(
            "Only pre-approved form components may be configured. "
            f"Unknown sections={sorted(bad_sections)}, columns={sorted(bad_columns)}"
        )


class FormConfigurationStore:
    def __init__(self, path: Path = PROFILE_PATH):
        self.path = path

    def load(self) -> FormConfiguration:
        if not self.path.exists():
            return build_default_configuration()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            config = FormConfiguration(**raw)
            return config.validated(get_profile(config.profile_key))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return build_default_configuration()

    def save(self, config: FormConfiguration) -> None:
        clean = config.validated(get_profile(config.profile_key))
        self.path.write_text(json.dumps(asdict(clean), indent=2), encoding="utf-8")
