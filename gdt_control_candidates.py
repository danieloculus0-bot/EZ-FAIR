"""GD&T control candidates for EZ FAIR.

A geometric control is not automatically a standalone physical feature. This
module partitions geometric-control detections from ordinary dimensional
characteristics so they cannot receive independent balloons until a reviewer or
future association engine links them to the controlled feature.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import ez_fai_builder as base


@dataclass(frozen=True)
class GeometricControlCandidate:
    """Reviewable GD&T evidence that has not yet been linked to a feature."""

    page_index: int
    rect: tuple[float, float, float, float]
    control_type: str
    raw_text: str
    source_text: str
    nearby_text: str
    tolerance: float | None
    datum_note: str
    extraction_method: str
    status: str = "UNRESOLVED"

    @classmethod
    def from_characteristic(cls, item: base.Characteristic) -> "GeometricControlCandidate":
        control_type = item.type.removeprefix("GD&T:").strip() or "UNKNOWN"
        tolerance = item.usl if item.usl is not None else None
        return cls(
            page_index=item.page_index,
            rect=tuple(item.rect),
            control_type=control_type,
            raw_text=item.raw_text,
            source_text=str(item.metadata.get("source", "")),
            nearby_text=str(item.metadata.get("nearby", "")),
            tolerance=tolerance,
            datum_note=item.comments,
            extraction_method=str(item.metadata.get("extraction", "GD&T")),
        )


def is_geometric_control(item: base.Characteristic) -> bool:
    """Return True only for legacy GD&T rows produced by the enhancement pass."""

    return str(item.type).upper().startswith("GD&T:")


def partition_geometric_controls(
    items: Iterable[base.Characteristic],
) -> tuple[list[base.Characteristic], list[GeometricControlCandidate]]:
    """Separate balloonable features from unresolved geometric controls.

    Ordinary characteristics are renumbered after partitioning. Candidate
    controls retain source coordinates and text but intentionally have no
    balloon number.
    """

    features: list[base.Characteristic] = []
    controls: list[GeometricControlCandidate] = []

    for item in items:
        if is_geometric_control(item):
            controls.append(GeometricControlCandidate.from_characteristic(item))
        else:
            features.append(item)

    for number, feature in enumerate(features, start=1):
        feature.char_number = number

    return features, controls
