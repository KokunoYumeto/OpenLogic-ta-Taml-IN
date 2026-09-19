#!/usr/bin/env python3
"""Independently audit a packaged Tamil EPUB and run EPUBCheck 5.3.0."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from lxml import etree

XHTML = "http://www.w3.org/1999/xhtml"
MATHML = "http://www.w3.org/1998/Math/MathML"
SVG = "http://www.w3.org/2000/svg"
OPF = "http://www.idpf.org/2007/opf"
DC = "http://purl.org/dc/elements/1.1/"
CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
XML = "http://www.w3.org/XML/1998/namespace"
SOURCE_REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"
TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")
SOURCE_LEAK_RE = re.compile(r"\\(?:begin|end|olimport|documentclass|usepackage)\b|%\s*SEGMENT")
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", re.IGNORECASE)
FIXED_ZIP_TIME = (2026, 9, 10, 0, 0, 0)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identify(path: Path) -> dict:
    payload = path.read_bytes()
    return {"path": str(path), "bytes": len(payload), "sha256": sha256(payload)}


def safe_zip_name(name: str) -> bool:
    candidate = PurePosixPath(name)
    return (
        bool(name)
        and not name.startswith(("/", "\\"))
        and "\\" not in name
        and not any(part in {"", ".", ".."} for part in candidate.parts)
        and not (candidate.parts and ":" in candidate.parts[0])
    )


def parse_xml(path: Path) -> etree._Element:
    return etree.parse(str(path), parser=etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True)).getroot()


def target_for(current: PurePosixPath, reference: str) -> tuple[PurePosixPath, str] | None:
    split = urlsplit(reference)
    if split.scheme or split.netloc or reference.startswith("//"):
        return None
    path = current if not split.path else PurePosixPath(posixpath.normpath(posixpath.join(current.parent.as_posix(), unquote(split.path))))
    return path, unquote(split.fragment)


def rebuild_zip(unpacked: Path, destination: Path) -> None:
    def info(name: str, compression: int) -> zipfile.ZipInfo:
        record = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
        record.compress_type = compression
        record.create_system = 3
        record.external_attr = 0o100644 << 16
        return record

    with zipfile.ZipFile(destination, "w") as archive:
        archive.writestr(info("mimetype", zipfile.ZIP_STORED), b"application/epub+zip")
        for path in sorted(unpacked.rglob("*"), key=lambda item: item.relative_to(unpacked).as_posix()):
            if path.is_file() and path.relative_to(unpacked).as_posix() != "mimetype":
                archive.writestr(info(path.relative_to(unpacked).as_posix(), zipfile.ZIP_DEFLATED), path.read_bytes())


def load_reader(repo: Path, slug: str) -> dict:
    configuration = json.loads((repo / "epub" / "readers.json").read_text(encoding="utf-8"))
    check(configuration["source_revision"] == SOURCE_REVISION, "Reader configuration revision drift")
    matches = [reader for reader in configuration["readers"] if reader["slug"] == slug]
    check(len(matches) == 1, "Reader slug does not resolve uniquely")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--state", type=Path, default=Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN"))
    parser.add_argument(
        "--epubcheck-jar",
        type=Path,
        default=Path(os.environ["EPUBCHECK_JAR"]) if os.environ.get("EPUBCHECK_JAR") else None,
        help="Path to the pinned EPUBCheck 5.3.0 JAR (or set EPUBCHECK_JAR).",
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    state = args.state.resolve()
    reader = load_reader(repo, args.slug)
    epub = repo / "readers" / reader["filename"]
    check(epub.is_file(), f"EPUB does not exist: {epub}")
    epubcheck_jar = args.epubcheck_jar
    check(epubcheck_jar is not None and epubcheck_jar.is_file(), "Pinned EPUBCheck 5.3.0 JAR is unavailable")

    audit_root = (state / "epub-audit-work" / reader["slug"]).resolve()
    allowed_root = (state / "epub-audit-work").resolve()
    check(audit_root.parent == allowed_root, "Audit extraction path escaped its state root")
    if audit_root.exists():
        shutil.rmtree(audit_root)
    audit_root.mkdir(parents=True)

    with zipfile.ZipFile(epub) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        check(len(names) == len(set(names)), "Duplicate ZIP entries")
        check(all(safe_zip_name(name) for name in names), "Unsafe ZIP entry")
        check(names and names[0] == "mimetype", "mimetype is not the first ZIP entry")
        check(entries[0].compress_type == zipfile.ZIP_STORED, "mimetype is compressed")
        check(archive.read("mimetype") == b"application/epub+zip", "mimetype payload is incorrect")
        archive.extractall(audit_root)

    container = parse_xml(audit_root / "META-INF" / "container.xml")
    rootfiles = container.xpath("./c:rootfiles/c:rootfile", namespaces={"c": CONTAINER})
    check(len(rootfiles) == 1, "Container does not declare exactly one rootfile")
    check(rootfiles[0].get("full-path") == "OEBPS/package.opf", "Unexpected OPF path")
    opf_path = audit_root / "OEBPS" / "package.opf"
    package = parse_xml(opf_path)
    ns = {"opf": OPF, "dc": DC}
    check(package.get("version") == "3.0", "Package is not EPUB 3")
    check(package.xpath("string(./opf:metadata/dc:language[1])", namespaces=ns) == "ta-IN", "Package language is not ta-IN")
    check(package.xpath("string(./opf:metadata/opf:meta[@property='rendition:layout'][1])", namespaces=ns) == "reflowable", "Package is not declared reflowable")
    check(package.xpath("string(./opf:spine/@page-progression-direction)", namespaces=ns) == "ltr", "Tamil page progression is not LTR")
    metadata_text = " ".join(package.xpath("./opf:metadata//text()", namespaces=ns))
    check(str(reader["unit_count"]) in metadata_text and "722" in metadata_text, "Honest bounded scope is missing from metadata")

    manifest_items = package.xpath("./opf:manifest/opf:item", namespaces=ns)
    manifest: dict[PurePosixPath, etree._Element] = {}
    id_map: dict[str, PurePosixPath] = {}
    for item in manifest_items:
        href = unquote(item.get("href", ""))
        path = PurePosixPath("OEBPS") / PurePosixPath(href)
        check(safe_zip_name(path.as_posix()), f"Unsafe manifest href: {href}")
        check(path not in manifest, f"Duplicate manifest href: {href}")
        manifest[path] = item
        item_id = item.get("id", "")
        check(item_id and item_id not in id_map, "Duplicate or missing manifest ID")
        id_map[item_id] = path
        check((audit_root / Path(*path.parts)).is_file(), f"Manifest resource is missing: {path}")

    actual_oebps = {
        PurePosixPath(path.relative_to(audit_root).as_posix())
        for path in (audit_root / "OEBPS").rglob("*")
        if path.is_file() and path != opf_path
    }
    check(set(manifest) == actual_oebps, "Manifest does not exactly cover OEBPS resources")
    nav_items = [path for path, item in manifest.items() if "nav" in item.get("properties", "").split()]
    check(nav_items == [PurePosixPath("OEBPS/nav.xhtml")], "Exactly one navigation document is required")

    spine_ids = package.xpath("./opf:spine/opf:itemref/@idref", namespaces=ns)
    check(spine_ids and all(item_id in id_map for item_id in spine_ids), "Spine references an unknown manifest item")
    spine_paths = [id_map[item_id] for item_id in spine_ids]
    xhtml_paths = sorted(path for path, item in manifest.items() if item.get("media-type") == "application/xhtml+xml")
    expected_spine = set(xhtml_paths) - {PurePosixPath("OEBPS/nav.xhtml")}
    check(set(spine_paths) == expected_spine and len(spine_paths) == len(expected_spine), "Spine does not exactly cover readable XHTML")

    roots: dict[PurePosixPath, etree._Element] = {}
    ids_by_path: dict[PurePosixPath, set[str]] = {}
    math_count = 0
    svg_count = 0
    image_count = 0
    tamil_characters = 0
    source_leaks: list[str] = []
    navigation_links = 0
    for path in xhtml_paths:
        root = parse_xml(audit_root / Path(*path.parts))
        roots[path] = root
        check(etree.QName(root).namespace == XHTML and etree.QName(root).localname == "html", f"Invalid XHTML root: {path}")
        check(root.get("lang") == "ta-IN" and root.get(f"{{{XML}}}lang") == "ta-IN", f"Language metadata missing: {path}")
        check(root.get("dir") == "ltr", f"Direction metadata missing: {path}")
        ids = [value for value in root.xpath(".//@id") if value]
        check(len(ids) == len(set(ids)), f"Duplicate IDs: {path}")
        ids_by_path[path] = set(ids)
        check(not root.xpath(".//*[local-name()='script' or local-name()='iframe' or local-name()='object' or local-name()='embed']"), f"Active content found: {path}")
        text = " ".join(root.itertext())
        tamil_characters += len(TAMIL_RE.findall(text))
        if SOURCE_LEAK_RE.search(text):
            source_leaks.append(path.as_posix())
        maths = root.xpath(".//*[local-name()='math']")
        check(all(etree.QName(node).namespace == MATHML for node in maths), f"Non-native MathML: {path}")
        has_math = bool(maths)
        properties = manifest[path].get("properties", "").split()
        check(("mathml" in properties) == has_math, f"MathML manifest property mismatch: {path}")
        math_count += len(maths)
        svgs = root.xpath(".//*[local-name()='svg']")
        check(all(etree.QName(node).namespace == SVG for node in svgs), f"Invalid inline SVG namespace: {path}")
        check(
            all(
                node.get("aria-label")
                or node.get("aria-labelledby")
                or node.xpath("./*[local-name()='title'][normalize-space()]")
                for node in svgs
            ),
            f"Inline SVG lacks a textual description: {path}",
        )
        has_svg = bool(svgs)
        check(("svg" in properties) == (has_svg or path.suffix.lower() == ".svg"), f"SVG manifest property mismatch: {path}")
        svg_count += len(svgs)
        images = root.xpath(".//*[local-name()='img']")
        check(all(node.get("alt") is not None for node in images), f"Image lacks alt text: {path}")
        image_count += len(images)
        if path == PurePosixPath("OEBPS/nav.xhtml"):
            navigation_links = len(root.xpath(".//*[local-name()='nav']//*[local-name()='a'][@href]"))

    check(not source_leaks, f"Raw TeX leaked into visible XHTML: {source_leaks}")
    check(tamil_characters >= 100, "EPUB contains too little Tamil text")
    check(math_count > 0, "Technical reader contains no native MathML")
    check(navigation_links >= 3, "Navigation document is too sparse")

    for current, root in roots.items():
        for node in root.xpath(".//*[@href or @src]"):
            for attribute in ("href", "src"):
                reference = node.get(attribute)
                if not reference:
                    continue
                resolved = target_for(current, reference)
                if attribute == "src":
                    split = urlsplit(reference)
                    check(not split.scheme and not split.netloc and not reference.startswith("//"), f"Remote embedded resource: {current} -> {reference}")
                if resolved is None:
                    continue
                target, fragment = resolved
                check(target in manifest or target == PurePosixPath("OEBPS/package.opf"), f"Broken local resource link: {current} -> {reference}")
                if fragment:
                    check(fragment in ids_by_path.get(target, set()), f"Broken fragment link: {current} -> {reference}")

    for css_path, item in manifest.items():
        if item.get("media-type") != "text/css":
            continue
        text = (audit_root / Path(*css_path.parts)).read_text(encoding="utf-8-sig", errors="strict")
        for _, reference in CSS_URL_RE.findall(text):
            if reference.startswith("data:"):
                continue
            split = urlsplit(reference)
            check(not split.scheme and not split.netloc and not reference.startswith("//"), f"Remote CSS resource: {css_path} -> {reference}")
            resolved = target_for(css_path, reference)
            if resolved is not None:
                check(resolved[0] in manifest, f"Broken CSS resource link: {css_path} -> {reference}")

    crosswalk_path = state / f"EPUB-SOURCE-CROSSWALK-{reader['slug'].upper().replace('-', '_')}.json"
    crosswalk = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    expected_ids = [f"OLP-{number:04d}" for number in range(reader["first_unit"], reader["last_unit"] + 1)]
    actual_ids = [unit["unit_id"] for unit in crosswalk["units"]]
    check(actual_ids == expected_ids, "Source crosswalk unit coverage drift")
    check(crosswalk["source_revision"] == SOURCE_REVISION, "Source crosswalk revision drift")
    check(crosswalk["literal_tamil_visible_coverage_pass"], "Literal Tamil source coverage failed")
    check(not crosswalk["literal_tamil_failing_units"], "Crosswalk contains failing units")
    verified_translation_files: set[str] = set()
    for unit in crosswalk["units"]:
        for file in unit["translation_files"]:
            relative = file["path"]
            if relative in verified_translation_files:
                continue
            payload = (repo / Path(*PurePosixPath(relative).parts)).read_bytes()
            check(len(payload) == file["bytes"] and sha256(payload) == file["sha256"], f"Translation source hash drift: {relative}")
            verified_translation_files.add(relative)

    check(not any(path.suffix.lower() == ".pdf" for path in manifest), "EPUB embeds a PDF")
    page_image_pattern = re.compile(r"(?:^|[-_])(?:page|sheet)[-_]?\d+", re.IGNORECASE)
    check(not any(page_image_pattern.search(path.stem) for path in manifest if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}), "EPUB appears to contain rasterized pages")

    replay = audit_root.parent / f"{reader['slug']}-replay.epub"
    if replay.exists():
        replay.unlink()
    rebuild_zip(audit_root, replay)
    check(replay.read_bytes() == epub.read_bytes(), "EPUB is not reproducible from its unpacked payload")

    epubcheck_json = state / f"EPUBCHECK-{reader['slug'].upper().replace('-', '_')}.json"
    process = subprocess.run(
        ["java", "-Xmx768m", "-jar", str(epubcheck_jar), str(epub), "--json", str(epubcheck_json)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    check(process.returncode == 0, f"EPUBCheck failed with exit code {process.returncode}: {process.stdout[-2000:]}")
    epubcheck = json.loads(epubcheck_json.read_text(encoding="utf-8-sig"))
    messages = epubcheck.get("messages", [])
    check(messages == [], f"EPUBCheck reported {len(messages)} message(s)")
    checker_version = epubcheck.get("checker", {}).get("checkerVersion")
    check(checker_version == "5.3.0", f"Unexpected EPUBCheck version: {checker_version}")

    receipt = {
        "schema": "openlogic-tamil-epub-audit/1",
        "audited_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "reader": reader,
        "source_revision": SOURCE_REVISION,
        "epub": identify(epub),
        "epubcheck": {
            "version": checker_version,
            "jar": identify(epubcheck_jar),
            "report": identify(epubcheck_json),
            "messages": 0,
            "exit_code": process.returncode,
        },
        "structural": {
            "zip_entries": len(names),
            "manifest_resources": len(manifest),
            "spine_documents": len(spine_paths),
            "xhtml_documents": len(xhtml_paths),
            "navigation_links": navigation_links,
            "native_mathml_roots": math_count,
            "inline_svg_roots": svg_count,
            "images": image_count,
            "tamil_characters": tamil_characters,
            "active_content": 0,
            "raw_tex_leaks": 0,
            "broken_local_links": 0,
            "missing_image_alternatives": 0,
            "embedded_pdfs": 0,
            "rasterized_page_images": 0,
        },
        "source_coverage": {
            "declared_range": crosswalk["declared_range"],
            "declared_units": crosswalk["declared_unit_count"],
            "exact_unit_ids": len(actual_ids),
            "translation_files_hash_verified": len(verified_translation_files),
            "literal_tamil_source_distinct_tokens": crosswalk["literal_tamil_source_distinct_tokens"],
            "missing_literal_tamil_distinct_tokens": 0,
        },
        "reproducible_zip": True,
        "human_accessibility_certification_claimed": False,
        "independent_human_translation_review_claimed": False,
    }
    receipt_path = state / f"EPUB-AUDIT-{reader['slug'].upper().replace('-', '_')}.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
