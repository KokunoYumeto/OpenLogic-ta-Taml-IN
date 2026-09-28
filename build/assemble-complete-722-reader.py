#!/usr/bin/env python3
"""Bind the validated 695-unit main PDF and 27-unit appendix into one reader.

The source TeX masters remain the editable authority. This operation preserves
their already-inspected PDF pages and turns cross-volume PDF links into local
links within the assembled, 722-unit reader.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, Fit, NameObject


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_evidence(repo: Path, state: Path, name: str) -> dict:
    path = state / name
    if not path.is_file():
        path = repo / "evidence" / name
    require(path.is_file(), f"Missing reader validation: {name}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_pdf(repo: Path, value: Path | None, default: str) -> Path:
    path = value or Path(default)
    return (path if path.is_absolute() else repo / path).resolve()


def check_current_build(repo: Path, path: Path, master: str, receipt_name: str) -> None:
    receipt_path = repo / "build" / receipt_name
    require(receipt_path.is_file(), f"Fresh build receipt missing: {receipt_path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
    require(receipt.get("status") == "built" and receipt.get("master") == master,
            f"Fresh build failed or came from another master: {master}")
    passes = receipt.get("passes", [])
    require(len(passes) >= 3 and all(row.get("exit_code") == 0 for row in passes),
            f"Fresh build lacks three successful passes: {master}")
    started = datetime.fromisoformat(receipt["started_utc"].replace("Z", "+00:00")).timestamp()
    require(path.stat().st_mtime >= started - 2,
            f"PDF predates its current build receipt: {path}")


def named_page(reader: PdfReader, destinations: dict, name: object) -> tuple[int, ArrayObject]:
    key = str(name)
    named = destinations.get(key)
    if named is None and key.startswith("/"):
        named = destinations.get(key[1:])
    require(named is not None, f"Unresolved component-local named destination: {name}")
    page_number = reader.get_destination_page_number(named)
    require(page_number is not None, f"Named destination has no source page: {name}")
    return page_number, named.dest_array


def append_outlines(writer: PdfWriter, reader: PdfReader, items: list,
                    parent: object, offset: int, records: list[dict]) -> None:
    latest = None
    for item in items:
        if isinstance(item, list):
            require(latest is not None, "Outline children have no parent")
            append_outlines(writer, reader, item, latest, offset, records)
            continue
        page = reader.get_destination_page_number(item)
        require(page is not None and 0 <= page < len(reader.pages),
                f"Original outline has no local page: {item}")
        flags = int(item.get("/F", 0))
        color_array = item.get("/C")
        color = tuple(float(value) for value in color_array) if color_array else None
        count = item.get("/Count")
        latest = writer.add_outline_item(
            item.title, offset + page, parent=parent, color=color,
            bold=bool(flags & 2), italic=bool(flags & 1), fit=Fit.fit(),
            is_open=count is None or int(count) >= 0,
        )
        records.append({"title": item.title, "source_page": page + 1,
                        "target_page": offset + page + 1})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--state", type=Path, help="Receipt directory; defaults to build/ in a fresh source ZIP")
    parser.add_argument("--main-pdf", type=Path, help="Freshly built main PDF; defaults to build/tamil-complete.pdf")
    parser.add_argument("--companion-pdf", type=Path, help="Freshly built companion PDF; defaults to build/tamil-source-companion.pdf")
    parser.add_argument("--validation", choices=("current-build", "release-pinned"), default="current-build")
    args = parser.parse_args()
    repo = args.repo.resolve()
    state = (args.state or repo / "build").resolve()
    assembly = load_evidence(repo, state, "COMPLETE-READER-ASSEMBLY-QA.json")
    layout = load_evidence(repo, state, "ALL-PAGE-LAYOUT-SCAN-QA.json")
    scope = assembly["scope"]
    require(assembly["result"] == "pass" and scope["frozen_units"] == 722, "The 722-unit source assembly is unverified")
    require(scope["main_source_units"] == 695 and scope["companion_source_units"] == 27, "Source partition changed")
    require(scope["duplicate_unit_loads"] == 0 and scope["unaccounted_units"] == 0, "Source units are duplicated or missing")
    require(layout["result"] == "scan-complete", "Reference PDF page scan is incomplete")

    main_path = resolve_pdf(repo, args.main_pdf,
                            "readers/tamil-complete.pdf" if args.validation == "release-pinned" else "build/tamil-complete.pdf")
    appendix_path = resolve_pdf(repo, args.companion_pdf,
                                "readers/tamil-source-companion.pdf" if args.validation == "release-pinned" else "build/tamil-source-companion.pdf")
    paths = {"main": main_path, "companion": appendix_path}
    inputs: dict[str, dict] = {}
    readers: dict[str, PdfReader] = {}
    for role, path in paths.items():
        require(path.is_file(), f"Missing validated {role} PDF: {path}")
        record = layout["volumes"][role]
        digest = sha256(path)
        if args.validation == "release-pinned":
            require(digest == record["pdf_sha256"], f"Validated {role} PDF hash changed")
        else:
            master, receipt_name = (("tamil-complete.tex", "TEX-COMPLETE-RECEIPT.json") if role == "main"
                                    else ("tamil-source-companion.tex", "TEX-COMPANION-RECEIPT.json"))
            check_current_build(repo, path, master, receipt_name)
        reader = PdfReader(path)
        require(len(reader.pages) == record["pages"], f"Validated {role} PDF page count changed")
        readers[role] = reader
        inputs[role] = {"path": path.relative_to(repo).as_posix() if path.is_relative_to(repo) else str(path),
                        "bytes": path.stat().st_size, "sha256": digest, "pages": len(reader.pages)}
    destinations_by_role = {role: reader.named_destinations for role, reader in readers.items()}

    main_pages = len(readers["main"].pages)
    writer = PdfWriter()
    writer.append(readers["main"], import_outline=False)
    writer.append(readers["companion"], import_outline=False)
    require(len(writer.pages) == main_pages + len(readers["companion"].pages), "PDF page merge lost pages")
    outline_records: list[dict] = []
    main_parent = writer.add_outline_item("முதன்மை நூல் — 695 மூல அலகுகள்", 0)
    append_outlines(writer, readers["main"], readers["main"].outline,
                    main_parent, 0, outline_records)
    companion_parent = writer.add_outline_item("இணைப்பு: மாற்று மூலப்பிரிவுகள் — 27 அலகுகள்", main_pages)
    append_outlines(writer, readers["companion"], readers["companion"].outline,
                    companion_parent, main_pages, outline_records)

    repaired: list[dict] = []
    local_named_rewritten: list[dict] = []
    for source_role, expected_name in (("main", appendix_path.name), ("companion", main_path.name)):
        source_start = 0 if source_role == "main" else main_pages
        source_pages = len(readers[source_role].pages)
        for local_page in range(source_pages):
            page = writer.pages[source_start + local_page]
            for annotation_reference in page.get("/Annots") or []:
                annotation = annotation_reference.get_object()
                action_reference = annotation.get("/A")
                if not action_reference and annotation.get("/Dest") is not None:
                    destination = annotation.get("/Dest")
                    if not isinstance(destination, ArrayObject):
                        local_target, original_array = named_page(
                            readers[source_role], destinations_by_role[source_role], destination)
                        target = source_start + local_target
                        annotation[NameObject("/Dest")] = ArrayObject(
                            [writer.pages[target].indirect_reference, *original_array[1:]])
                        local_named_rewritten.append({"source_volume": source_role,
                                                      "source_page": local_page + 1,
                                                      "name": str(destination), "target_page": target + 1})
                if not action_reference:
                    continue
                action = action_reference.get_object()
                if action.get("/S") == "/GoTo" and not isinstance(action.get("/D"), ArrayObject):
                    destination = action.get("/D")
                    local_target, original_array = named_page(
                        readers[source_role], destinations_by_role[source_role], destination)
                    target = source_start + local_target
                    action[NameObject("/D")] = ArrayObject(
                        [writer.pages[target].indirect_reference, *original_array[1:]])
                    local_named_rewritten.append({"source_volume": source_role,
                                                  "source_page": local_page + 1,
                                                  "name": str(destination), "target_page": target + 1})
                    continue
                if action.get("/S") != "/GoToR":
                    continue
                require(str(action.get("/F")) == expected_name, f"Unexpected cross-volume PDF target: {action.get('/F')}")
                remote = action.get("/D")
                if source_role == "main":
                    require(isinstance(remote, ArrayObject) and int(remote[0]) == 0, "Main appendix link has an unexpected destination")
                    destination_page = main_pages
                elif isinstance(remote, ArrayObject):
                    require(int(remote[0]) == 0, "Companion first-page link has an unexpected destination")
                    destination_page = 0
                else:
                    destination_page, _ = named_page(
                        readers["main"], destinations_by_role["main"], remote)
                require(0 <= destination_page < len(writer.pages), "Rewritten PDF link targets a missing page")
                action[NameObject("/S")] = NameObject("/GoTo")
                action[NameObject("/D")] = ArrayObject([writer.pages[destination_page].indirect_reference, NameObject("/Fit")])
                action.pop(NameObject("/F"), None)
                action.pop(NameObject("/NewWindow"), None)
                repaired.append({"source_volume": source_role, "source_page": local_page + 1, "target_page": destination_page + 1})

    require(len([item for item in repaired if item["source_volume"] == "main"]) == 2, "Main-to-appendix link count changed")
    require(len([item for item in repaired if item["source_volume"] == "companion"]) == 24, "Appendix-to-main link count changed")
    writer.add_metadata({
        "/Title": "திறந்த தருக்கவியல் — முழுத் தமிழ்ப் பதிப்பு (722 மூல அலகுகள்)",
        "/Author": "Open Logic Project; தமிழ் மொழிபெயர்ப்புத் திட்டம்",
        "/Subject": "695 முதன்மை அலகுகளும் 27 மாற்று மூலப்பிரிவு அலகுகளும் கொண்ட இந்தியத் தமிழ்ப் பதிப்பு",
        "/Keywords": "Open Logic; Tamil; ta-Taml-IN; 722 source units; CC BY 4.0",
    })
    destination = repo / "readers" / "openlogic-ta-Taml-IN-complete-722.pdf"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        writer.write(output)

    verify = PdfReader(destination)
    require(len(verify.pages) == len(writer.pages), "Written PDF page count changed")
    require("722" in str(verify.metadata.title), "Combined-reader title metadata is missing")
    remote_actions = 0
    local_actions = 0
    for page in verify.pages:
        for annotation_reference in page.get("/Annots") or []:
            action_reference = annotation_reference.get_object().get("/A")
            if not action_reference:
                continue
            action = action_reference.get_object()
            remote_actions += action.get("/S") == "/GoToR"
            local_actions += action.get("/S") == "/GoTo"
    require(remote_actions == 0 and local_actions >= len(repaired), "Cross-volume links did not become local PDF links")
    appendix_text = subprocess.run(
        ["pdftotext", "-f", str(main_pages + 1), "-l", str(main_pages + 1), "-enc", "UTF-8", str(destination), "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(appendix_text.returncode == 0 and "மூல மாற்று வடிவங்களும்" in appendix_text.stdout.decode("utf-8"), "Appendix title page is missing")

    receipt = {
        "schema": "openlogic-tamil-722-reader-assembly/1",
        "assembled_utc": datetime.now(timezone.utc).isoformat(),
        "status": "assembled-awaiting-visual-qa",
        "validation_mode": args.validation,
        "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
        "source_units": {"main": 695, "appendix": 27, "total": 722, "duplicated": 0},
        "inputs": inputs,
        "output": {"path": destination.relative_to(repo).as_posix(), "bytes": destination.stat().st_size, "sha256": sha256(destination), "pages": len(verify.pages)},
        "appendix_starts_at_page": main_pages + 1,
        "cross_volume_links_rewritten": len(repaired),
        "component_local_named_links_rewritten": len(local_named_rewritten),
        "component_outline_entries_rebuilt": len(outline_records),
        "component_outline_samples": [
            row for row in outline_records if row["title"] in {
                "முதல்தரத் தருக்கத்தின் மாற்று வடிவங்கள்", "கூற்றுத் தருக்கமும் இரண்டாம்தரத் தருக்கமும்"}
        ],
        "component_local_named_link_samples": [
            row for row in local_named_rewritten if row["name"] in
            {"chapter*.4", "chapter*.205", "section*.206", "section*.244", "section*.271"}
            and row["source_volume"] == "companion"
        ],
        "remaining_remote_pdf_actions": remote_actions,
        "local_pdf_actions": local_actions,
        "repaired_links": repaired,
    }
    state.mkdir(parents=True, exist_ok=True)
    (state / "COMPLETE-722-READER-RECEIPT.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
