"""Editable qualified-tooling catalog for EZ FAIR."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def _data_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "EZ FAIR"
    base.mkdir(parents=True, exist_ok=True)
    return base


TOOLING_PATH = _data_root() / "qualified_tooling.json"


@dataclass
class QualifiedTool:
    name: str
    tool_id: str = ""
    category: str = "GENERAL"
    calibration_required: bool = False
    active: bool = True
    notes: str = ""

    def validate(self) -> None:
        self.name = self.name.strip().upper()
        self.tool_id = self.tool_id.strip().upper()
        self.category = self.category.strip().upper() or "GENERAL"
        if not self.name:
            raise ValueError("Tool name is required.")


DEFAULT_TOOLS = [
    QualifiedTool("VISUAL", category="ATTRIBUTE"),
    QualifiedTool("CALIPER", category="VARIABLE", calibration_required=True),
    QualifiedTool("MICROMETER", category="VARIABLE", calibration_required=True),
    QualifiedTool("HEIGHT GAGE", category="VARIABLE", calibration_required=True),
    QualifiedTool("PIN GAGE", category="ATTRIBUTE", calibration_required=True),
    QualifiedTool("THREAD GAGE", category="ATTRIBUTE", calibration_required=True),
    QualifiedTool("CMM", category="VARIABLE", calibration_required=True),
    QualifiedTool("SURFACE PLATE", category="REFERENCE", calibration_required=True),
    QualifiedTool("PROTRACTOR", category="VARIABLE", calibration_required=True),
    QualifiedTool("ANGLE GAGE", category="ATTRIBUTE", calibration_required=True),
    QualifiedTool("TAPE", category="VARIABLE", calibration_required=True),
    QualifiedTool("CERTIFICATION", category="DOCUMENT"),
    QualifiedTool("FITMENT/NHA", category="ATTRIBUTE"),
    QualifiedTool("HARDWARE", category="ATTRIBUTE"),
]


class QualifiedToolStore:
    def __init__(self, path: Path = TOOLING_PATH):
        self.path = path

    def load(self) -> list[QualifiedTool]:
        if not self.path.exists():
            self.save(DEFAULT_TOOLS)
            return [QualifiedTool(**asdict(item)) for item in DEFAULT_TOOLS]
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            tools = [QualifiedTool(**item) for item in raw]
            for tool in tools:
                tool.validate()
            return tools
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return [QualifiedTool(**asdict(item)) for item in DEFAULT_TOOLS]

    def save(self, tools: list[QualifiedTool]) -> None:
        cleaned: list[QualifiedTool] = []
        seen: set[tuple[str, str]] = set()
        for tool in tools:
            tool.validate()
            key = (tool.name, tool.tool_id)
            if key in seen:
                raise ValueError(f"Duplicate qualified tool: {tool.name} {tool.tool_id}".strip())
            seen.add(key)
            cleaned.append(tool)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(item) for item in cleaned], indent=2), encoding="utf-8")

    def active_labels(self) -> list[str]:
        labels: list[str] = []
        for tool in self.load():
            if not tool.active:
                continue
            labels.append(f"{tool.name} [{tool.tool_id}]" if tool.tool_id else tool.name)
        return labels
