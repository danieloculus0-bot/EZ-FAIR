"""FAI-oriented characteristic ordering.

FAI balloon numbers are traceability identifiers, not a PDF text-reading order.
This module groups nearby callouts/features and then walks the drawing clockwise,
keeping local feature clusters consecutive and stable.
"""
from __future__ import annotations

from collections import defaultdict
from math import atan2, hypot, pi
from typing import Any, Iterable


def _center(item: Any) -> tuple[float, float]:
    x0, y0, x1, y1 = item.rect
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def _norm_source(item: Any) -> str:
    value = str(getattr(item, "metadata", {}).get("source", "") or "")
    return " ".join(value.upper().split())


def _page_size(items: list[Any]) -> tuple[float, float]:
    widths = [float(getattr(item, "metadata", {}).get("page_width", 0) or 0) for item in items]
    heights = [float(getattr(item, "metadata", {}).get("page_height", 0) or 0) for item in items]
    width = max(widths or [0.0])
    height = max(heights or [0.0])
    if width <= 0:
        width = max((float(item.rect[2]) for item in items), default=1000.0) + 40.0
    if height <= 0:
        height = max((float(item.rect[3]) for item in items), default=1000.0) + 40.0
    return width, height


def _linked(a: Any, b: Any, width: float, height: float) -> bool:
    if a.page_index != b.page_index:
        return False

    ax, ay = _center(a)
    bx, by = _center(b)
    dx, dy = abs(ax - bx), abs(ay - by)

    source_a, source_b = _norm_source(a), _norm_source(b)
    if source_a and source_a == source_b:
        return True

    # Keep callouts that are physically local together. Thresholds scale with
    # the drawing but are capped so a dense sheet does not collapse into one group.
    x_gate = min(100.0, max(42.0, width * 0.055))
    y_gate = min(76.0, max(32.0, height * 0.050))
    if dx <= x_gate and dy <= y_gate:
        return True

    # Same drawing zone plus short diagonal distance is another strong signal
    # that the items belong to the same view/callout neighborhood.
    same_zone = getattr(a, "reference_location", "") == getattr(b, "reference_location", "")
    diag_gate = min(125.0, max(60.0, hypot(width, height) * 0.07))
    return same_zone and hypot(dx, dy) <= diag_gate


def _clusters(items: list[Any], width: float, height: float) -> list[list[Any]]:
    parent = list(range(len(items)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _linked(items[i], items[j], width, height):
                union(i, j)

    grouped: dict[int, list[Any]] = defaultdict(list)
    for index, item in enumerate(items):
        grouped[find(index)].append(item)
    return list(grouped.values())


def _clockwise_key(x: float, y: float, cx: float, cy: float) -> tuple[float, float]:
    # Start at 12 o'clock and move clockwise.
    angle = (atan2(y - cy, x - cx) + pi / 2.0) % (2.0 * pi)
    radius = hypot(x - cx, y - cy)
    return angle, radius


def _order_cluster(cluster: list[Any]) -> list[Any]:
    if len(cluster) <= 1:
        return cluster[:]
    cx = sum(_center(item)[0] for item in cluster) / len(cluster)
    cy = sum(_center(item)[1] for item in cluster) / len(cluster)
    return sorted(cluster, key=lambda item: _clockwise_key(*_center(item), cx, cy))


def order_characteristics_for_fai(characteristics: Iterable[Any]) -> list[Any]:
    """Return characteristics in a stable FAI-friendly sequence.

    Pages are kept in order. Within each page, physically related annotations
    are grouped first, groups are walked clockwise around the sheet, and group
    members remain consecutive. Characteristic numbers are then reassigned.
    """
    pages: dict[int, list[Any]] = defaultdict(list)
    for item in characteristics:
        pages[int(item.page_index)].append(item)

    ordered: list[Any] = []
    group_number = 0
    for page_index in sorted(pages):
        page_items = pages[page_index]
        width, height = _page_size(page_items)
        page_cx, page_cy = width / 2.0, height / 2.0

        clusters = _clusters(page_items, width, height)
        clusters.sort(
            key=lambda cluster: _clockwise_key(
                sum(_center(item)[0] for item in cluster) / len(cluster),
                sum(_center(item)[1] for item in cluster) / len(cluster),
                page_cx,
                page_cy,
            )
        )

        for cluster in clusters:
            group_number += 1
            for item in _order_cluster(cluster):
                item.metadata["balloon_group"] = group_number
                item.metadata["balloon_ordering"] = "FAI_CLOCKWISE_LOCAL_GROUP"
                ordered.append(item)

    for number, item in enumerate(ordered, start=1):
        item.char_number = number
    return ordered
