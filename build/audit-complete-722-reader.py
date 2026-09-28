#!/usr/bin/env python3
"""Independently check every PDF page and component-local navigation target."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ArrayObject, IndirectObject


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--main-pdf", type=Path, default=Path("readers/tamil-complete.pdf"))
parser.add_argument("--companion-pdf", type=Path, default=Path("readers/tamil-source-companion.pdf"))
parser.add_argument("--combined-pdf", type=Path, default=Path("readers/openlogic-ta-Taml-IN-complete-722.pdf"))
args = parser.parse_args()
MAIN = (ROOT / args.main_pdf).resolve()
COMPANION = (ROOT / args.companion_pdf).resolve()
COMBINED = (ROOT / args.combined_pdf).resolve()
RECEIPT = ROOT / "build" / "complete-722-pdf-navigation-qa.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def page_index(reader: PdfReader) -> dict[tuple[int, int], int]:
    return {(page.indirect_reference.idnum, page.indirect_reference.generation): number
            for number, page in enumerate(reader.pages)}


def annotations(page: object) -> list:
    value = page.get("/Annots")
    if isinstance(value, IndirectObject):
        value = value.get_object()
    return value or []


def local_target(reader: PdfReader, index: dict[tuple[int, int], int],
                 destinations: dict, destination: object) -> int:
    if isinstance(destination, ArrayObject):
        first = destination[0]
        require(isinstance(first, IndirectObject), f"Local destination is not a page reference: {first}")
        target = index.get((first.idnum, first.generation))
        require(target is not None, f"Local destination page is missing: {first}")
        return target
    name = str(destination)
    named = destinations.get(name)
    if named is None and name.startswith("/"):
        named = destinations.get(name[1:])
    require(named is not None, f"Unknown source named destination: {name}")
    number = reader.get_destination_page_number(named)
    require(number is not None, f"Named destination has no page: {name}")
    return number


def outline_rows(reader: PdfReader, items: list, parent: tuple[int, ...] = ()) -> list[tuple[tuple[int, ...], str, int]]:
    rows = []
    latest = None
    sibling = 0
    for item in items:
        if isinstance(item, list):
            require(latest is not None, "Outline children have no parent")
            rows.extend(outline_rows(reader, item, latest))
            continue
        latest = (*parent, sibling)
        page = reader.get_destination_page_number(item)
        require(page is not None, f"Outline has no page: {item.title}")
        rows.append((latest, item.title, page))
        sibling += 1
    return rows


readers = {"main": PdfReader(MAIN), "companion": PdfReader(COMPANION)}
combined = PdfReader(COMBINED)
lengths = {role: len(reader.pages) for role, reader in readers.items()}
require(lengths == {"main": 1171, "companion": 56} and len(combined.pages) == 1227,
        "Component or combined page count changed")
indices = {role: page_index(reader) for role, reader in readers.items()}
combined_index = page_index(combined)
destinations = {role: reader.named_destinations for role, reader in readers.items()}
destinations["combined"] = combined.named_destinations
counts = {"page_streams_identical": 0, "local_links_checked": 0,
          "cross_volume_links_checked": 0, "external_actions_preserved": 0}
samples = {}

for role in ("main", "companion"):
    source_reader = readers[role]
    offset = 0 if role == "main" else lengths["main"]
    other_role = "companion" if role == "main" else "main"
    other_reader = readers[other_role]
    for local_page, source_page in enumerate(source_reader.pages):
        output_page = combined.pages[offset + local_page]
        require(source_page.mediabox == output_page.mediabox,
                f"Page geometry changed: {role} {local_page + 1}")
        source_contents = source_page.get_contents()
        output_contents = output_page.get_contents()
        require((source_contents.get_data() if source_contents else b"") ==
                (output_contents.get_data() if output_contents else b""),
                f"Page content stream changed: {role} {local_page + 1}")
        counts["page_streams_identical"] += 1
        source_annots = annotations(source_page)
        output_annots = annotations(output_page)
        require(len(source_annots) == len(output_annots),
                f"Annotation count changed: {role} {local_page + 1}")
        for source_ref, output_ref in zip(source_annots, output_annots):
            source, output = source_ref.get_object(), output_ref.get_object()
            source_action_ref, output_action_ref = source.get("/A"), output.get("/A")
            if not source_action_ref:
                continue
            source_action = source_action_ref.get_object()
            output_action = output_action_ref.get_object() if output_action_ref else {}
            kind = str(source_action.get("/S"))
            if kind == "/GoTo":
                expected = offset + local_target(source_reader, indices[role], destinations[role],
                                                 source_action.get("/D"))
                counts["local_links_checked"] += 1
            elif kind == "/GoToR":
                remote = source_action.get("/D")
                if isinstance(remote, ArrayObject):
                    require(int(remote[0]) == 0, "Unexpected remote page number")
                    expected = 0 if other_role == "main" else lengths["main"]
                else:
                    other_offset = 0 if other_role == "main" else lengths["main"]
                    expected = other_offset + local_target(other_reader, indices[other_role],
                                                           destinations[other_role], remote)
                counts["cross_volume_links_checked"] += 1
            else:
                require(str(output_action.get("/S")) == kind,
                        f"External action changed: {role} {local_page + 1}")
                counts["external_actions_preserved"] += 1
                continue
            require(str(output_action.get("/S")) == "/GoTo", "Local link was not preserved")
            actual = local_target(combined, combined_index, destinations["combined"],
                                  output_action.get("/D"))
            require(actual == expected,
                    f"Wrong target: {role} {local_page + 1}, {source_action.get('/D')}: "
                    f"expected {expected + 1}, found {actual + 1}")
            name = str(source_action.get("/D"))
            if role == "companion" and name in {
                    "chapter*.4", "chapter*.205", "section*.206", "section*.244", "section*.271"}:
                samples[name] = actual + 1

require(counts["local_links_checked"] >= 2797 and
        counts["cross_volume_links_checked"] == 26 and
        samples == {"chapter*.4": 1174, "chapter*.205": 1212,
                    "section*.206": 1213, "section*.244": 1218, "section*.271": 1225},
        "Full link coverage or known appendix TOC repairs are incomplete")
combined_outline = combined.outline
require(len(combined_outline) == 4 and isinstance(combined_outline[1], list) and
        isinstance(combined_outline[3], list), "Combined outline does not have two volume groups")
for role, group in (("main", combined_outline[1]), ("companion", combined_outline[3])):
    source_rows = outline_rows(readers[role], readers[role].outline)
    output_rows = outline_rows(combined, group)
    offset = 0 if role == "main" else lengths["main"]
    require(len(source_rows) == len(output_rows), f"Outline count changed: {role}")
    for (source_path, source_title, source_page), (output_path, output_title, output_page) in zip(source_rows, output_rows):
        require((source_path, source_title, source_page + offset) ==
                (output_path, output_title, output_page),
                f"Outline target or hierarchy changed: {role} {source_path} {source_title}")
    counts[f"{role}_outline_entries_checked"] = len(source_rows)
require(counts["main_outline_entries_checked"] + counts["companion_outline_entries_checked"] == 718,
        "Outline coverage changed")
receipt = {
    "schema": "openlogic-tamil-complete-722-pdf-navigation/1",
    "status": "pass",
    "source_pdf_sha256": {role: digest(path) for role, path in
                          (("main", MAIN), ("companion", COMPANION))},
    "combined_pdf": {"path": COMBINED.relative_to(ROOT).as_posix() if COMBINED.is_relative_to(ROOT) else str(COMBINED),
                     "bytes": COMBINED.stat().st_size, "sha256": digest(COMBINED)},
    "counts": counts,
    "repaired_appendix_toc_targets": samples,
}
RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, ensure_ascii=False))
