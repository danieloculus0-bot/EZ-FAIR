"""Conservative title-block metadata extraction for engineering drawings."""
from __future__ import annotations

import re
from pathlib import Path

import fitz

from project_store import ProjectMetadata

LABEL_PATTERNS: dict[str, tuple[str, ...]] = {
    "part_no": (r"PART\s*(?:NO\.?|NUMBER|#)\s*[:\-]?\s*([^\n|]{2,48})", r"P/N\s*[:\-]?\s*([^\n|]{2,48})"),
    "drawing_no": (r"(?:DWG|DRAWING)\s*(?:NO\.?|NUMBER|#)\s*[:\-]?\s*([^\n|]{2,48})",),
    "revision": (r"(?:REV|REVISION)\s*[:\-]?\s*([A-Z0-9.\-]{1,12})",),
    "part_name": (r"(?:TITLE|DESCRIPTION|PART\s*NAME)\s*[:\-]?\s*([^\n|]{3,80})",),
    "material": (r"(?:MATERIAL|MATL)\s*[:\-]?\s*([^\n|]{2,80})",),
    "scale": (r"SCALE\s*[:\-]?\s*([^\s|]{1,20})",),
    "sheet": (r"SHEET\s*[:\-]?\s*([^\n|]{1,24})",),
    "drawing_date": (r"(?:DRAWN\s*DATE|DATE)\s*[:\-]?\s*([0-9/\-.]{6,16})",),
}


def _clean(value: str) -> str:
    value = " ".join(value.replace("\r", " ").split())
    value = re.split(r"\s{2,}|(?:\b(?:REV|SCALE|SHEET|DATE|DRAWN|CHECKED|APPROVED)\b\s*:?)", value, maxsplit=1, flags=re.I)[0]
    return value.strip(" :-|")[:100]


def _find(text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            cleaned = _clean(match.group(1))
            if cleaned:
                return cleaned
    return ""


def extract_title_block_metadata(pdf_path: str | Path) -> ProjectMetadata:
    """Read likely metadata from the bottom-right region, then full first page.

    Results are candidates for human review, never silently treated as approved.
    """
    path = Path(pdf_path)
    metadata = ProjectMetadata()
    with fitz.open(path) as document:
        if not document.page_count:
            return metadata
        page = document[0]
        rect = page.rect
        title_clip = fitz.Rect(rect.width * 0.55, rect.height * 0.55, rect.width, rect.height)
        region_text = page.get_text("text", clip=title_clip)
        full_text = page.get_text("text")
        search_text = f"{region_text}\n{full_text}"

    for field, patterns in LABEL_PATTERNS.items():
        setattr(metadata, field, _find(search_text, patterns))

    filename = path.stem
    if not metadata.drawing_no:
        metadata.drawing_no = filename
    if not metadata.part_no:
        metadata.part_no = metadata.drawing_no

    units_match = re.search(r"\b(INCH(?:ES)?|IMPERIAL|MM|MILLIMETERS?|METRIC)\b", search_text, re.I)
    if units_match:
        token = units_match.group(1).upper()
        metadata.units = "MM" if token.startswith("M") else "INCH"
    return metadata
