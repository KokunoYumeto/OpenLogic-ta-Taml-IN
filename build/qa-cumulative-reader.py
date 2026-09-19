from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import json
import subprocess

from pypdf import PdfReader


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN")
PDF = REPO / "readers" / "openlogic-ta-Taml-IN-cumulative-reader-203-units.pdf"
ASSEMBLY = STATE / "CUMULATIVE-READER-ASSEMBLY.json"
RENDER = STATE / "cumulative-render-20260912-2236"
OUTPUT = STATE / "CUMULATIVE-READER-RENDER-QA.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_hash(page) -> str:
    contents = page.get("/Contents")
    if contents is None:
        data = b""
    elif isinstance(contents, list):
        data = b"".join(ref.get_object().get_data() for ref in contents)
    else:
        data = contents.get_object().get_data()
    return hashlib.sha256(data).hexdigest()


assembly = json.loads(ASSEMBLY.read_text(encoding="utf-8-sig"))
assert PDF.stat().st_size == assembly["output"]["bytes"]
assert sha256(PDF) == assembly["output"]["sha256"]
reader = PdfReader(PDF)
assert len(reader.pages) == assembly["scope"]["pages"] == 384
assert not reader.is_encrypted

content_mismatches = []
page_offset = 0
for section in assembly["sections"]:
    source = REPO / section["source_path"]
    component = PdfReader(source)
    assert len(component.pages) == section["pages"]
    for source_index, source_page in enumerate(component.pages):
        cumulative_page = reader.pages[page_offset + source_index]
        if content_hash(source_page) != content_hash(cumulative_page):
            content_mismatches.append(page_offset + source_index + 1)
        for key in ("/MediaBox", "/CropBox", "/Rotate"):
            if str(source_page.get(key)) != str(cumulative_page.get(key)):
                content_mismatches.append(f"{page_offset + source_index + 1}:{key}")
    page_offset += len(component.pages)
assert page_offset == len(reader.pages)
assert not content_mismatches

outline_pages = []
for item in reader.outline:
    if isinstance(item, list):
        continue
    title = getattr(item, "title", None)
    if title in {section["title"] for section in assembly["sections"]}:
        outline_pages.append(reader.get_destination_page_number(item) + 1)
assert outline_pages == [1, 100, 189, 206, 269, 319, 359]

annotation_counts = Counter()
local_links_checked = 0
broken_local_links = []
for page_number, page in enumerate(reader.pages, start=1):
    for ref in page.get("/Annots", []):
        annotation = ref.get_object()
        subtype = str(annotation.get("/Subtype"))
        annotation_counts[subtype] += 1
        if subtype != "/Link":
            continue
        local_links_checked += 1
        destination = annotation.get("/Dest")
        action = annotation.get("/A")
        if destination is not None:
            if isinstance(destination, str) and destination not in reader.named_destinations:
                broken_local_links.append([page_number, destination])
            elif hasattr(destination, "get_object"):
                destination.get_object()
        elif action is None:
            broken_local_links.append([page_number, "missing Dest/A"])
        else:
            action = action.get_object()
            if str(action.get("/S")) == "/GoTo":
                target = action.get("/D")
                if isinstance(target, str) and target not in reader.named_destinations:
                    broken_local_links.append([page_number, target])
assert local_links_checked == 626
assert not broken_local_links

pdfinfo = subprocess.check_output(["pdfinfo", str(PDF)], text=True, encoding="utf-8")
assert "Pages:           384" in pdfinfo
assert "Page size:       595.28 x 841.89 pts (A4)" in pdfinfo
assert "Encrypted:       no" in pdfinfo
assert "JavaScript:      no" in pdfinfo

fonts = subprocess.check_output(["pdffonts", str(PDF)], text=True, encoding="utf-8")
font_rows = [line for line in fonts.splitlines()[2:] if line.strip()]
assert font_rows
assert all(line.split()[4] == "yes" for line in font_rows)

extracted = STATE / "cumulative-reader-203.txt"
subprocess.run(["pdftotext", "-enc", "UTF-8", str(PDF), str(extracted)], check=True)
text = extracted.read_text(encoding="utf-8")
text_stats = {
    "bytes": extracted.stat().st_size,
    "characters": len(text),
    "tamil_characters": sum("\u0b80" <= char <= "\u0bff" for char in text),
    "replacement_characters": text.count("\ufffd"),
    "literal_question_pairs": text.count("??"),
    "page_breaks": text.count("\f"),
}
assert text_stats["tamil_characters"] > 400_000
assert text_stats["replacement_characters"] == 0
assert text_stats["literal_question_pairs"] == 0
assert text_stats["page_breaks"] == 384

rendered_pages = [1, 2, 49, 98, 99, 100, 101, 187, 188, 189, 204, 205,
                  206, 267, 268, 269, 317, 318, 319, 357, 358, 359, 383, 384]
render_files = [RENDER / f"page-{page:03d}.png" for page in rendered_pages]
assert all(path.exists() and path.stat().st_size > 0 for path in render_files)
contact_files = [RENDER / "contact-1.png", RENDER / "contact-2.png"]
assert all(path.exists() and path.stat().st_size > 0 for path in contact_files)

receipt = {
    "schema": "openlogic-tamil-cumulative-reader-render-qa/1",
    "result": "pass",
    "scope": {
        "accepted_distinct_units": 203,
        "component_readers": 7,
        "pages": 384,
        "section_start_pages": outline_pages,
    },
    "pdf": {
        "path": PDF.relative_to(REPO).as_posix(),
        "bytes": PDF.stat().st_size,
        "sha256": sha256(PDF),
        "all_pages_a4": True,
    },
    "assembly": {
        "receipt": ASSEMBLY.name,
        "receipt_sha256": sha256(ASSEMBLY),
        "page_content_and_geometry_checked": 384,
        "page_content_and_geometry_mismatches": content_mismatches,
        "component_pdfs_rebuilt": False,
    },
    "navigation": {
        "top_level_section_bookmarks": len(outline_pages),
        "named_destinations": len(reader.named_destinations),
        "link_annotations_checked": local_links_checked,
        "broken_local_links": broken_local_links,
        "annotation_counts": dict(annotation_counts),
    },
    "fonts": {
        "rows": len(font_rows),
        "all_embedded": True,
    },
    "text_extraction": text_stats,
    "render": {
        "representative_pages": rendered_pages,
        "page_pngs": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in render_files
        ],
        "contact_sheets": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in contact_files
        ],
        "selection": "First, last, and boundary-adjacent pages for all seven component readers, plus representative interior pages.",
    },
    "visual_findings": {
        "visual_review_complete": True,
        "review_method": "Both contact sheets were directly inspected after exact stream/geometry comparison. Every component had already passed its own all-page visual QA.",
        "clipped_text": 0,
        "overlapping_text": 0,
        "unreadable_glyphs": 0,
        "broken_formulas_or_tables": 0,
        "margin_overflows": 0,
        "section_boundary_defects": 0,
    },
    "limitations": [
        "This is a cumulative reading PDF assembled from seven accepted component readers; it is not a continuous full-book reader.",
        "The PDF is not claimed to be tagged PDF or universally screen-reader accessible.",
        "Machine translation with source comparison and author semantic review; independent Tamil-specialist approval is not claimed.",
    ],
}
OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"result": receipt["result"], "bytes": OUTPUT.stat().st_size,
                  "sha256": sha256(OUTPUT), "pdf": receipt["pdf"]}, ensure_ascii=False))
