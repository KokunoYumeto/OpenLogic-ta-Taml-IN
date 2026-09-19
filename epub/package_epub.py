#!/usr/bin/env python3
"""Package make4ht XHTML as a deterministic, reflowable Tamil EPUB 3.3."""

from __future__ import annotations

import argparse
import hashlib
import html as html_std
import json
import mimetypes
import os
import posixpath
import re
import shutil
import sys
import unicodedata
import uuid
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit, urlunsplit

from lxml import etree, html

XHTML = "http://www.w3.org/1999/xhtml"
MATHML = "http://www.w3.org/1998/Math/MathML"
SVG = "http://www.w3.org/2000/svg"
OPF = "http://www.idpf.org/2007/opf"
DC = "http://purl.org/dc/elements/1.1/"
CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
EPUB = "http://www.idpf.org/2007/ops"
XML = "http://www.w3.org/XML/1998/namespace"
SOURCE_REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"
FIXED_ZIP_TIME = (2026, 9, 10, 0, 0, 0)
TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]+")
SEGMENT_RE = re.compile(r"^% SEGMENT (OLP-(\d{4})-S\d+)\s*$", re.MULTILINE)
SAFE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]+$")
ALLOWED_ASSETS = {
    ".css", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".woff", ".woff2", ".otf", ".ttf",
}
MEDIA_TYPES = {
    ".xhtml": "application/xhtml+xml",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".otf": "font/otf",
    ".ttf": "font/ttf",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_record(path: Path, root: Path | None = None) -> dict:
    payload = path.read_bytes()
    record = {"bytes": len(payload), "sha256": sha256(payload)}
    if root is not None:
        record["path"] = path.relative_to(root).as_posix()
    return record


def strip_tex_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        cut = len(line)
        for index, char in enumerate(line):
            if char != "%":
                continue
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                cut = index
                break
        lines.append(line[:cut])
    return "\n".join(lines)


def tamil_tokens(text: str) -> list[str]:
    return [unicodedata.normalize("NFC", token) for token in TAMIL_RE.findall(text)]


def load_configuration(repo: Path, slug: str) -> tuple[dict, dict]:
    configuration = json.loads((repo / "epub" / "readers.json").read_text(encoding="utf-8"))
    if configuration.get("source_revision") != SOURCE_REVISION:
        fail("Reader configuration source revision drift")
    if not SAFE_SLUG_RE.fullmatch(slug):
        fail("Unsafe reader slug")
    matches = [item for item in configuration["readers"] if item["slug"] == slug]
    if len(matches) != 1:
        fail(f"Reader slug does not resolve uniquely: {slug}")
    reader = matches[0]
    expected_count = reader["last_unit"] - reader["first_unit"] + 1
    if expected_count != reader["unit_count"]:
        fail("Reader unit range is inconsistent")
    return configuration, reader


def segment_inventory(repo: Path, reader: dict, visible_text: str) -> dict:
    manifest_path = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN\SOURCE_MANIFEST.jsonl")
    source_manifest: dict[str, dict] = {}
    for line in manifest_path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            record = json.loads(line)
            source_manifest[record["unit_id"]] = record

    unit_blocks: dict[str, list[tuple[Path, str, str]]] = {}
    for path in sorted((repo / "translation").rglob("*.tex")):
        raw = path.read_text(encoding="utf-8-sig")
        matches = list(SEGMENT_RE.finditer(raw))
        for index, match in enumerate(matches):
            unit_id = match.group(1).rsplit("-S", 1)[0]
            number = int(match.group(2))
            if not reader["first_unit"] <= number <= reader["last_unit"]:
                continue
            end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
            block = raw[match.end():end]
            unit_blocks.setdefault(unit_id, []).append((path, match.group(1), block))

    expected_ids = [f"OLP-{number:04d}" for number in range(reader["first_unit"], reader["last_unit"] + 1)]
    missing_units = [unit for unit in expected_ids if unit not in unit_blocks]
    if missing_units:
        fail(f"Translated source units missing for configured reader: {missing_units}")
    if any(unit not in source_manifest for unit in expected_ids):
        fail("Configured unit is absent from the frozen source manifest")

    visible_counter = Counter(tamil_tokens(visible_text))
    records: list[dict] = []
    aggregate_source = Counter()
    for unit in expected_ids:
        blocks = unit_blocks[unit]
        source_counter = Counter()
        segment_records = []
        files: dict[str, dict] = {}
        for path, segment_id, block in blocks:
            clean = strip_tex_comments(block)
            words = tamil_tokens(clean)
            source_counter.update(words)
            relative = path.relative_to(repo).as_posix()
            files.setdefault(relative, file_record(path, repo))
            segment_records.append({
                "segment_id": segment_id,
                "translation_path": relative,
                "literal_tamil_token_occurrences": len(words),
            })
        aggregate_source.update(source_counter)
        missing_distinct = sorted(token for token in source_counter if visible_counter[token] == 0)
        records.append({
            "unit_id": unit,
            "source_path": source_manifest[unit]["source_path"],
            "source_sha256": source_manifest[unit]["source_sha256"],
            "source_role": source_manifest[unit]["source_role"],
            "segments": segment_records,
            "translation_files": list(files.values()),
            "literal_tamil_distinct_tokens": len(source_counter),
            "literal_tamil_missing_distinct_tokens": missing_distinct,
            "visible_literal_token_test": "pass" if not missing_distinct else "fail",
        })

    missing_aggregate = sorted(token for token in aggregate_source if visible_counter[token] == 0)
    failing_units = [record["unit_id"] for record in records if record["visible_literal_token_test"] != "pass"]
    return {
        "schema": "openlogic-tamil-epub-source-crosswalk/1",
        "source_revision": SOURCE_REVISION,
        "reader_slug": reader["slug"],
        "declared_range": f"OLP-{reader['first_unit']:04d}–OLP-{reader['last_unit']:04d}",
        "declared_unit_count": reader["unit_count"],
        "units": records,
        "unit_ids_complete": len(records) == reader["unit_count"],
        "literal_tamil_source_distinct_tokens": len(aggregate_source),
        "literal_tamil_missing_distinct_tokens": missing_aggregate,
        "literal_tamil_failing_units": failing_units,
        "literal_tamil_visible_coverage_pass": not failing_units,
    }


def parse_document(path: Path) -> tuple[etree._Element, str]:
    payload = path.read_bytes()
    mode = "xml"
    try:
        root = etree.fromstring(payload, parser=etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
    except etree.XMLSyntaxError:
        mode = "html-recovery"
        root = html.fromstring(payload, parser=html.HTMLParser(encoding="utf-8", recover=True))
    if etree.QName(root).localname.lower() != "html":
        fail(f"Generated document has no HTML root: {path}")
    return root, mode


def namespace_tree(node: etree._Element, inherited: str = XHTML) -> None:
    if not isinstance(node.tag, str):
        return
    qname = etree.QName(node)
    local = qname.localname.lower()
    namespace = qname.namespace
    target = inherited
    if namespace in {MATHML, SVG, XHTML}:
        target = namespace
    elif local == "math" or inherited == MATHML:
        target = MATHML
    elif local == "svg" or inherited == SVG:
        target = SVG
    node.tag = f"{{{target}}}{local}"
    for child in node:
        namespace_tree(child, target)


def ensure_root_namespaces(root: etree._Element) -> etree._Element:
    namespace_tree(root)
    replacement = etree.Element(f"{{{XHTML}}}html", nsmap={None: XHTML, "epub": EPUB})
    for key, value in root.attrib.items():
        replacement.set(key, value)
    replacement.text = root.text
    replacement.tail = root.tail
    for child in list(root):
        root.remove(child)
        replacement.append(child)
    return replacement


def local_name(node: etree._Element) -> str:
    return etree.QName(node).localname.lower() if isinstance(node.tag, str) else ""


def rewrite_reference(value: str, source_rel: PurePosixPath, path_map: dict[PurePosixPath, PurePosixPath]) -> str:
    split = urlsplit(value)
    if split.scheme or split.netloc or value.startswith("//") or not split.path:
        return value
    target = PurePosixPath(posixpath.normpath(posixpath.join(source_rel.parent.as_posix(), unquote(split.path))))
    if target not in path_map:
        return value
    destination = path_map[target]
    relative = posixpath.relpath(destination.as_posix(), start=path_map[source_rel].parent.as_posix())
    return urlunsplit(("", "", relative, split.query, split.fragment))


def make_xhtml(
    source: Path,
    source_rel: PurePosixPath,
    destination: Path,
    path_map: dict[PurePosixPath, PurePosixPath],
    reader: dict,
) -> dict:
    root, parse_mode = parse_document(source)
    root = ensure_root_namespaces(root)
    root.set("lang", "ta-IN")
    root.set(f"{{{XML}}}lang", "ta-IN")
    root.set("dir", "ltr")
    scripts = root.xpath(".//*[local-name()='script' or local-name()='iframe' or local-name()='object' or local-name()='embed']")
    if scripts:
        fail(f"Executable or embedded active content in generated HTML: {source_rel}")

    heads = root.xpath("./x:head", namespaces={"x": XHTML})
    bodies = root.xpath("./x:body", namespaces={"x": XHTML})
    if len(heads) != 1 or len(bodies) != 1:
        fail(f"Generated document lacks one head and body: {source_rel}")
    head, body = heads[0], bodies[0]
    titles = head.xpath("./x:title", namespaces={"x": XHTML})
    if not titles:
        title = etree.Element(f"{{{XHTML}}}title")
        title.text = reader["title"]
        head.insert(0, title)
    else:
        titles[0].text = " ".join(titles[0].itertext()).strip() or reader["title"]
    for meta in head.xpath("./x:meta[@charset]", namespaces={"x": XHTML}):
        meta.set("charset", "utf-8")
    if not head.xpath("./x:meta[@charset]", namespaces={"x": XHTML}):
        meta = etree.Element(f"{{{XHTML}}}meta")
        meta.set("charset", "utf-8")
        head.insert(0, meta)
    css_href = posixpath.relpath("../styles/reader.css", start=path_map[source_rel].parent.as_posix())
    link = etree.Element(f"{{{XHTML}}}link")
    link.set("rel", "stylesheet")
    link.set("type", "text/css")
    link.set("href", css_href)
    head.append(link)

    for node in root.xpath(".//*[@href or @src]"):
        for attribute in ("href", "src"):
            if node.get(attribute):
                split = urlsplit(node.get(attribute))
                if attribute == "src" and (split.scheme or split.netloc or node.get(attribute).startswith("//")):
                    fail(f"Remote embedded resource in generated HTML: {source_rel} -> {node.get(attribute)}")
                node.set(attribute, rewrite_reference(node.get(attribute), source_rel, path_map))

    ids: set[str] = set()
    duplicate_ids: list[str] = []
    for node in root.xpath(".//*[@id]"):
        value = node.get("id")
        if value in ids:
            duplicate_ids.append(value)
        ids.add(value)
    if duplicate_ids:
        fail(f"Duplicate IDs in {source_rel}: {sorted(set(duplicate_ids))[:10]}")

    headings: list[dict] = []
    heading_counter = 0
    for node in body.xpath(".//*[self::x:h1 or self::x:h2 or self::x:h3]", namespaces={"x": XHTML}):
        heading_counter += 1
        if not node.get("id"):
            candidate = f"heading-{heading_counter}"
            while candidate in ids:
                heading_counter += 1
                candidate = f"heading-{heading_counter}"
            node.set("id", candidate)
            ids.add(candidate)
        label = " ".join(" ".join(node.itertext()).split())
        if label:
            headings.append({"level": int(local_name(node)[1]), "id": node.get("id"), "label": label})

    math_nodes = root.xpath(".//*[local-name()='math']")
    for math_node in math_nodes:
        if etree.QName(math_node).namespace != MATHML:
            fail(f"Non-native MathML root survived normalization in {source_rel}")
    svg_nodes = root.xpath(".//*[local-name()='svg']")
    for svg_node in svg_nodes:
        if etree.QName(svg_node).namespace != SVG:
            fail(f"Invalid inline SVG namespace in {source_rel}")
        has_name = bool(
            svg_node.get("aria-label")
            or svg_node.get("aria-labelledby")
            or svg_node.xpath("./*[local-name()='title'][normalize-space()]")
        )
        if not has_name:
            fail(f"Inline SVG lacks a textual description in {source_rel}")
    image_nodes = root.xpath(".//*[local-name()='img']")
    images_without_alt = [node.get("src", "") for node in image_nodes if node.get("alt") is None]
    if images_without_alt:
        fail(f"Images without alt text in {source_rel}: {images_without_alt[:10]}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=False, doctype="<!DOCTYPE html>")
    destination.write_bytes(payload)
    visible = " ".join(" ".join(body.itertext()).split())
    return {
        "source": source_rel.as_posix(),
        "output": destination.name,
        "parse_mode": parse_mode,
        "headings": headings,
        "mathml_roots": len(math_nodes),
        "svg_roots": len(svg_nodes),
        "images": len(image_nodes),
        "visible_text": visible,
        "record": file_record(destination),
    }


def write_title_page(path: Path, reader: dict) -> dict:
    root = etree.Element(f"{{{XHTML}}}html", nsmap={None: XHTML, "epub": EPUB})
    root.set("lang", "ta-IN")
    root.set(f"{{{XML}}}lang", "ta-IN")
    root.set("dir", "ltr")
    head = etree.SubElement(root, f"{{{XHTML}}}head")
    etree.SubElement(head, f"{{{XHTML}}}meta", charset="utf-8")
    etree.SubElement(head, f"{{{XHTML}}}title").text = reader["title"]
    etree.SubElement(head, f"{{{XHTML}}}link", rel="stylesheet", type="text/css", href="styles/reader.css")
    body = etree.SubElement(root, f"{{{XHTML}}}body")
    section = etree.SubElement(body, f"{{{XHTML}}}section")
    section.set(f"{{{EPUB}}}type", "titlepage")
    etree.SubElement(section, f"{{{XHTML}}}h1", id="title").text = reader["title"]
    etree.SubElement(section, f"{{{XHTML}}}p", attrib={"class": "subtitle"}).text = reader["subtitle"]
    etree.SubElement(section, f"{{{XHTML}}}p").text = (
        f"இந்த இடைக்கால வாசகர், உறையவைக்கப்பட்ட 722 மூல அலகுகளில் "
        f"OLP-{reader['first_unit']:04d} முதல் OLP-{reader['last_unit']:04d} வரை உள்ள "
        f"{reader['unit_count']} அலகுகளை உள்ளடக்குகிறது."
    )
    etree.SubElement(section, f"{{{XHTML}}}p").text = (
        "இது இயந்திர மொழிபெயர்ப்பு; சுயாதீன மனிதச் சரிபார்ப்பு செய்யப்பட்டதாகக் கூறப்படவில்லை. "
        "முழுத் தமிழ் பதிப்பு இன்னும் தயாராகவில்லை."
    )
    source = etree.SubElement(section, f"{{{XHTML}}}p")
    source.text = "மூலம்: Open Logic Project, "
    link = etree.SubElement(source, f"{{{XHTML}}}a", href="https://github.com/OpenLogicProject/OpenLogic")
    link.text = SOURCE_REVISION
    link.tail = ". உரிமம்: "
    license_link = etree.SubElement(source, f"{{{XHTML}}}a", href="https://creativecommons.org/licenses/by/4.0/")
    license_link.text = "CC BY 4.0"
    license_link.tail = "."
    path.write_bytes(etree.tostring(root, encoding="utf-8", xml_declaration=True, doctype="<!DOCTYPE html>"))
    return file_record(path)


def write_scope_page(path: Path, reader: dict, crosswalk: dict) -> dict:
    root = etree.Element(f"{{{XHTML}}}html", nsmap={None: XHTML, "epub": EPUB})
    root.set("lang", "ta-IN")
    root.set(f"{{{XML}}}lang", "ta-IN")
    root.set("dir", "ltr")
    head = etree.SubElement(root, f"{{{XHTML}}}head")
    etree.SubElement(head, f"{{{XHTML}}}meta", charset="utf-8")
    etree.SubElement(head, f"{{{XHTML}}}title").text = "உள்ளடக்க எல்லையும் மூல இணைப்பும்"
    etree.SubElement(head, f"{{{XHTML}}}link", rel="stylesheet", type="text/css", href="styles/reader.css")
    body = etree.SubElement(root, f"{{{XHTML}}}body")
    section = etree.SubElement(body, f"{{{XHTML}}}section")
    section.set(f"{{{EPUB}}}type", "appendix")
    etree.SubElement(section, f"{{{XHTML}}}h1", id="scope").text = "உள்ளடக்க எல்லையும் மூல இணைப்பும்"
    etree.SubElement(section, f"{{{XHTML}}}p").text = (
        f"இந்த வாசகர் {crosswalk['declared_range']} என்ற தொடர்ச்சியான "
        f"{crosswalk['declared_unit_count']} மூல அலகுகளுடன் இணைக்கப்பட்டுள்ளது."
    )
    table = etree.SubElement(section, f"{{{XHTML}}}table")
    caption = etree.SubElement(table, f"{{{XHTML}}}caption")
    caption.text = "உறையவைக்கப்பட்ட மூல அலகுகள்"
    thead = etree.SubElement(table, f"{{{XHTML}}}thead")
    row = etree.SubElement(thead, f"{{{XHTML}}}tr")
    etree.SubElement(row, f"{{{XHTML}}}th", scope="col").text = "அலகு"
    etree.SubElement(row, f"{{{XHTML}}}th", scope="col").text = "மூலப் பாதை"
    tbody = etree.SubElement(table, f"{{{XHTML}}}tbody")
    for unit in crosswalk["units"]:
        row = etree.SubElement(tbody, f"{{{XHTML}}}tr", id=unit["unit_id"].lower())
        etree.SubElement(row, f"{{{XHTML}}}th", scope="row").text = unit["unit_id"]
        etree.SubElement(row, f"{{{XHTML}}}td").text = unit["source_path"]
    path.write_bytes(etree.tostring(root, encoding="utf-8", xml_declaration=True, doctype="<!DOCTYPE html>"))
    return file_record(path)


def write_navigation(path: Path, reader: dict, document_records: list[dict]) -> dict:
    root = etree.Element(f"{{{XHTML}}}html", nsmap={None: XHTML, "epub": EPUB})
    root.set("lang", "ta-IN")
    root.set(f"{{{XML}}}lang", "ta-IN")
    root.set("dir", "ltr")
    head = etree.SubElement(root, f"{{{XHTML}}}head")
    etree.SubElement(head, f"{{{XHTML}}}meta", charset="utf-8")
    etree.SubElement(head, f"{{{XHTML}}}title").text = "பொருளடக்கம்"
    etree.SubElement(head, f"{{{XHTML}}}link", rel="stylesheet", type="text/css", href="styles/reader.css")
    body = etree.SubElement(root, f"{{{XHTML}}}body")
    nav = etree.SubElement(body, f"{{{XHTML}}}nav")
    nav.set(f"{{{EPUB}}}type", "toc")
    nav.set("id", "toc")
    etree.SubElement(nav, f"{{{XHTML}}}h1").text = "பொருளடக்கம்"
    ordered = etree.SubElement(nav, f"{{{XHTML}}}ol")
    title_item = etree.SubElement(ordered, f"{{{XHTML}}}li")
    etree.SubElement(title_item, f"{{{XHTML}}}a", href="title.xhtml#title").text = reader["title"]
    for document in document_records:
        if not document["headings"]:
            continue
        for heading in document["headings"]:
            item = etree.SubElement(ordered, f"{{{XHTML}}}li", attrib={"class": f"level-{heading['level']}"})
            href = f"content/{document['output']}#{heading['id']}"
            etree.SubElement(item, f"{{{XHTML}}}a", href=href).text = heading["label"]
    scope_item = etree.SubElement(ordered, f"{{{XHTML}}}li")
    etree.SubElement(scope_item, f"{{{XHTML}}}a", href="scope.xhtml#scope").text = "உள்ளடக்க எல்லையும் மூல இணைப்பும்"
    path.write_bytes(etree.tostring(root, encoding="utf-8", xml_declaration=True, doctype="<!DOCTYPE html>"))
    return file_record(path)


def css_payload() -> bytes:
    return """@charset "UTF-8";
:root { color-scheme: light dark; }
html { writing-mode: horizontal-tb; }
body { font-family: "Noto Sans Tamil", "Nirmala UI", sans-serif; line-height: 1.55; margin: 5%; }
h1, h2, h3 { line-height: 1.25; break-after: avoid; }
.subtitle { font-size: 1.15em; }
math { font-family: math; }
img, svg { max-width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid currentColor; padding: 0.3em; vertical-align: top; }
code, pre { font-family: monospace; }
pre { white-space: pre-wrap; }
nav .level-2 { margin-inline-start: 1em; }
nav .level-3 { margin-inline-start: 2em; }
""".encode("utf-8")


def media_type(path: PurePosixPath) -> str:
    suffix = path.suffix.lower()
    if suffix in MEDIA_TYPES:
        return MEDIA_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    fail(f"No EPUB media type for resource: {path}")


def write_opf(
    path: Path,
    reader: dict,
    resources: list[PurePosixPath],
    spine: list[PurePosixPath],
    math_paths: set[PurePosixPath],
    svg_paths: set[PurePosixPath],
    all_images_have_alt: bool,
) -> dict:
    package = etree.Element(f"{{{OPF}}}package", nsmap={None: OPF, "dc": DC})
    package.set("version", "3.0")
    package.set("unique-identifier", "pub-id")
    package.set("prefix", "rendition: http://www.idpf.org/vocab/rendition/# schema: http://schema.org/")
    metadata = etree.SubElement(package, f"{{{OPF}}}metadata")
    identifier = etree.SubElement(metadata, f"{{{DC}}}identifier", id="pub-id")
    identifier.text = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"openlogic:{SOURCE_REVISION}:ta-Taml-IN:{reader['slug']}"))
    etree.SubElement(metadata, f"{{{DC}}}title").text = reader["title"]
    etree.SubElement(metadata, f"{{{DC}}}language").text = "ta-IN"
    etree.SubElement(metadata, f"{{{DC}}}creator").text = "Open Logic Project contributors"
    etree.SubElement(metadata, f"{{{DC}}}publisher").text = "OpenLogic Tamil translation programme"
    etree.SubElement(metadata, f"{{{DC}}}rights").text = "Creative Commons Attribution 4.0 International (CC BY 4.0)"
    etree.SubElement(metadata, f"{{{DC}}}description").text = (
        f"Machine-translated interim Tamil reader covering OLP-{reader['first_unit']:04d} through "
        f"OLP-{reader['last_unit']:04d} ({reader['unit_count']} of 722 frozen source units). "
        "Reflowable EPUB with native MathML; no claim of independent human review."
    )
    modified = etree.SubElement(metadata, f"{{{OPF}}}meta", property="dcterms:modified")
    modified.text = "2026-09-10T00:00:00Z"
    layout = etree.SubElement(metadata, f"{{{OPF}}}meta", property="rendition:layout")
    layout.text = "reflowable"
    for value in ("textual", "visual", "symbolic"):
        etree.SubElement(metadata, f"{{{OPF}}}meta", property="schema:accessMode").text = value
    for value in ("MathML", "tableOfContents", "readingOrder", "structuralNavigation"):
        etree.SubElement(metadata, f"{{{OPF}}}meta", property="schema:accessibilityFeature").text = value
    if all_images_have_alt:
        etree.SubElement(metadata, f"{{{OPF}}}meta", property="schema:accessibilityFeature").text = "alternativeText"
    etree.SubElement(metadata, f"{{{OPF}}}meta", property="schema:accessibilitySummary").text = (
        "Reflowable Tamil text, structural navigation, and native MathML. Images carry text alternatives. "
        "Reading-system MathML support varies. Automated checks are not a human accessibility certification."
    )

    manifest = etree.SubElement(package, f"{{{OPF}}}manifest")
    ids: dict[PurePosixPath, str] = {}
    for index, resource in enumerate(resources, start=1):
        item_id = f"item-{index:04d}"
        ids[resource] = item_id
        item = etree.SubElement(
            manifest,
            f"{{{OPF}}}item",
            attrib={"id": item_id, "href": resource.as_posix(), "media-type": media_type(resource)},
        )
        properties: list[str] = []
        if resource == PurePosixPath("nav.xhtml"):
            properties.append("nav")
        if resource in math_paths:
            properties.append("mathml")
        if resource.suffix.lower() == ".svg" or resource in svg_paths:
            properties.append("svg")
        if properties:
            item.set("properties", " ".join(properties))
    spine_element = etree.SubElement(package, f"{{{OPF}}}spine")
    spine_element.set("page-progression-direction", "ltr")
    for resource in spine:
        etree.SubElement(spine_element, f"{{{OPF}}}itemref", idref=ids[resource])
    path.write_bytes(etree.tostring(package, encoding="utf-8", xml_declaration=True, pretty_print=True))
    return file_record(path)


def write_container(root: Path) -> dict:
    meta = root / "META-INF"
    meta.mkdir(parents=True, exist_ok=True)
    container = etree.Element(f"{{{CONTAINER}}}container", nsmap={None: CONTAINER}, version="1.0")
    rootfiles = etree.SubElement(container, f"{{{CONTAINER}}}rootfiles")
    etree.SubElement(
        rootfiles,
        f"{{{CONTAINER}}}rootfile",
        attrib={"full-path": "OEBPS/package.opf", "media-type": "application/oebps-package+xml"},
    )
    path = meta / "container.xml"
    path.write_bytes(etree.tostring(container, encoding="utf-8", xml_declaration=True, pretty_print=True))
    return file_record(path)


def deterministic_zip(unpacked: Path, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()

    def info(name: str, compression: int) -> zipfile.ZipInfo:
        record = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
        record.compress_type = compression
        record.create_system = 3
        record.external_attr = 0o100644 << 16
        return record

    with zipfile.ZipFile(destination, "w") as archive:
        archive.writestr(info("mimetype", zipfile.ZIP_STORED), b"application/epub+zip")
        for path in sorted(unpacked.rglob("*"), key=lambda item: item.relative_to(unpacked).as_posix()):
            if not path.is_file() or path.name == "mimetype":
                continue
            archive.writestr(info(path.relative_to(unpacked).as_posix(), zipfile.ZIP_DEFLATED), path.read_bytes())
    with zipfile.ZipFile(destination) as archive:
        entries = archive.infolist()
        if not entries or entries[0].filename != "mimetype" or entries[0].compress_type != zipfile.ZIP_STORED:
            fail("Deterministic ZIP invariant failed")
    return file_record(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--state", type=Path, default=Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN"))
    arguments = parser.parse_args()
    repo = arguments.repo.resolve()
    state = arguments.state.resolve()
    _, reader = load_configuration(repo, arguments.slug)
    html_root = repo / "epub" / "work" / reader["slug"] / "html"
    if not html_root.is_dir():
        fail(f"No guarded make4ht output for {reader['slug']}")
    source_html = sorted(path for path in html_root.rglob("*") if path.is_file() and path.suffix.lower() in {".html", ".xhtml", ".htm"})
    if not source_html:
        fail(f"No generated HTML documents for {reader['slug']}")

    staging = repo / "epub" / "work" / reader["slug"] / "unpacked"
    if staging.exists():
        shutil.rmtree(staging)
    content = staging / "OEBPS" / "content"
    styles = staging / "OEBPS" / "styles"
    content.mkdir(parents=True)
    styles.mkdir(parents=True)
    (staging / "mimetype").write_bytes(b"application/epub+zip")
    (styles / "reader.css").write_bytes(css_payload())

    path_map: dict[PurePosixPath, PurePosixPath] = {}
    for path in sorted(item for item in html_root.rglob("*") if item.is_file()):
        relative = PurePosixPath(path.relative_to(html_root).as_posix())
        if path.suffix.lower() in {".html", ".xhtml", ".htm"}:
            path_map[relative] = PurePosixPath(relative.with_suffix(".xhtml"))
        elif path.suffix.lower() in ALLOWED_ASSETS:
            path_map[relative] = relative

    document_records: list[dict] = []
    visible_text: list[str] = []
    for source in source_html:
        relative = PurePosixPath(source.relative_to(html_root).as_posix())
        output_relative = path_map[relative]
        destination = content.joinpath(*output_relative.parts)
        record = make_xhtml(source, relative, destination, path_map, reader)
        record["output"] = output_relative.as_posix()
        document_records.append(record)
        visible_text.append(record.pop("visible_text"))

    copied_assets: list[dict] = []
    for source_relative, destination_relative in sorted(path_map.items(), key=lambda item: item[0].as_posix()):
        if source_relative.suffix.lower() in {".html", ".xhtml", ".htm"}:
            continue
        source = html_root.joinpath(*source_relative.parts)
        destination = content.joinpath(*destination_relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        copied_assets.append(file_record(destination, staging / "OEBPS"))

    crosswalk = segment_inventory(repo, reader, " ".join(visible_text))
    if not crosswalk["unit_ids_complete"]:
        fail("Source crosswalk is incomplete")
    if not crosswalk["literal_tamil_visible_coverage_pass"]:
        sample = crosswalk["literal_tamil_failing_units"][:10]
        fail(f"Generated XHTML omits literal Tamil tokens from source units: {sample}")

    oebps = staging / "OEBPS"
    title_record = write_title_page(oebps / "title.xhtml", reader)
    scope_record = write_scope_page(oebps / "scope.xhtml", reader, crosswalk)
    nav_record = write_navigation(oebps / "nav.xhtml", reader, document_records)

    resources = [PurePosixPath("title.xhtml"), PurePosixPath("nav.xhtml"), PurePosixPath("scope.xhtml"), PurePosixPath("styles/reader.css")]
    for path in sorted(content.rglob("*")):
        if path.is_file():
            resources.append(PurePosixPath(path.relative_to(oebps).as_posix()))
    spine = [PurePosixPath("title.xhtml")]
    spine.extend(PurePosixPath("content") / PurePosixPath(record["output"]) for record in document_records)
    spine.append(PurePosixPath("scope.xhtml"))
    math_paths = {
        PurePosixPath("content") / PurePosixPath(record["output"])
        for record in document_records if record["mathml_roots"] > 0
    }
    svg_paths = {
        PurePosixPath("content") / PurePosixPath(record["output"])
        for record in document_records if record["svg_roots"] > 0
    }
    opf_record = write_opf(
        oebps / "package.opf",
        reader,
        resources,
        spine,
        math_paths,
        svg_paths,
        all_images_have_alt=True,
    )
    container_record = write_container(staging)

    destination = repo / "readers" / reader["filename"]
    epub_record = deterministic_zip(staging, destination)
    crosswalk_path = state / f"EPUB-SOURCE-CROSSWALK-{reader['slug'].upper().replace('-', '_')}.json"
    crosswalk_path.write_text(json.dumps(crosswalk, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema": "openlogic-tamil-epub-package-receipt/1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "reader": reader,
        "source_revision": SOURCE_REVISION,
        "format": "EPUB 3.3",
        "layout": "reflowable",
        "language": "ta-IN",
        "script": "Taml",
        "direction": "ltr",
        "native_mathml": True,
        "wrapped_pdf_or_page_images": False,
        "independent_human_review_claimed": False,
        "documents": document_records,
        "copied_assets": copied_assets,
        "mathml_roots": sum(record["mathml_roots"] for record in document_records),
        "svg_roots": sum(record["svg_roots"] for record in document_records),
        "images": sum(record["images"] for record in document_records),
        "source_crosswalk": {**file_record(crosswalk_path), "path": crosswalk_path.name},
        "title_page": title_record,
        "scope_page": scope_record,
        "navigation": nav_record,
        "package_document": opf_record,
        "container": container_record,
        "epub": {**epub_record, "path": destination.relative_to(repo).as_posix()},
        "status": "packaged-awaiting-independent-audit",
    }
    receipt_path = state / f"EPUB-PACKAGE-{reader['slug'].upper().replace('-', '_')}-RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
