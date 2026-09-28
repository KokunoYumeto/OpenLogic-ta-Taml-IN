#!/usr/bin/env python3
"""Stage the five ordered complete-edition release files after exact QA."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN")
DEST = REPO / "release" / "complete-assets"
ASSETS = [
    ("01-openlogic-ta-Taml-IN-complete.pdf", "readers/tamil-complete.pdf"),
    ("02-openlogic-ta-Taml-IN-complete.tex", "build/tamil-complete-direct.tex"),
    ("03-openlogic-ta-Taml-IN-complete-source.zip", "release/openlogic-ta-Taml-IN-complete-source.zip"),
    ("04-openlogic-ta-Taml-IN-source-companion.pdf", "readers/tamil-source-companion.pdf"),
    ("05-openlogic-ta-Taml-IN-source-companion.tex", "build/tamil-source-companion-direct.tex"),
]


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def read_state(name: str) -> dict:
    return json.loads((STATE / name).read_text(encoding="utf-8"))


def check_file(path: Path, expected: dict) -> None:
    if not path.is_file() or path.stat().st_size != expected["bytes"] or digest(path) != expected["sha256"]:
        raise RuntimeError(f"Exact artifact identity failed: {path}")


direct = read_state("COMPLETE-DIRECT-TEX-QA.json")
equivalence = read_state("DIRECT-RENDER-EQUIVALENCE-QA.json")
layout = read_state("ALL-PAGE-LAYOUT-SCAN-QA.json")
source_package = read_state("SOURCE-PACKAGE-RECEIPT.json")
if direct["result"] != "pass" or direct["aligned_segment_markers"] != 2242:
    raise RuntimeError("Full direct-source assembly is not verified")
if equivalence["result"] != "pass-with-localized-raster-differences":
    raise RuntimeError("Direct and modular render comparison is not accepted")
if layout["result"] != "scan-complete":
    raise RuntimeError("All-page PDF layout scan is not complete")
if not (source_package["zip_readback_pass"] and source_package["entry_sha256_pass"]
        and source_package["source_target_units_verified"] == 722):
    raise RuntimeError("Complete source archive has not passed readback")

direct_rows = {row["volume"]: row for row in direct["artifacts"]}
for volume, reader_name, modular_receipt, direct_receipt in (
    ("main", "tamil-complete", "TEX-COMPLETE-RECEIPT.json", "TEX-COMPLETE-DIRECT-RECEIPT.json"),
    ("companion", "tamil-source-companion", "TEX-COMPANION-RECEIPT.json", "TEX-COMPANION-DIRECT-RECEIPT.json"),
):
    source_row = direct_rows[volume]
    check_file(REPO / source_row["path"], source_row)
    for source_name, receipt_name in ((source_row["master"], modular_receipt),
                                      (source_row["path"], direct_receipt)):
        build = read_state(receipt_name)
        source_file = REPO / source_name
        started = datetime.fromisoformat(build["started_utc"].replace("Z", "+00:00")).timestamp()
        if (build["status"] != "built" or len(build["passes"]) < 3
                or any(run["exit_code"] != 0 for run in build["passes"])
                or build["master"] != source_file.name or started < source_file.stat().st_mtime):
            raise RuntimeError(f"Guarded build receipt does not bind the current source: {source_name}")
    rendered = equivalence["volumes"][volume]
    if not (rendered["extracted_text_equal"] and rendered["page_count_equal"]
            and rendered["text_and_pagination_pass"]):
        raise RuntimeError(f"Direct render equivalence failed: {volume}")
    for row in rendered["files"]:
        check_file(REPO / row["path"], row)
    modular = rendered["files"][0]
    reader = REPO / "readers" / f"{reader_name}.pdf"
    check_file(reader, modular)
    if layout["volumes"][volume]["pdf_sha256"] != modular["sha256"]:
        raise RuntimeError(f"Page scan is stale: {volume}")

source_path = REPO / source_package["path"]
check_file(source_path, source_package)
with zipfile.ZipFile(source_path) as archive:
    listed = {row["path"]: row for row in json.loads(archive.read("SOURCE_PACKAGE_MANIFEST.json"))["files"]}
    for path in ("README.md", "README.en.md", "epub/README.md", "epub/readers.json",
                 "epub/package_epub.py", "build/stage-complete-release.py",
                 "build/tamil-complete.tex", "build/tamil-source-companion.tex",
                 "build/tamil-complete-direct.tex", "build/tamil-source-companion-direct.tex",
                 "evidence/translation-decisions/START_HERE.md",
                 "evidence/translation-decisions/TRANSLATION_DECISIONS_TAMIL.md",
                 "evidence/translation-decisions/DECISIONS.json.gz",
                 "evidence/translation-decisions/VARIANT_ASSESSMENT.md",
                 "evidence/translation-decisions/TRANSLATION_DECISION_QA.json"):
        check_file(REPO / path, listed[path])

draft = (STATE / "COMPLETE-RELEASE-PUBLIC-DRAFT.md").read_text(encoding="utf-8")
positions = [draft.index(name) for name, _ in ASSETS]
if positions != sorted(positions):
    raise RuntimeError("Tamil release links are out of asset order")

DEST.mkdir(parents=True, exist_ok=True)
inventory = []
for number, (name, relative) in enumerate(ASSETS, 1):
    source = REPO / relative
    target = DEST / name
    shutil.copyfile(source, target)
    if digest(source) != digest(target):
        raise RuntimeError(f"Release staging copy mismatch: {name}")
    inventory.append({
        "order": number, "name": name, "path": target.relative_to(REPO).as_posix(),
        "source_path": relative, "bytes": target.stat().st_size, "sha256": digest(target),
    })

receipt = {
    "schema": "openlogic-tamil-complete-release-assets/1",
    "staged_utc": datetime.now(timezone.utc).isoformat(),
    "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
    "status": "pass", "assets": inventory,
    "epub_status": "pending separate validation and release",
}
(STATE / "COMPLETE-RELEASE-ASSETS.json").write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "pass", "assets": [row["name"] for row in inventory]}, ensure_ascii=False))
