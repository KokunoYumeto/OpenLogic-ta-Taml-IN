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
from pypdf.generic import ArrayObject, NameObject


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--state", type=Path, default=Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN"))
    args = parser.parse_args()
    repo, state = args.repo.resolve(), args.state.resolve()
    assembly = load_evidence(repo, state, "COMPLETE-READER-ASSEMBLY-QA.json")
    layout = load_evidence(repo, state, "ALL-PAGE-LAYOUT-SCAN-QA.json")
    scope = assembly["scope"]
    require(assembly["result"] == "pass" and scope["frozen_units"] == 722, "The 722-unit source assembly is unverified")
    require(scope["main_source_units"] == 695 and scope["companion_source_units"] == 27, "Source partition changed")
    require(scope["duplicate_unit_loads"] == 0 and scope["unaccounted_units"] == 0, "Source units are duplicated or missing")
    require(layout["result"] == "scan-complete", "The original PDF page scan is incomplete")

    main_path = repo / "readers" / "tamil-complete.pdf"
    appendix_path = repo / "readers" / "tamil-source-companion.pdf"
    paths = {"main": main_path, "companion": appendix_path}
    inputs: dict[str, dict] = {}
    readers: dict[str, PdfReader] = {}
    for role, path in paths.items():
        require(path.is_file(), f"Missing validated {role} PDF: {path}")
        record = layout["volumes"][role]
        digest = sha256(path)
        require(digest == record["pdf_sha256"], f"Validated {role} PDF hash changed")
        reader = PdfReader(path)
        require(len(reader.pages) == record["pages"], f"Validated {role} PDF page count changed")
        readers[role] = reader
        inputs[role] = {"path": path.relative_to(repo).as_posix(), "bytes": path.stat().st_size, "sha256": digest, "pages": len(reader.pages)}

    main_pages = len(readers["main"].pages)
    writer = PdfWriter()
    writer.append(readers["main"], outline_item="முதன்மை நூல் — 695 மூல அலகுகள்", import_outline=True)
    writer.append(readers["companion"], outline_item="இணைப்பு: மாற்று மூலப்பிரிவுகள் — 27 அலகுகள்", import_outline=True)
    require(len(writer.pages) == main_pages + len(readers["companion"].pages), "PDF page merge lost pages")

    repaired: list[dict] = []
    for source_role, expected_name in (("main", appendix_path.name), ("companion", main_path.name)):
        source_start = 0 if source_role == "main" else main_pages
        source_pages = len(readers[source_role].pages)
        for local_page in range(source_pages):
            page = writer.pages[source_start + local_page]
            for annotation_reference in page.get("/Annots") or []:
                annotation = annotation_reference.get_object()
                action_reference = annotation.get("/A")
                if not action_reference:
                    continue
                action = action_reference.get_object()
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
                    named = readers["main"].named_destinations.get(str(remote))
                    require(named is not None, f"Unresolved main-reader named destination: {remote}")
                    destination_page = readers["main"].get_destination_page_number(named)
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
        "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
        "source_units": {"main": 695, "appendix": 27, "total": 722, "duplicated": 0},
        "inputs": inputs,
        "output": {"path": destination.relative_to(repo).as_posix(), "bytes": destination.stat().st_size, "sha256": sha256(destination), "pages": len(verify.pages)},
        "appendix_starts_at_page": main_pages + 1,
        "cross_volume_links_rewritten": len(repaired),
        "remaining_remote_pdf_actions": remote_actions,
        "local_pdf_actions": local_actions,
        "repaired_links": repaired,
    }
    state.mkdir(parents=True, exist_ok=True)
    (state / "COMPLETE-722-READER-RECEIPT.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
