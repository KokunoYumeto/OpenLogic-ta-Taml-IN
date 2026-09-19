from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
import subprocess


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN")
ASSET = REPO / "release" / "openlogic-ta-Taml-IN-cumulative-reader-203-units.tex"
RECEIPT = STATE / "CUMULATIVE-TEX-SOURCE.json"
QA_PATH = STATE / "CUMULATIVE-TEX-SOURCE-QA.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
artifact = ASSET.read_bytes()
text = artifact.decode("utf-8")
assert len(artifact) == receipt["asset"]["bytes"]
assert sha256(artifact) == receipt["asset"]["sha256"]

block_re = re.compile(
    r"\\begin\{filecontents\*\}\{([^}]+)\}\n(.*?)\\end\{filecontents\*\}\n",
    re.DOTALL,
)
blocks = {match.group(1): match.group(2).encode("utf-8") for match in block_re.finditer(text)}
assert len(blocks) == len(list(block_re.finditer(text)))
assert all("/" not in name and "\\" not in name and ".." not in name for name in blocks)

reader_rows = receipt["reader_units"]
driver_rows = receipt["structural_driver_files"]
assert len(reader_rows) == 203
assert len(driver_rows) == 3
assert {row["unit_id"] for row in driver_rows} == {"OLP-0275", "OLP-0280", "OLP-0289"}
all_rows = reader_rows + driver_rows
assert len({row["unit_id"] for row in all_rows}) == 206

verified_units = []
for row in all_rows:
    name = f"olt-unit-{row['unit_id']}.tex"
    assert name in blocks, name
    committed = subprocess.check_output(
        ["git", "show", f"{receipt['release_commit']}:{row['source_path']}"], cwd=REPO
    )
    assert blocks[name] == committed, row["unit_id"]
    assert sha256(committed) == row["translation_sha256"]
    verified_units.append(row["unit_id"])

assert not any(unit in verified_units for unit in [f"OLP-{number:04d}" for number in range(347, 353)])
assert len(re.findall(r"^% Reader-Unit: OLP-\d{4} ", text, re.MULTILINE)) == 203
assert len(re.findall(r"^% Structural-Driver: OLP-\d{4} ", text, re.MULTILINE)) == 3

required_embedded = {
    "olt-open-logic.sty",
    "olt-open-logic-locale.sty",
    "olt-open-logic-referencing.sty",
    "olt-open-logic-formulas.sty",
    "olt-open-logic-tokenize.sty",
    "olt-open-logic-selective.sty",
    "olt-bussproofs-extra.sty",
    "olt-ptolemaicastronomy.sty",
    "olt-open-logic-config.sty",
    "olt-open-logic-envs.sty",
    "olt-tamil-config.sty",
    "olt-tamil-pdf-math.sty",
    "olt-open-logic.bib",
    "olt-natbib-oup.bst",
}
assert required_embedded.issubset(blocks)
assert len([name for name in blocks if name.startswith("olt-note-")]) == 6
diagram_names = [name for name in blocks if name.startswith("olt-asset-")]
assert len(diagram_names) == receipt["completeness"]["embedded_diagram_sources"]

executable = text[text.rindex(r"\documentclass") :]
assert "../" not in executable and "..\\" not in executable
literal_inputs = re.findall(r"\\input\{([^}]+)\}", executable)
for target in literal_inputs:
    assert target in blocks, target
assert "\\bibliography{olt-open-logic}" in executable
assert "olt-open-logic.bib" in blocks
assert "\\bibliographystyle{olt-natbib-oup}" in executable
assert "olt-natbib-oup.bst" in blocks
assert len(re.findall(r"\\TAIncludePath\{content/", executable)) == 16

lower = artifact.lower()
assert b"c:\\users" not in lower

qa = {
    "schema": "openlogic-tamil-cumulative-tex-source-qa/1",
    "result": "pass",
    "release_commit": receipt["release_commit"],
    "asset": receipt["asset"],
    "scope": {
        "counted_reader_units": len(reader_rows),
        "structural_chapter_drivers": len(driver_rows),
        "exact_translation_blobs_verified": len(verified_units),
        "unaccepted_drafts_included": 0,
    },
    "embedded": {
        "filecontents_blocks": len(blocks),
        "project_support_files": len(required_embedded),
        "editorial_note_files": 6,
        "diagram_sources": len(diagram_names),
        "all_literal_executable_inputs_embedded": True,
        "bibliography_and_style_embedded": True,
    },
    "checks": {
        "asset_identity": True,
        "reader_unit_inventory": True,
        "structural_driver_inventory": True,
        "translation_payloads_match_release_commit": True,
        "project_local_input_completeness": True,
        "unaccepted_drafts_absent": True,
        "personal_path_absent": True,
        "pdf_rebuilt_for_packaging": False,
    },
}
QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(qa, ensure_ascii=False, indent=2))
