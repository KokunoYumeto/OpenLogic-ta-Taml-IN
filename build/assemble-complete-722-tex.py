#!/usr/bin/env python3
"""Assemble one editable, full-text TeX source from the two audited volumes.

This file contains every translated source body. The released PDF is assembled
from two independently compiled volumes; see README.md for that exact route.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
MAIN = BUILD / "tamil-complete-direct.tex"
COMPANION = BUILD / "tamil-source-companion-direct.tex"
OUTPUT = BUILD / "tamil-complete-722-direct.tex"
RECEIPT = BUILD / "tamil-complete-722-direct.qa.json"
BEGIN = r"\begin{document}"
END = r"\end{document}"
UNIT_BEGIN = re.compile(r"(?m)^% BEGIN SOURCE UNIT (OLP-\d{4}) ")
UNIT_END = re.compile(r"(?m)^% END SOURCE UNIT (OLP-\d{4})\s*$")
SEGMENT = re.compile(r"(?m)^% SEGMENT (OLP-\d{4}-S\d+)\s*$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parts(text: str) -> tuple[str, str, str]:
    require(text.count(BEGIN) == 1 and text.count(END) == 1, "Expected one document body")
    preamble, rest = text.split(BEGIN, 1)
    body, ending = rest.rsplit(r"\nocite{", 1)
    tail = r"\nocite{" + ending
    require(tail.count(r"\bibliographystyle{") == 1 and tail.rstrip().endswith(END),
            "Expected one final bibliography")
    return preamble, body, tail


def unit_ids(text: str) -> list[str]:
    starts, ends = UNIT_BEGIN.findall(text), UNIT_END.findall(text)
    require(len(starts) == len(ends) and set(starts) == set(ends),
            "Source-unit begin/end markers disagree")
    require(len(starts) == len(set(starts)), "Duplicate source-unit marker")
    return starts


main_bytes, companion_bytes = MAIN.read_bytes(), COMPANION.read_bytes()
main = main_bytes.decode("utf-8").replace("\r\n", "\n")
companion = companion_bytes.decode("utf-8").replace("\r\n", "\n")
main_preamble, main_body, main_tail = parts(main)
companion_preamble, companion_body, companion_tail = parts(companion)
main_units, companion_units = unit_ids(main_body), unit_ids(companion_body)
require(len(main_units) == 695 and len(companion_units) == 27, "Component unit count changed")
require(set(main_units).isdisjoint(companion_units), "The components repeat source units")
require(len(SEGMENT.findall(main_body)) == 2100 and len(SEGMENT.findall(companion_body)) == 142,
        "Aligned-segment count changed")

# The companion's volume-specific label imports are unnecessary in the one-file
# source. Its driver commands still need their full definitions before the body.
helper_start = companion_preamble.index(r"\makeatletter")
companion_helpers = companion_preamble[helper_start:]
require(companion_helpers.count(r"\NewDocumentCommand\TADriverImport") == 1,
        "Companion driver definitions changed")
require(r"\externaldocument" not in companion_helpers, "External label import leaked")
main_preamble = main_preamble.replace(
    "\\hypersetup{pdftitle={திறந்த தருக்கவியல் — தமிழ் பதிப்பு}",
    "\\hypersetup{pdftitle={திறந்த தருக்கவியல் — முழு 722 அலகுத் தமிழ்ப் பதிப்பு}", 1)
require("முழு 722 அலகுத் தமிழ்ப் பதிப்பு" in main_preamble, "PDF title update failed")

main_link = r"\href{tamil-source-companion.pdf}{இணை வாசிப்பு நூலைத் திறக்க}"
companion_link = r"\href{tamil-complete.pdf}{முதன்மை வாசிப்பு நூலைத் திறக்க}"
require(main_body.count(main_link) == 1 and companion_body.count(companion_link) == 1,
        "Volume navigation changed")
main_body = main_body.replace(main_link,
    r"\hyperlink{ta-complete-appendix}{இணை வாசிப்பு நூலைத் திறக்க}")
companion_body = companion_body.replace(companion_link,
    r"\hyperlink{ta-complete-main}{முதன்மை வாசிப்பு நூலைத் திறக்க}")

# One contents list is enough in a bound document. This removes only the
# companion's repeated document-level table, never a source-unit body.
second_contents = re.compile(
    r"\\clearpage\s*\\begingroup\s*\\sloppy\s*"
    r"\\renewcommand\{\\cftsectionfont\}\{\\small\}\s*"
    r"\\tableofcontents\*\s*\\endgroup\s*")
companion_body, count = second_contents.subn("\\\\clearpage\n", companion_body, count=1)
require(count == 1, "Companion contents block changed")

header = (
    "% ஒரே கோப்பில் 722 மூல அலகுகளின் முழு திருத்தத்தக்க தமிழ்ப் பாடப்பொருள்.\n"
    "% 695 முதன்மை அலகுகளும் 27 பெயரிடப்பட்ட இணை அலகுகளும் உள்ளன.\n"
    "% சரியான வெளியீட்டு PDF இரண்டு தொகுதிகளின் கட்டமைப்பால் உருவாகிறது; README பார்க்கவும்.\n"
    "% XeLaTeX, மூல ZIP இன் upstream/translation ஆதாரங்கள், எழுத்துருக்கள் தேவை.\n"
)
combined = (
    header + main_preamble.rstrip() + "\n\n" + companion_helpers.rstrip() + "\n"
    + BEGIN + "\n\\hypertarget{ta-complete-main}{}\n"
    + main_body.rstrip() + "\n\n\\clearpage\n\\appendix\n"
    + "\\hypertarget{ta-complete-appendix}{}\n"
    + companion_body.rstrip() + "\n\n" + main_tail.rstrip() + "\n"
)
combined_units = unit_ids(combined)
require(len(combined_units) == 722 and set(combined_units) == set(main_units + companion_units),
        "Cumulative source is not the same 722 units")
require(main_body.rstrip() in combined and companion_body.rstrip() in combined,
        "A translated component body was changed in assembly")
segments = SEGMENT.findall(combined)
require(len(segments) == 2242 and len(set(segments)) == 2242,
        "Cumulative source has missing or duplicated aligned segments")
require(combined.count(BEGIN) == 1 and combined.count(END) == 1,
        "Cumulative source has multiple documents")

output_bytes = combined.encode("utf-8")
OUTPUT.write_bytes(output_bytes)
receipt = {
    "schema": "openlogic-tamil-complete-722-direct-tex/1",
    "status": "source-assembled",
    "output": {"path": OUTPUT.relative_to(ROOT).as_posix(), "bytes": len(output_bytes),
               "sha256": digest(output_bytes)},
    "inputs": [
        {"path": MAIN.relative_to(ROOT).as_posix(), "bytes": len(main_bytes),
         "sha256": digest(main_bytes), "units": 695},
        {"path": COMPANION.relative_to(ROOT).as_posix(), "bytes": len(companion_bytes),
         "sha256": digest(companion_bytes), "units": 27},
    ],
    "source_units": 722,
    "unaltered_source_unit_blocks": 722,
    "aligned_segment_markers": 2242,
    "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
    "released_reader_build": "Guarded component builds, then assemble-complete-722-reader.py",
}
RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, ensure_ascii=False))
