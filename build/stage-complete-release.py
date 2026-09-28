#!/usr/bin/env python3
"""Stage the single-reader 722-unit edition and its component sources after QA."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN")
DEST = REPO / "release" / "complete-722-assets"
ASSETS = [
    ("01-openlogic-ta-Taml-IN-complete-722.pdf", "readers/openlogic-ta-Taml-IN-complete-722.pdf"),
    ("02-openlogic-ta-Taml-IN-complete-722.epub", "readers/openlogic-ta-Taml-IN-complete-722.epub"),
    ("03-openlogic-ta-Taml-IN-complete-source.zip", "release/openlogic-ta-Taml-IN-complete-source.zip"),
    ("tamil-complete.pdf", "readers/tamil-complete.pdf"),
    ("openlogic-ta-Taml-IN-complete-main.epub", "readers/openlogic-ta-Taml-IN-complete-main.epub"),
    ("tamil-complete.tex", "build/tamil-complete-direct.tex"),
    ("tamil-source-companion.pdf", "readers/tamil-source-companion.pdf"),
    ("openlogic-ta-Taml-IN-complete-companion.epub", "readers/openlogic-ta-Taml-IN-complete-companion.epub"),
    ("tamil-source-companion.tex", "build/tamil-source-companion-direct.tex"),
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
                 "epub/package_epub.py", "epub/audit_epub.py", "epub/requirements.txt",
                 "build/assemble-complete-722-reader.py", "build/assemble-complete-722-epub.py",
                 "build/stage-complete-release.py",
                 "build/tamil-complete.tex", "build/tamil-source-companion.tex",
                 "build/tamil-complete-direct.tex", "build/tamil-source-companion-direct.tex",
                 "evidence/translation-decisions/START_HERE.md",
                 "evidence/translation-decisions/TRANSLATION_DECISIONS_TAMIL.md",
                 "evidence/translation-decisions/DECISIONS.json.gz",
                 "evidence/translation-decisions/VARIANT_ASSESSMENT.md",
                 "evidence/translation-decisions/TRANSLATION_DECISION_QA.json"):
        check_file(REPO / path, listed[path])
    for name in ("COMPLETE-722-VISUAL-QA.json", "EPUB-AUDIT-COMPLETE_722.json"):
        archive_path = f"evidence/{name}"
        check_file(STATE / name, listed[archive_path])
        if digest(STATE / name) != hashlib.sha256(archive.read(archive_path)).hexdigest():
            raise RuntimeError(f"Source archive evidence changed: {name}")

combined_pdf = read_state("COMPLETE-722-READER-RECEIPT.json")
visual = read_state("COMPLETE-722-VISUAL-QA.json")
if (combined_pdf["source_units"]["total"] != 722 or combined_pdf["remaining_remote_pdf_actions"] != 0
        or combined_pdf["cross_volume_links_rewritten"] != 26 or visual["status"] != "pass"):
    raise RuntimeError("Combined 722-unit PDF validation is incomplete")
check_file(REPO / combined_pdf["output"]["path"], combined_pdf["output"])
if visual["pdf"]["sha256"] != combined_pdf["output"]["sha256"]:
    raise RuntimeError("Combined 722-unit PDF visual check is stale")
for slug, expected_units in (("COMPLETE_MAIN", 695), ("COMPLETE_COMPANION", 27), ("COMPLETE_722", 722)):
    audit = read_state(f"EPUB-AUDIT-{slug}.json")
    if (audit["status"] != "pass" or audit["epubcheck"]["messages"] != 0
            or audit["source_coverage"]["exact_unit_ids"] != expected_units
            or not audit["reproducible_zip"]):
        raise RuntimeError(f"EPUB audit is incomplete: {slug}")
    check_file(Path(audit["epub"]["path"]), audit["epub"])

draft = (STATE / "COMPLETE-722-RELEASE-PUBLIC-DRAFT.md").read_text(encoding="utf-8")
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
    "schema": "openlogic-tamil-complete-722-release-assets/1",
    "staged_utc": datetime.now(timezone.utc).isoformat(),
    "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
    "status": "pass", "assets": inventory,
    "epub_status": "three independent EPUBCheck 5.3.0 audits pass",
}
(STATE / "COMPLETE-RELEASE-ASSETS.json").write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "pass", "assets": [row["name"] for row in inventory]}, ensure_ascii=False))
