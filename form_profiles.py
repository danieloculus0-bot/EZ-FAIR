"""Configurable inspection form profiles for EZ FAIR."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROFILE_PATH = Path.home() / ".ez_fair_form_profiles.json"

AVAILABLE_COLUMNS = [
    "balloon_number", "reference_location", "requirement", "feature_type", "quantity",
    "nominal", "lower_limit", "upper_limit", "units", "tolerance_source", "actual",
    "attribute_result", "pass_fail", "qualified_tooling", "tool_id", "operation",
    "sampling_frequency", "inspector", "inspection_date", "serial_lot", "comments",
    "source_confidence", "review_status",
]


@dataclass
class FormColumn:
    field: str
    label: str
    visible: bool = True
    required: bool = False
    width: int = 14
    choices: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if self.field not in AVAILABLE_COLUMNS:
            raise ValueError(f"Unsupported form column: {self.field}")
        if self.width < 4 or self.width > 80:
            raise ValueError("Column width must be between 4 and 80")


@dataclass
class FormProfile:
    name: str = "EZ FAIR Standard"
    metadata_fields: list[str] = field(default_factory=lambda: [
        "part_number", "drawing_number", "revision", "description", "job_number"
    ])
    columns: list[FormColumn] = field(default_factory=lambda: [
        FormColumn("balloon_number", "Balloon", width=8),
        FormColumn("reference_location", "Location", width=12),
        FormColumn("requirement", "Requirement", width=28),
        FormColumn("feature_type", "Type", width=14),
        FormColumn("actual", "Actual", width=12),
        FormColumn("pass_fail", "Accept", width=10),
        FormColumn("qualified_tooling", "Qualified Tooling", visible=False, width=18),
        FormColumn("comments", "Comments", width=24),
    ])

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Form profile name is required")
        seen: set[str] = set()
        for column in self.columns:
            column.validate()
            if column.field in seen:
                raise ValueError(f"Duplicate form column: {column.field}")
            seen.add(column.field)

    def set_visible(self, field_name: str, visible: bool) -> None:
        for column in self.columns:
            if column.field == field_name:
                column.visible = visible
                return
        raise KeyError(field_name)

    def add_column(self, field_name: str, label: str | None = None) -> None:
        if field_name not in AVAILABLE_COLUMNS:
            raise ValueError(field_name)
        if any(column.field == field_name for column in self.columns):
            raise ValueError(f"Column already exists: {field_name}")
        self.columns.append(FormColumn(field_name, label or field_name.replace("_", " ").title()))

    def remove_column(self, field_name: str) -> None:
        original = len(self.columns)
        self.columns = [column for column in self.columns if column.field != field_name]
        if len(self.columns) == original:
            raise KeyError(field_name)

    def visible_columns(self) -> list[FormColumn]:
        return [column for column in self.columns if column.visible]


class FormProfileStore:
    def __init__(self, path: Path = PROFILE_PATH):
        self.path = path

    def load(self) -> list[FormProfile]:
        if not self.path.exists():
            return [FormProfile()]
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            profiles = []
            for item in raw:
                columns = [FormColumn(**column) for column in item.get("columns", [])]
                profile = FormProfile(name=item.get("name", "Unnamed"), metadata_fields=item.get("metadata_fields", []), columns=columns)
                profile.validate()
                profiles.append(profile)
            return profiles or [FormProfile()]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return [FormProfile()]

    def save(self, profiles: list[FormProfile]) -> None:
        for profile in profiles:
            profile.validate()
        self.path.write_text(json.dumps([asdict(profile) for profile in profiles], indent=2), encoding="utf-8")
