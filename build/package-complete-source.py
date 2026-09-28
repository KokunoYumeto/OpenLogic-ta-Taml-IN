#!/usr/bin/env python3
"""Create a deterministic editable source archive for the complete Tamil edition."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN")
DESTINATION = REPO / "release" / "openlogic-ta-Taml-IN-complete-source.zip"
SOURCE_REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"
ZIP_TIME = (2026, 9, 28, 0, 0, 0)
SUPPORT = [
    "build/tamil-complete.tex", "build/tamil-source-companion.tex",
    "build/tamil-complete-direct.tex", "build/tamil-source-companion-direct.tex",
    "build/tamil-complete-722-direct.tex", "build/tamil-complete-722-direct.qa.json",
    "build/build-tamil.ps1", "build/build-epub-html.ps1",
    "build/assemble-complete-722-reader.py", "build/audit-complete-722-reader.py",
    "build/assemble-complete-722-tex.py", "build/assemble-complete-722-epub.py",
    "build/complete-722-pdf-navigation-qa.json",
    "build/package-complete-source.py", "build/stage-complete-release.py",
    "epub/readers.json", "epub/package_epub.py", "epub/audit_epub.py", "epub/requirements.txt", "epub/README.md",
    "README.md", "README.en.md", "LICENSE.md", "NOTICE.md",
    "evidence/source-corrections.json",
    "evidence/translation-decisions/START_HERE.md",
    "evidence/translation-decisions/TRANSLATION_DECISIONS_TAMIL.md",
    "evidence/translation-decisions/TRANSLATION_DECISIONS_FULL.md",
    "evidence/translation-decisions/PRIORITY_REVIEW.md",
    "evidence/translation-decisions/DECISION_OCCURRENCES.csv",
    "evidence/translation-decisions/DECISIONS.json",
    "evidence/translation-decisions/DECISIONS.json.gz",
    "evidence/translation-decisions/translation-decision.schema.json",
    "evidence/translation-decisions/VARIANT_ASSESSMENT.md",
    "evidence/translation-decisions/VARIANT_ASSESSMENT.en.md",
    "evidence/translation-decisions/TRANSLATION_DECISION_QA.json",
]
STATE_EVIDENCE = [
    "SOURCE_MANIFEST.jsonl", "SOURCE_VERIFICATION.json", "SOURCE_CORRECTIONS.json",
    "TRANSLATION_DECISIONS.jsonl", "FINAL-CORPUS-SCOPE-QA.json",
    "COMPLETE-READER-ASSEMBLY-QA.json", "COMPLETE-DIRECT-TEX-QA.json",
    "DIRECT-RENDER-EQUIVALENCE-QA.json", "ALL-PAGE-LAYOUT-SCAN-QA.json",
    "ALL-PAGE-VISUAL-REVIEW.md",
    "COMPLETE-722-READER-RECEIPT.json", "COMPLETE-722-VISUAL-QA.json",
    "COMPLETE-722-VISUAL-QA-V2.json", "TEX-COMPLETE-722-DIRECT.json",
    "EPUB-AUDIT-COMPLETE_MAIN.json", "EPUB-AUDIT-COMPLETE_COMPANION.json",
    "EPUB-AUDIT-COMPLETE_722.json",
]


def hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


files: dict[str, Path] = {}
for directory in ("translation", "upstream", "illustrations"):
    root = REPO / directory
    for path in root.rglob("*"):
        if path.is_file() and not any(part in {".git", ".github", "__pycache__"} for part in path.relative_to(root).parts):
            files[path.relative_to(REPO).as_posix()] = path
for name in SUPPORT:
    path = REPO / name
    if not path.is_file():
        raise RuntimeError(f"Missing complete-edition source dependency: {name}")
    files[name] = path
for name in STATE_EVIDENCE:
    path = STATE / name
    if not path.is_file():
        raise RuntimeError(f"Missing complete-edition evidence: {name}")
    files[f"evidence/{name}"] = path

manifest = {
    "schema": "openlogic-tamil-complete-source-package/1",
    "source_revision": SOURCE_REVISION,
    "locale": "ta-Taml-IN",
    "scope": "உறையவைக்கப்பட்ட 722 உள்ளடக்க அலகுகள்: ஒரே வாசிப்பு நூலின் முதன்மைப் பகுதியில் 695, மாற்று மூலப்பிரிவு இணைப்பில் 27",
    "editable_masters": ["build/tamil-complete-722-direct.tex", "build/tamil-complete-direct.tex", "build/tamil-source-companion-direct.tex"],
    "build_dependencies": "இத்தொகுப்பில் பகுதிவாரித் தமிழ் மூலம், உறையவைக்கப்பட்ட மூலப் பாணிக் கோப்புகள், படங்கள், நூற்பட்டியல் உள்ளன; கணினியில் தமிழ் மற்றும் இலத்தீன் எழுத்துருக்களும் TeX நிறுவலும் தேவை.",
    "files": [],
}
for name, path in sorted(files.items()):
    payload = path.read_bytes()
    manifest["files"].append({"path": name, "bytes": len(payload), "sha256": hash_bytes(payload)})

DESTINATION.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(DESTINATION, "w", allowZip64=True) as archive:
    archive.writestr(zip_info("SOURCE_PACKAGE_MANIFEST.json"),
                     (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    for name, path in sorted(files.items()):
        archive.writestr(zip_info(name), path.read_bytes())
with zipfile.ZipFile(DESTINATION) as archive:
    bad = archive.testzip()
    if bad or set(archive.namelist()) != set(files) | {"SOURCE_PACKAGE_MANIFEST.json"}:
        raise RuntimeError(f"Source ZIP failed readback: {bad}")
    archived_manifest = json.loads(archive.read("SOURCE_PACKAGE_MANIFEST.json"))
    for entry in archived_manifest["files"]:
        payload = archive.read(entry["path"])
        if len(payload) != entry["bytes"] or hash_bytes(payload) != entry["sha256"]:
            raise RuntimeError(f"Source ZIP manifest mismatch: {entry['path']}")
    source_units = [
        json.loads(line)
        for line in STATE.joinpath("SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if len(source_units) != 722 or len({unit["unit_id"] for unit in source_units}) != 722:
        raise RuntimeError("Frozen source manifest does not identify 722 unique units")
    cumulative = json.loads(archive.read("build/tamil-complete-722-direct.qa.json"))
    cumulative_path = "build/tamil-complete-722-direct.tex"
    if (cumulative["source_units"] != 722 or cumulative["aligned_segment_markers"] != 2242
            or cumulative["output"]["sha256"] != hash_bytes(archive.read(cumulative_path))):
        raise RuntimeError("Cumulative full-text TeX is missing or fails its unit and segment audit")
    for unit in source_units:
        source = "upstream/" + unit["source_path"]
        target = "translation/" + unit["source_path"]
        if source not in files or target not in files:
            raise RuntimeError(f"Missing source/target unit in ZIP: {unit['unit_id']}")
        if hash_bytes(archive.read(source)) != unit["source_sha256"]:
            raise RuntimeError(f"Frozen source unit hash drift in ZIP: {unit['unit_id']}")

receipt = {
    "schema": "openlogic-tamil-complete-source-package-receipt/1",
    "built_utc": datetime.now(timezone.utc).isoformat(),
    "source_revision": SOURCE_REVISION,
    "path": DESTINATION.relative_to(REPO).as_posix(),
    "bytes": DESTINATION.stat().st_size,
    "sha256": hash_bytes(DESTINATION.read_bytes()),
    "file_count": len(files) + 1,
    "editable_masters_present": True,
    "zip_readback_pass": True,
    "entry_sha256_pass": True,
    "source_target_units_verified": len(source_units),
}
receipt_path = STATE / "SOURCE-PACKAGE-RECEIPT.json"
receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, ensure_ascii=False))
