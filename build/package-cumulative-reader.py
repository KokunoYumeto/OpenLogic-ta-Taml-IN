from __future__ import annotations

from pathlib import Path
import hashlib
import json

from pypdf import PdfReader, PdfWriter


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN")
OUTPUT = REPO / "readers" / "openlogic-ta-Taml-IN-cumulative-reader-203-units.pdf"

SECTIONS = [
    {
        "title": "கணங்கள், தொடர்புகள், சார்புகள் மற்றும் எண்கணிதக் கட்டமைப்புகள்",
        "qa": "SFR-RENDER-QA.json",
        "units": 51,
    },
    {
        "title": "நிறுவல் முறைமைகள்: தொடர்கணிதம், இயற்கை வருவித்தல், அட்டவணை மரங்கள்",
        "qa": "PROOF-SYSTEMS-TABLEAUX-RENDER-QA.json",
        "units": 49,
    },
    {
        "title": "அடிகோள் வருவித்தல்",
        "qa": "AXIOMATIC-DEDUCTION-RENDER-QA.json",
        "units": 14,
    },
    {
        "title": "கணிப்புத்தன்மை",
        "qa": "COMPUTABILITY-RENDER-QA.json",
        "units": 44,
    },
    {
        "title": "டியூரிங் பொறிகள்",
        "qa": "TURING-MACHINES-RENDER-QA.json",
        "units": 22,
    },
    {
        "title": "முழுமையின்மையும் எண்கணிதமாக்கலும்",
        "qa": "INCOMPLETENESS-ARITHMETIZATION-RENDER-QA.json",
        "units": 12,
    },
    {
        "title": "ராபின்சன் Q இல் பிரதிநிதித்துவப்படுத்தல்",
        "qa": "REPRESENTABILITY-IN-Q-RENDER-QA.json",
        "units": 11,
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


writer = PdfWriter()
receipt_sections = []
page_cursor = 1
for section in SECTIONS:
    qa_path = STATE / section["qa"]
    qa = json.loads(qa_path.read_text(encoding="utf-8-sig"))
    assert qa["result"] == "pass", qa_path
    qa_units = qa["scope"].get("reader_units", qa["scope"].get("completed_units"))
    assert qa_units == section["units"], qa_path
    source = REPO / qa["pdf"]["path"]
    assert source.stat().st_size == qa["pdf"]["bytes"], source
    assert sha256(source) == qa["pdf"]["sha256"], source
    reader = PdfReader(source)
    pages = len(reader.pages)
    assert pages == qa["pdf"]["pages"], source
    writer.append(source, outline_item=section["title"], import_outline=True)
    receipt_sections.append(
        {
            "title": section["title"],
            "source_path": source.relative_to(REPO).as_posix(),
            "source_bytes": source.stat().st_size,
            "source_sha256": sha256(source),
            "units": section["units"],
            "pages": pages,
            "first_cumulative_page": page_cursor,
            "last_cumulative_page": page_cursor + pages - 1,
            "source_qa": section["qa"],
            "source_qa_sha256": sha256(qa_path),
        }
    )
    page_cursor += pages

assert sum(section["units"] for section in SECTIONS) == 203
assert page_cursor - 1 == sum(section["pages"] for section in receipt_sections)
writer.add_metadata(
    {
        "/Title": "OpenLogic தமிழ் — 203 அலகுகளின் திரட்டப்பட்ட வாசிப்புப் பதிப்பு",
        "/Author": "OpenLogic Tamil Translation Project",
        "/Subject": "Seven accepted India-standard Tamil readers, combined in frozen-source order",
        "/Creator": "OpenLogic Tamil deterministic cumulative-reader assembler",
    }
)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open("wb") as stream:
    writer.write(stream)

reopened = PdfReader(OUTPUT)
assert len(reopened.pages) == page_cursor - 1
assert reopened.metadata.title == "OpenLogic தமிழ் — 203 அலகுகளின் திரட்டப்பட்ட வாசிப்புப் பதிப்பு"
receipt = {
    "schema": "openlogic-tamil-cumulative-reader-assembly/1",
    "language": "ta-Taml-IN",
    "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
    "scope": {
        "accepted_distinct_units": 203,
        "component_readers": len(SECTIONS),
        "pages": len(reopened.pages),
        "order": "frozen-source order with accepted gaps retained",
    },
    "assembly": "Lossless PDF page concatenation; accepted component PDFs were not rebuilt or changed.",
    "sections": receipt_sections,
    "output": {
        "path": OUTPUT.relative_to(REPO).as_posix(),
        "bytes": OUTPUT.stat().st_size,
        "sha256": sha256(OUTPUT),
    },
}
receipt_path = STATE / "CUMULATIVE-READER-ASSEMBLY.json"
receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(receipt["output"], ensure_ascii=False))
