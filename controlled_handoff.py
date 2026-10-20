"""Verified ForgeVault-to-EZ-FAIR inspection proposal."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from extractor_engine import extract_pdf_dimensions

def inspect_released_pdf(manifest, pdf_bytes):
    if manifest.get("schema") != "forgevault.released_drawing.v1":
        raise ValueError("unsupported handoff")
    if manifest.get("lifecycle") != "Released":
        raise ValueError("drawing is not released")
    required = ("record_id", "file_version_id", "release_package_number",
                "customer_part_number", "customer_revision", "internal_revision",
                "sha256", "byte_size", "filename", "version_number")
    if any(not manifest.get(k) for k in required):
        raise ValueError("missing controlled revision identity")
    if not isinstance(pdf_bytes, bytes) or not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("invalid PDF bytes")
    if len(pdf_bytes) != manifest["byte_size"] or hashlib.sha256(pdf_bytes).hexdigest() != manifest["sha256"]:
        raise ValueError("drawing digest or length mismatch")
    if not manifest["filename"].lower().endswith(".pdf"):
        raise ValueError("not a drawing PDF")
    with TemporaryDirectory() as folder:
        path = Path(folder) / "drawing.pdf"
        path.write_bytes(pdf_bytes)
        characteristics = extract_pdf_dimensions(path)
    if not characteristics:
        raise ValueError("no readable dimensions; manual inspection required")
    rows = [{"char_number": c.char_number, "reference_location": c.reference_location,
             "raw_text": c.raw_text, "nominal": c.nominal, "lsl": c.lsl,
             "usl": c.usl, "characteristic_type": c.type, "tooling": c.tooling,
             "notes": c.comments, "source_metadata": c.metadata} for c in characteristics]
    return {"schema": "ezfair.inspection_handoff.v1", "status": "review_required",
            "source_drawing": {k: manifest[k] for k in required},
            "characteristic_count": len(rows), "characteristics": rows}
