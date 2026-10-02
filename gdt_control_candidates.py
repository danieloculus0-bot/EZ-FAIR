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


def _center(item: base.Characteristic) -> tuple[float, float]:
    x0, y0, x1, y1 = item.rect
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def _association_distance(feature: base.Characteristic, control: base.Characteristic) -> float:
    fx, fy = _center(feature)
    cx, cy = _center(control)
    return ((fx - cx) ** 2 + (fy - cy) ** 2) ** 0.5


def _association_gate(control: base.Characteristic) -> float:
    width = float(control.metadata.get("page_width", 0) or 0)
    height = float(control.metadata.get("page_height", 0) or 0)
    if width > 0 and height > 0:
        diagonal = (width * width + height * height) ** 0.5
        return min(150.0, max(65.0, diagonal * 0.09))
    return 100.0


def partition_geometric_controls(
    items: Iterable[base.Characteristic],
) -> tuple[list[base.Characteristic], list[GeometricControlCandidate]]:
    """Link clear GD&T controls to nearby features and hold ambiguity for review.

    A feature-control frame is itself an inspectable design characteristic for
    FAI purposes. When a control is spatially close to one dimensional feature,
    keep it immediately after that feature so the balloon/Form 3 sequence stays
    logical. Controls that cannot be associated confidently remain unresolved
    and are not auto-ballooned.
    """

    features: list[base.Characteristic] = []
    control_items: list[base.Characteristic] = []
    unresolved: list[GeometricControlCandidate] = []

    for item in items:
        if is_geometric_control(item):
            control_items.append(item)
        else:
            features.append(item)

    linked: dict[int, list[base.Characteristic]] = {id(feature): [] for feature in features}
    for control in control_items:
        same_page = [feature for feature in features if feature.page_index == control.page_index]
        if not same_page:
            unresolved.append(GeometricControlCandidate.from_characteristic(control))
            continue

        ranked_features = sorted(same_page, key=lambda feature: _association_distance(feature, control))
        best_feature = ranked_features[0]
        best_distance = _association_distance(best_feature, control)
        second_distance = _association_distance(ranked_features[1], control) if len(ranked_features) > 1 else float("inf")
        gate = _association_gate(control)

        # Require the best candidate to be local and meaningfully better than
        # the runner-up. This avoids silently attaching an FCF in a crowded view.
        unambiguous = best_distance <= gate and (
            second_distance == float("inf") or best_distance <= second_distance * 0.72
        )
        if not unambiguous:
            unresolved.append(GeometricControlCandidate.from_characteristic(control))
            continue

        control.metadata["linked_feature_raw_text"] = best_feature.raw_text
        control.metadata["linked_feature_reference"] = best_feature.reference_location
        control.metadata["balloon_group"] = best_feature.metadata.get("balloon_group")
        control.metadata["gdt_association"] = "AUTO_NEAREST_UNAMBIGUOUS"
        control.comments = (control.comments + f" Linked to {best_feature.raw_text or best_feature.reference_location}.").strip()
        linked[id(best_feature)].append(control)

    balloonable: list[base.Characteristic] = []
    for feature in features:
        balloonable.append(feature)
        balloonable.extend(sorted(linked[id(feature)], key=lambda item: _association_distance(feature, item)))

    for number, item in enumerate(balloonable, start=1):
        item.char_number = number

    return balloonable, unresolved

