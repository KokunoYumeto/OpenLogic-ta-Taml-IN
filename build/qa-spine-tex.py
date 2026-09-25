from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
import subprocess


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN")
ASSET = REPO / "release" / "openlogic-ta-Taml-IN-set-theory-stages-ranks-7-units.tex"
RECEIPT = STATE / "SET-THEORY-SPINE-TEX-SOURCE.json"
QA_PATH = STATE / "SET-THEORY-SPINE-TEX-SOURCE-QA.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
artifact = ASSET.read_bytes()
text = artifact.decode("utf-8")
assert len(artifact) == receipt["asset"]["bytes"]
assert sha256(artifact) == receipt["asset"]["sha256"]
assert ASSET.name == receipt["asset"]["filename"]

block_re = re.compile(
    r"\\begin\{filecontents\*\}\{([^}]+)\}\n(.*?)\\end\{filecontents\*\}\n",
    re.DOTALL,
)
matches = list(block_re.finditer(text))
blocks = {match.group(1): match.group(2).encode("utf-8") for match in matches}
assert len(blocks) == len(matches) == 21
assert all("/" not in name and "\\" not in name and ".." not in name for name in blocks)

rows = receipt["reader_units"]
assert len(rows) == 7
assert {row["unit_id"] for row in rows} == {
    f"OLP-{number:04d}" for number in range(558, 565)
}
for row in rows:
    name = f"olt-spine-unit-{row['unit_id']}.tex"
    committed = subprocess.check_output(
        ["git", "show", f"{receipt['source_commit']}:{row['source_path']}"], cwd=REPO
    )
    assert blocks[name] == committed, row["unit_id"]
    assert sha256(committed) == row["translation_sha256"]

required_embedded = {
    "olt-spine-open-logic.sty",
    "olt-spine-open-logic-locale.sty",
    "olt-spine-open-logic-referencing.sty",
    "olt-spine-open-logic-formulas.sty",
    "olt-spine-open-logic-tokenize.sty",
    "olt-spine-open-logic-selective.sty",
    "olt-spine-bussproofs-extra.sty",
    "olt-spine-ptolemaicastronomy.sty",
    "olt-spine-open-logic-config.sty",
    "olt-spine-open-logic-envs.sty",
    "olt-spine-tamil-config.sty",
    "olt-spine-tamil-pdf-math.sty",
    "olt-spine-open-logic.bib",
    "olt-spine-natbib-oup.bst",
}
assert required_embedded.issubset(blocks)
replacements = {
    r"\olpath/locale/\ollangid/open-logic-locale.sty": "olt-spine-open-logic-locale.sty",
    r"\olpath/open-logic-locale.sty": "olt-spine-open-logic-locale.sty",
    r"\olpath/sty/open-logic-referencing.sty": "olt-spine-open-logic-referencing.sty",
    r"\olpath/sty/open-logic-formulas.sty": "olt-spine-open-logic-formulas.sty",
    r"\olpath/sty/open-logic-tokenize.sty": "olt-spine-open-logic-tokenize.sty",
    r"\olpath/sty/open-logic-selective.sty": "olt-spine-open-logic-selective.sty",
    r"\olpath/sty/bussproofs-extra.sty": "olt-spine-bussproofs-extra.sty",
    r"\olpath/sty/ptolemaicastronomy.sty": "olt-spine-ptolemaicastronomy.sty",
    r"\olpath/open-logic-config.sty": "olt-spine-open-logic-config.sty",
    r"\olpath/locale/\ollangid/open-logic-envs.sty": "olt-spine-open-logic-envs.sty",
    r"\olpath/open-logic-envs.sty": "olt-spine-open-logic-envs.sty",
}
assert len(receipt["support_files"]) == len(required_embedded) == 14
for row in receipt["support_files"]:
    source = subprocess.check_output(
        ["git", "show", f"{receipt['source_commit']}:{row['source_path']}"], cwd=REPO
    )
    assert sha256(source) == row["source_sha256"]
    expected = source
    if row["source_path"].endswith(".sty"):
        rewritten = source.decode("utf-8")
        for old, new in replacements.items():
            rewritten = rewritten.replace(old, new)
        expected = rewritten.encode("utf-8")
    assert blocks[row["embedded_name"]] == expected, row["source_path"]
    assert sha256(expected) == row["embedded_sha256"]

executable = text[text.rindex(r"\documentclass") :]
assert "../" not in executable and "..\\" not in executable
for target in re.findall(r"\\input\{([^}]+)\}", executable):
    assert target in blocks, target
assert r"\bibliography{olt-spine-open-logic}" in executable
assert r"\bibliographystyle{olt-spine-natbib-oup}" in executable
assert executable.count(r"\TAIncludePath{content/set-theory/spine/spine.tex}") == 1
assert len(re.findall(r"^% Reader-Unit: OLP-\d{4} ", text, re.MULTILINE)) == 7
assert "pdftitle={திறந்த தருக்கவியல் — படிநிலைகளும் தரநிலைகளும்}" in executable
assert "GPT-5.6 Sol" in executable
assert b"c:\\users" not in artifact.lower()

master = subprocess.check_output(
    ["git", "show", f"{receipt['source_commit']}:{receipt['reader_master']['source_path']}"],
    cwd=REPO,
)
assert sha256(master) == receipt["reader_master"]["source_sha256"]
assert sha256(executable.encode("utf-8")) == receipt["reader_master"]["assembled_executable_sha256"]
pdf = REPO / receipt["reader_pdf"]["path"]
assert pdf.stat().st_size == receipt["reader_pdf"]["bytes"]
assert sha256(pdf.read_bytes()) == receipt["reader_pdf"]["sha256"]

qa = {
    "schema": "openlogic-tamil-spine-tex-source-qa/1",
    "result": "pass",
    "source_commit": receipt["source_commit"],
    "asset": receipt["asset"],
    "scope": {
        "counted_reader_units": len(rows),
        "exact_translation_blobs_verified": len(rows),
        "unaccepted_drafts_included": 0,
    },
    "embedded": {
        "filecontents_blocks": len(blocks),
        "project_support_files": len(required_embedded),
        "all_literal_executable_inputs_embedded": True,
        "bibliography_and_style_embedded": True,
    },
    "checks": {
        "asset_identity": True,
        "reader_unit_inventory": True,
        "translation_payloads_match_source_commit": True,
        "project_local_input_completeness": True,
        "support_payloads_match_source_commit_or_declared_path_rewrites": True,
        "reader_master_identity": True,
        "accepted_pdf_identity_and_preservation": True,
        "unaccepted_drafts_absent": True,
        "personal_path_absent": True,
    },
}
QA_PATH.write_text(
    json.dumps(qa, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)
print(json.dumps(qa, ensure_ascii=False, indent=2))
