#!/usr/bin/env python3
"""Package make4ht XHTML as a deterministic, reflowable Tamil EPUB 3.3."""

from __future__ import annotations

import argparse
import copy
import hashlib
import html as html_std
import json
import mimetypes
import os
import posixpath
import re
import shutil
import subprocess
import sys
import unicodedata
import uuid
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit, urlunsplit

import html5lib
from lxml import etree

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
MATHML_ELEMENTS = {
    "math", "mrow", "mi", "mn", "mo", "mtext", "ms", "mspace", "mstyle",
    "mfrac", "msub", "msup", "msubsup", "mover", "munder", "munderover",
    "mtable", "mtr", "mtd", "msqrt", "mroot", "menclose", "mpadded",
    "mphantom", "mmultiscripts", "maction", "maligngroup", "malignmark",
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
BLOCK_SEPARATORS = {
    "p", "div", "li", "br", "table", "tr", "td", "th",
    "h1", "h2", "h3", "h4", "h5", "h6", "mtr", "mtd",
}
NICEFRAC_RE = re.compile(
    r'<sup class="nicefrac">(.*?)</sup>\s*<mo\b[^>]*>∕</mo>\s*<sub class="nicefrac">(.*?)</sub>',
    re.DOTALL,
)
BROKEN_SMALL_CAPS_RE = re.compile(r'<span\u00a0class="small-caps">(.*?)</span>', re.DOTALL)
PUBLIC_COMPANION_PDF_URL = (
    "https://github.com/KokunoYumeto/OpenLogic-ta-Taml-IN/releases/download/"
    "v1.0.0-complete/04-openlogic-ta-Taml-IN-source-companion.pdf"
)


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


def visible_body_text(body: etree._Element) -> str:
    # Inline TeX4ht spans can split one Tamil word across several text nodes.
    # Block and table-cell boundaries, however, must separate their words.
    parts: list[str] = []
    for event, node in etree.iterwalk(body, events=("start", "end")):
        if not isinstance(node.tag, str):
            continue
        block = etree.QName(node).localname in BLOCK_SEPARATORS
        if event == "start":
            if block:
                parts.append(" ")
            if node.text:
                parts.append(node.text)
        else:
            if block:
                parts.append(" ")
            if node.tail:
                parts.append(node.tail)
    return " ".join("".join(parts).split())


def reference_pdf_vocabulary(repo: Path, reader: dict, visible_text: str) -> dict | None:
    reference = {
        "complete-main": "tamil-complete.pdf",
        "complete-722": "openlogic-ta-Taml-IN-complete-722.pdf",
    }.get(reader["slug"])
    if reference is None:
        return None
    pdf = repo / "readers" / reference
    if not pdf.is_file():
        fail(f"Validated main PDF unavailable for EPUB rendered-text parity: {pdf}")
    process = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", "-layout", str(pdf), "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if process.returncode:
        fail(f"pdftotext could not extract the validated main PDF: {process.stderr[-500:]!r}")
    pdf_words = set(tamil_tokens(process.stdout.decode("utf-8")))
    epub_words = set(tamil_tokens(visible_text))
    missing = sorted(pdf_words - epub_words)
    return {
        "method": "distinct NFC Tamil tokens in validated PDF text versus EPUB body text",
        "pdf": {"path": pdf.relative_to(repo).as_posix(), **file_record(pdf)},
        "pdf_distinct_tokens": len(pdf_words),
        "epub_distinct_tokens": len(epub_words),
        "pdf_tokens_missing_from_epub": missing,
        "pass": not missing,
    }


def configured_unit_ids(reader: dict) -> list[str]:
    first, last = reader["first_unit"], reader["last_unit"]
    full_range = [f"OLP-{number:04d}" for number in range(first, last + 1)]
    if "unit_ids" in reader:
        ids = reader["unit_ids"]
    else:
        omitted = set(reader.get("omit_units", []))
        if not omitted.issubset(full_range):
            fail("Reader omits units outside its declared span")
        ids = [unit for unit in full_range if unit not in omitted]
    if ids != sorted(set(ids)) or not ids or ids[0] != full_range[0] or ids[-1] != full_range[-1]:
        fail("Reader unit selection is unordered, duplicated, or outside its declared span")
    if len(ids) != reader["unit_count"]:
        fail("Reader unit count is inconsistent")
    return ids


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
    configured_unit_ids(reader)
    return configuration, reader


def segment_inventory(repo: Path, reader: dict, visible_text: str,
                      state: Path | None = None) -> dict:
    expected_ids = configured_unit_ids(reader)
    expected_set = set(expected_ids)
    manifest_path = repo / "evidence" / "SOURCE_MANIFEST.jsonl"
    if not manifest_path.is_file() and state is not None:
        manifest_path = state / "SOURCE_MANIFEST.jsonl"
    if not manifest_path.is_file():
        fail("Frozen source manifest is absent from evidence/ and the selected state directory")
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
            if unit_id not in expected_set:
                continue
            end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
            block = raw[match.end():end]
            unit_blocks.setdefault(unit_id, []).append((path, match.group(1), block))

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
        "declared_selection": "selected" if reader.get("unit_ids") or reader.get("omit_units") else "contiguous",
        "declared_unit_count": reader["unit_count"],
        "units": records,
        "unit_ids_complete": len(records) == reader["unit_count"],
        "literal_tamil_source_distinct_tokens": len(aggregate_source),
        "literal_tamil_missing_distinct_tokens": missing_aggregate,
        "literal_tamil_failing_units": failing_units,
        "literal_tamil_visible_coverage_pass": not failing_units,
    }


def parse_document(path: Path) -> tuple[etree._Element, str, int, dict]:
    payload = path.read_bytes()
    repaired_alternatives = 0
    preparse_repairs: dict[str, int] = {}
    if path.suffix.lower() in {".html", ".htm"}:
        generated = payload.decode("utf-8")
        generated, nicefrac_count = NICEFRAC_RE.subn(
            lambda match: '<mfrac bevelled="true"><mrow>' + match.group(1) + '</mrow><mrow>' + match.group(2) + '</mrow></mfrac>',
            generated,
        )
        preparse_repairs["nicefrac_to_mathml_fraction"] = nicefrac_count
        generated, malformed_span_count = BROKEN_SMALL_CAPS_RE.subn(lambda match: match.group(1), generated)
        preparse_repairs["malformed_small_caps_wrappers_removed"] = malformed_span_count
        if path.name == "complete-main.html":
            # The installed TeX4ht writes two tableau SVG alternatives with
            # malformed numeric entities (&#x1xxx / &#x0x). HTML5 parsing
            # turns these into XML-forbidden control characters. Preserve
            # the SVGs and give each visible step table a concise Tamil name.
            alternatives = {
                "complete-main1411x.svg": "அட்டவணை நிரூபணத்தின் 1 முதல் 6 வரிகள்",
                "complete-main1456x.svg": "அட்டவணை நிரூபணத்தின் 1 முதல் 8 வரிகள்",
            }
            for filename, description in alternatives.items():
                pattern = re.compile(
                    rf'(<img\s+src="{re.escape(filename)}"\s+alt=")[^"]*(")',
                    re.DOTALL,
                )
                matches = list(pattern.finditer(generated))
                if len(matches) != 1 or "&#x" not in matches[0].group(0):
                    fail(f"Expected one malformed tableau alternative for {filename}")
                generated = pattern.sub(lambda match: match.group(1) + description + match.group(2), generated)
                repaired_alternatives += 1
        payload = generated.encode("utf-8")
        mode = "html5"
        root = html5lib.parse(payload, treebuilder="lxml", namespaceHTMLElements=True).getroot()
    else:
        mode = "xml"
        root = etree.fromstring(payload, parser=etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
    if etree.QName(root).localname.lower() != "html":
        fail(f"Generated document has no HTML root: {path}")
    return root, mode, repaired_alternatives, preparse_repairs


def namespace_tree(node: etree._Element, inherited: str = XHTML) -> None:
    if not isinstance(node.tag, str):
        return
    qname = etree.QName(node)
    local = qname.localname.lower()
    namespace = qname.namespace
    target = inherited
    if inherited == MATHML and local in MATHML_ELEMENTS:
        target = MATHML
    elif namespace in {MATHML, SVG, XHTML}:
        target = namespace
    elif local == "math" or inherited == MATHML:
        target = MATHML
    elif local == "svg" or inherited == SVG:
        target = SVG
    node.tag = f"{{{target}}}{local}"
    # lxml's HTML recovery parser keeps xml:lang as a literal attribute name.
    # Qualify it before moving the node into a strict XHTML tree.
    for key in list(node.attrib):
        if key == "xmlns" or key.startswith("{http://www.w3.org/2000/xmlns/}"):
            del node.attrib[key]
        elif key.startswith("xml:") or key.startswith("xmlU0003A"):
            value = node.attrib.pop(key)
            local = key.split(":", 1)[1] if ":" in key else key.removeprefix("xmlU0003A")
            node.set(f"{{{XML}}}{local}", value)
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
    etree.cleanup_namespaces(replacement)
    return replacement


def local_name(node: etree._Element) -> str:
    return etree.QName(node).localname.lower() if isinstance(node.tag, str) else ""


def repair_broken_less_than(root: etree._Element) -> int:
    """Repair TeX4ht's lost opening <mo> for a literal less-than relation."""
    repaired = 0
    for node in list(root.iter()):
        if not isinstance(node.tag, str) or etree.QName(node).namespace != MATHML:
            continue
        if not (node.text or "").startswith("/mo>"):
            continue
        if node.get("class") != "MathClass-rel":
            fail("An unrecognized MathML fragment contains TeX4ht's broken /mo> marker")
        parent = node.getparent()
        if parent is None:
            fail("Broken MathML relation has no parent")
        position = parent.index(node)
        replacement = etree.Element(f"{{{MATHML}}}mo")
        replacement.set("class", "MathClass-rel")
        replacement.set("stretchy", "false")
        replacement.text = "<"
        replacement.tail = (node.text or "")[4:]
        parent.insert(position, replacement)
        last = replacement
        for child in list(node):
            node.remove(child)
            position += 1
            parent.insert(position, child)
            last = child
        last.tail = (last.tail or "") + (node.tail or "")
        parent.remove(node)
        repaired += 1
    return repaired


def split_nested_math(root: etree._Element) -> int:
    """Restore separate formulas and prose swallowed by malformed MathML."""
    repaired = 0

    def is_math(node: etree._Element) -> bool:
        return isinstance(node.tag, str) and etree.QName(node).namespace == MATHML and local_name(node) == "math"

    def has_nested_math(node: etree._Element) -> bool:
        return any(is_math(child) for child in node.iterdescendants())

    def has_tamil_spill(node: etree._Element) -> bool:
        if not isinstance(node.tag, str) or etree.QName(node).namespace != MATHML:
            return False
        if local_name(node) in {"mi", "mn", "mo", "mtext", "ms"}:
            return False
        if TAMIL_RE.search(node.text or ""):
            return True
        for child in node:
            if TAMIL_RE.search(child.tail or "") or has_tamil_spill(child):
                return True
        return False

    def events(node: etree._Element):
        if is_math(node):
            clone = copy.deepcopy(node)
            clone.tail = None
            yield ("formula", clone)
            return
        if not has_nested_math(node) and not has_tamil_spill(node):
            clone = copy.deepcopy(node)
            clone.tail = None
            yield ("piece", clone)
            return
        if node.text and node.text.strip():
            yield ("text", node.text)
        for child in node:
            if not isinstance(child.tag, str):
                continue
            yield from events(child)
            if child.tail and child.tail.strip():
                yield ("text", child.tail)

    for _ in range(10):
        candidates = [
            node for node in root.iter()
            if is_math(node)
            and node.getparent() is not None
            and etree.QName(node.getparent()).namespace != MATHML
            and (has_nested_math(node) or has_tamil_spill(node))
        ]
        if not candidates:
            return repaired
        for outer in candidates:
            parent = outer.getparent()
            if parent is None:
                continue
            position = parent.index(outer)
            preceding = parent[position - 1] if position else None
            trailing = outer.tail or ""
            stream = []
            if outer.text and outer.text.strip():
                stream.append(("text", outer.text))
            for child in outer:
                if not isinstance(child.tag, str):
                    continue
                stream.extend(events(child))
                if child.tail and child.tail.strip():
                    stream.append(("text", child.tail))
            parent.remove(outer)
            last = preceding
            pending: list[etree._Element] = []
            first_group = True

            def add_text(value: str) -> None:
                if last is None:
                    parent.text = (parent.text or "") + value
                else:
                    last.tail = (last.tail or "") + value

            def flush() -> None:
                nonlocal last, position, first_group
                if not pending:
                    return
                formula = etree.Element(f"{{{MATHML}}}math")
                if first_group and outer.get("display"):
                    formula.set("display", outer.get("display"))
                if first_group and outer.get("id"):
                    formula.set("id", outer.get("id"))
                if len(pending) == 1:
                    formula.append(pending.pop())
                else:
                    row = etree.SubElement(formula, f"{{{MATHML}}}mrow")
                    for piece in pending:
                        row.append(piece)
                    pending.clear()
                parent.insert(position, formula)
                position += 1
                last = formula
                first_group = False

            for kind, value in stream:
                if kind == "piece":
                    pending.append(value)
                elif kind == "formula":
                    flush()
                    parent.insert(position, value)
                    position += 1
                    last = value
                    first_group = False
                else:
                    flush()
                    add_text(value)
            flush()
            add_text(trailing)
            repaired += 1
    fail("Nested TeX4ht MathML exceeded the bounded normalization pass")


def normalize_generated_math(root: etree._Element) -> dict:
    changes = Counter()
    for node in list(root.iter()):
        if not isinstance(node.tag, str):
            continue
        qname = etree.QName(node)
        local = qname.localname.lower()
        if qname.namespace == MATHML:
            if local in {"mi", "mn", "mo", "mtext", "ms"} and any(
                isinstance(child.tag, str) and local_name(child) not in {"malignmark", "mglyph"}
                for child in node
            ):
                attributes = dict(node.attrib)
                original_text = node.text or ""
                node.tag = f"{{{MATHML}}}mrow"
                node.attrib.clear()
                if "id" in attributes:
                    node.set("id", attributes.pop("id"))
                node.text = None
                if original_text.strip():
                    prefix = etree.Element(f"{{{MATHML}}}{local}", attrib=attributes)
                    prefix.text = original_text
                    node.insert(0, prefix)
                else:
                    node.text = original_text
                for child in list(node):
                    if child.tail and child.tail.strip():
                        trailing = child.tail
                        child.tail = None
                        suffix = etree.Element(f"{{{MATHML}}}{local}", attrib=attributes)
                        suffix.text = trailing
                        node.insert(node.index(child) + 1, suffix)
                changes["compound_math_token_expanded"] += 1
                local = "mrow"
            if local == "a":
                node.tag = f"{{{MATHML}}}mrow"
                local = "mrow"
                changes["math_anchor_to_row"] += 1
            if local != "mo" and "stretchy" in node.attrib:
                del node.attrib["stretchy"]
                changes["invalid_stretchy_removed"] += 1
            if local == "mtable" and node.get("rowlines") == "":
                del node.attrib["rowlines"]
                changes["empty_rowlines_removed"] += 1
            if local in {"math", "mrow", "mstyle", "mtd"}:
                if node.text and node.text.strip():
                    value = node.text
                    node.text = None
                    token = etree.Element(f"{{{MATHML}}}mtext")
                    token.text = value
                    node.insert(0, token)
                    changes["bare_math_text_wrapped"] += 1
                for child in list(node):
                    if child.tail and child.tail.strip():
                        value = child.tail
                        child.tail = None
                        token = etree.Element(f"{{{MATHML}}}mtext")
                        token.text = value
                        node.insert(node.index(child) + 1, token)
                        changes["bare_math_text_wrapped"] += 1
        elif qname.namespace == XHTML and local in {"mtr", "mtd", "mspace"}:
            original_class = node.get("class", "")
            for key in list(node.attrib):
                if key not in {"id", "class"}:
                    del node.attrib[key]
            node.tag = f"{{{XHTML}}}span"
            node.set("class", f"tex4ht-{local}" + (f" {original_class}" if original_class else ""))
            if local == "mspace" and not (node.text or "").strip():
                node.text = "\u00a0"
            changes[f"stray_{local}_to_span"] += 1
    return dict(changes)


def repair_epub_xhtml_structure(root: etree._Element) -> dict:
    """Repair bounded TeX4ht HTML-parser spill without changing reading order."""
    changes = Counter()

    def append_before(parent: etree._Element, index: int, value: str) -> None:
        if not value:
            return
        if index:
            previous = parent[index - 1]
            previous.tail = (previous.tail or "") + value
        else:
            parent.text = (parent.text or "") + value

    # An HTML5 parser treats self-closing orphan <mspace/> as a container.
    # Some of those containers swallowed hundreds of later paragraphs.
    for node in reversed(list(root.xpath(".//x:span[starts-with(@class, 'tex4ht-mspace')]", namespaces={"x": XHTML}))):
        parent = node.getparent()
        if parent is None:
            continue
        position = parent.index(node)
        append_before(parent, position, node.text or "")
        for child in list(node):
            node.remove(child)
            parent.insert(position, child)
            position += 1
        append_before(parent, position, node.tail or "")
        parent.remove(node)
        changes["orphan_mspace_containers_unwrapped"] += 1

    for node in list(root.iter()):
        if not isinstance(node.tag, str):
            continue
        qname = etree.QName(node)
        local = qname.localname
        if qname.namespace == XHTML:
            if local in MATHML_ELEMENTS:
                if local == "mtable" and not len(node) and not (node.text or "").strip():
                    parent = node.getparent()
                    position = parent.index(node)
                    append_before(parent, position, node.tail or "")
                    parent.remove(node)
                    changes["empty_orphan_math_tables_removed"] += 1
                    continue
                node.tag = f"{{{MATHML}}}{local}"
                changes["orphan_math_elements_restored"] += 1
            elif local in {"td", "div"} and "columnalign" in node.attrib:
                value = node.attrib.pop("columnalign")
                if value in {"left", "right", "center"}:
                    node.set("style", ((node.get("style") or "").rstrip("; ") + f"; text-align:{value};").lstrip("; "))
                changes["html_columnalign_to_css"] += 1
            elif local == "table" and "rules" in node.attrib:
                del node.attrib["rules"]
                changes["obsolete_html_table_rules_removed"] += 1
            elif local == "span" and node.get("class", "").startswith(("tex4ht-mtd", "tex4ht-mtr")):
                if any(
                    isinstance(child.tag, str) and etree.QName(child).namespace == XHTML
                    and etree.QName(child).localname in {"p", "div", "table", "ol", "ul", "h1", "h2", "h3", "figure", "figcaption"}
                    for child in node.iterdescendants()
                ):
                    node.tag = f"{{{XHTML}}}div"
                    changes["block_math_cell_containers_retyped"] += 1

    # Keep the rendered vector glyph in its mathematical position.
    for image in list(root.xpath(".//*[local-name()='img']")):
        parent = image.getparent()
        if parent is None or etree.QName(parent).namespace != MATHML:
            continue
        replacement = etree.Element(f"{{{MATHML}}}mo")
        glyph = etree.SubElement(replacement, f"{{{MATHML}}}mglyph")
        glyph.set("src", image.get("src", ""))
        glyph.set("alt", image.get("alt", ""))
        replacement.tail = image.tail
        parent.replace(image, replacement)
        changes["math_images_to_mglyph"] += 1

    # Wrap each contiguous run of HTML-ejected MathML nodes in a math root.
    for parent in list(root.iter()):
        if not isinstance(parent.tag, str) or etree.QName(parent).namespace != XHTML:
            continue
        children = list(parent)
        index = 0
        while index < len(children):
            node = children[index]
            if not isinstance(node.tag, str) or etree.QName(node).namespace != MATHML or local_name(node) == "math":
                index += 1
                continue
            previous = node.getprevious()
            if (previous is not None and isinstance(previous.tag, str)
                    and etree.QName(previous).namespace == MATHML and local_name(previous) == "math"
                    and not (previous.tail or "").strip()):
                formula = previous
                formula.tail = None
            else:
                formula = etree.Element(f"{{{MATHML}}}math", display="inline")
                parent.insert(parent.index(node), formula)
                changes["orphan_math_runs_wrapped"] += 1
            while index < len(children):
                piece = children[index]
                if not isinstance(piece.tag, str) or etree.QName(piece).namespace != MATHML or local_name(piece) == "math":
                    break
                next_tail = piece.tail or ""
                piece.tail = None
                parent.remove(piece)
                formula.append(piece)
                index += 1
                if next_tail.strip():
                    formula.tail = (formula.tail or "") + next_tail
                    break
                if next_tail:
                    piece.tail = next_tail
            changes["orphan_math_elements_wrapped"] += len(formula)

    # HTML5 requires column groups before the table body.
    for table in root.xpath(".//x:table", namespaces={"x": XHTML}):
        misplaced = [child for child in table if local_name(child) == "colgroup"]
        for column_group in reversed(misplaced):
            table.remove(column_group)
            table.insert(0, column_group)
            changes["html_column_groups_reordered"] += 1

    # A handful of TeX4ht foreign-content rows retain HTML wrappers even
    # after their surrounding mathematical table has been restored.
    for node in list(root.iter()):
        if not isinstance(node.tag, str) or etree.QName(node).namespace != XHTML:
            continue
        parent = node.getparent()
        if parent is None or etree.QName(parent).namespace != MATHML:
            continue
        if local_name(node) == "strong" and len(node) == 1 and local_name(node[0]) == "math":
            nested = node[0]
            position = parent.index(node)
            for child in list(nested):
                nested.remove(child)
                parent.insert(position, child)
                position += 1
            append_before(parent, position, node.tail or "")
            parent.remove(node)
            changes["bold_math_html_wrappers_flattened"] += 1
        elif local_name(node) == "span" and node.get("class", "").startswith("tex4ht-mtr"):
            node.tag = f"{{{MATHML}}}mtr"
            node.attrib.clear()
            for cell in list(node):
                if local_name(cell) != "span" or not cell.get("class", "").startswith("tex4ht-mtd"):
                    fail("An orphan mathematical table row contains a non-cell element")
                cell.tag = f"{{{MATHML}}}mtd"
                cell.attrib.clear()
                for nested in list(cell):
                    if local_name(nested) != "math":
                        fail("An orphan mathematical table cell contains non-math content")
                    position = cell.index(nested)
                    for child in list(nested):
                        nested.remove(child)
                        cell.insert(position, child)
                        position += 1
                    append_before(cell, position, nested.tail or "")
                    cell.remove(nested)
            changes["orphan_math_table_rows_restored"] += 1

    for caption in list(root.xpath(".//x:figcaption", namespaces={"x": XHTML})):
        center = caption.getparent()
        figure = center.getparent() if center is not None else None
        if local_name(center) == "div" and local_name(figure) == "figure":
            center.remove(caption)
            figure.insert(figure.index(center) + 1, caption)
            changes["figure_captions_raised"] += 1

    for node in list(root.iter()):
        if not isinstance(node.tag, str) or etree.QName(node).namespace != MATHML:
            continue
        local = local_name(node)
        if local == "mspace" and (node.text or "").strip():
            value = node.text or ""
            spacing = etree.Element(f"{{{MATHML}}}mspace", attrib=dict(node.attrib))
            spacing.tail = None
            node.tag = f"{{{MATHML}}}mrow"
            node.attrib.clear()
            node.text = None
            node.insert(0, spacing)
            symbol = etree.Element(f"{{{MATHML}}}mo")
            symbol.text = value
            node.insert(1, symbol)
            changes["mspace_glyphs_separated"] += 1
        elif local == "mfrac" and len(node) > 2:
            denominator = etree.Element(f"{{{MATHML}}}mrow")
            for child in list(node)[1:]:
                node.remove(child)
                denominator.append(child)
            node.append(denominator)
            changes["compound_fraction_denominators_grouped"] += 1
        elif local == "msup" and len(node) == 1 and not "".join(node.itertext()).strip():
            parent = node.getparent()
            position = parent.index(node)
            append_before(parent, position, node.tail or "")
            parent.remove(node)
            changes["empty_superscript_layout_artifacts_removed"] += 1
        if node.text and not node.text.strip() and "\u00a0" in node.text:
            node.text = node.text.replace("\u00a0", " ")
            changes["math_nonbreaking_whitespace_normalized"] += 1
        for child in node:
            if child.tail and not child.tail.strip() and "\u00a0" in child.tail:
                child.tail = child.tail.replace("\u00a0", " ")
                changes["math_nonbreaking_whitespace_normalized"] += 1
    changes.update(normalize_generated_math(root))
    return dict(changes)


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
    root, parse_mode, repaired_alternatives, preparse_repairs = parse_document(source)
    root = ensure_root_namespaces(root)
    repaired_less_than = repair_broken_less_than(root)
    split_math = split_nested_math(root)
    math_normalizations = normalize_generated_math(root)
    structure_repairs = repair_epub_xhtml_structure(root)
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
                if (reader["slug"] == "complete-main" and source_rel.as_posix() == "complete-main.html"
                        and attribute == "href" and node.get(attribute) == "tamil-source-companion.pdf"):
                    node.set(attribute, PUBLIC_COMPANION_PDF_URL)
                    continue
                split = urlsplit(node.get(attribute))
                if attribute == "src" and (split.scheme or split.netloc or node.get(attribute).startswith("//")):
                    fail(f"Remote embedded resource in generated HTML: {source_rel} -> {node.get(attribute)}")
                node.set(attribute, rewrite_reference(node.get(attribute), source_rel, path_map))

    id_nodes = root.xpath(".//*[@id]")
    id_counts = Counter(node.get("id") for node in id_nodes)
    duplicate_values = {value for value, count in id_counts.items() if count > 1}
    linked_fragments = Counter(
        urlsplit(node.get("href")).fragment
        for node in root.xpath(".//*[@href]")
        if node.get("href")
    )
    ambiguous = duplicate_values & set(linked_fragments)
    disambiguated_linked_duplicates: list[str] = []
    if ambiguous:
        expected = {"x1-210003": "h2", "x1-230012": "figure"}
        if source_rel.as_posix() != "complete-main.html" or ambiguous != set(expected):
            fail(f"Linked duplicate IDs in {source_rel} cannot be disambiguated: {sorted(ambiguous)[:10]}")
        for value, parent_name in expected.items():
            occurrences = [node for node in id_nodes if node.get("id") == value]
            if len(occurrences) != 2 or linked_fragments[value] != 1 or local_name(occurrences[0].getparent()) != parent_name:
                fail(f"Linked duplicate ID context changed in {source_rel}: {value}")
            disambiguated_linked_duplicates.append(value)
    ids = set(id_counts)
    seen: Counter[str] = Counter()
    renamed_duplicate_ids: list[dict] = []
    for node in id_nodes:
        value = node.get("id")
        seen[value] += 1
        if seen[value] == 1:
            continue
        suffix = seen[value]
        candidate = f"{value}-duplicate-{suffix}"
        while candidate in ids:
            suffix += 1
            candidate = f"{value}-duplicate-{suffix}"
        node.set("id", candidate)
        ids.add(candidate)
        renamed_duplicate_ids.append({"original": value, "replacement": candidate})

    removed_orphan_footnote_mark_links = 0
    for anchor in list(body.xpath(".//x:a[starts-with(@href, '#Hfootnote.')]", namespaces={"x": XHTML})):
        target = anchor.get("href", "")[1:]
        if target in ids:
            continue
        next_anchor = anchor.getnext()
        children = list(anchor)
        if (len(children) != 1 or local_name(children[0]) != "span"
                or children[0].get("class") != "footnote-mark"
                or "".join(anchor.itertext()).strip()
                or next_anchor is None or local_name(next_anchor) != "a"
                or not next_anchor.get("href", "").startswith("#fn")
                or next_anchor.get("href")[1:] not in ids):
            fail(f"Unresolved footnote link is not a redundant TeX4ht mark: {target}")
        parent = anchor.getparent()
        previous = anchor.getprevious()
        if previous is None:
            parent.text = (parent.text or "") + (anchor.tail or "")
        else:
            previous.tail = (previous.tail or "") + (anchor.tail or "")
        parent.remove(anchor)
        removed_orphan_footnote_mark_links += 1

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
    # TeX4ht wraps some italic Tamil words one glyph per span. Adjacent text
    # nodes are contiguous in reading order; inserting a space at each node
    # falsely breaks those words and weakens the source-visibility check.
    visible = visible_body_text(body)
    return {
        "source": source_rel.as_posix(),
        "output": destination.name,
        "parse_mode": parse_mode,
        "repaired_tableau_alternatives": repaired_alternatives,
        "preparse_repairs": preparse_repairs,
        "repaired_less_than_relations": repaired_less_than,
        "split_nested_math_blocks": split_math,
        "math_normalizations": math_normalizations,
        "structure_repairs": structure_repairs,
        "renamed_duplicate_ids": renamed_duplicate_ids,
        "disambiguated_linked_duplicates": disambiguated_linked_duplicates,
        "removed_orphan_footnote_mark_links": removed_orphan_footnote_mark_links,
        "headings": headings,
        "mathml_roots": len(math_nodes),
        "svg_roots": len(svg_nodes),
        "images": len(image_nodes),
        "visible_text": visible,
        "record": file_record(destination),
    }


def ai_disclosure(reader: dict) -> str:
    if reader["slug"] == "complete-companion":
        attribution = "இந்த 27 அலகுகளின் இயந்திரத் தமிழாக்கமும் பதிப்புப் பணியும் OpenAI Codex — GPT-6 Sol, Ultra சிந்தனை நிலையில் செய்யப்பட்டன."
    elif reader.get("complete_edition"):
        attribution = ("முதல் 570 அலகுகளின் இயந்திரத் தமிழாக்கமும் திருத்தங்களும் OpenAI Codex — GPT-5.6 Sol, Ultra சிந்தனை நிலையில்; "
                       "பின்னைய தமிழாக்கமும் பதிப்புப் பணியும் OpenAI Codex — GPT-6 Sol, Ultra சிந்தனை நிலையில் செய்யப்பட்டன.")
    elif reader["last_unit"] <= 573:
        attribution = "இந்த அலகுகளின் இயந்திரத் தமிழாக்கமும் திருத்தங்களும் OpenAI Codex — GPT-5.6 Sol, Ultra சிந்தனை நிலையில் செய்யப்பட்டன."
    else:
        attribution = "இந்த அலகுகளின் இயந்திரத் தமிழாக்கமும் திருத்தங்களும் OpenAI Codex — GPT-6 Sol, Ultra சிந்தனை நிலையில் செய்யப்பட்டன."
    return attribution + " சுயாதீன மனிதச் சரிபார்ப்பு செய்யப்பட்டதாகக் கூறப்படவில்லை."


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
    scope_kind = "தேர்ந்தெடுக்கப்பட்ட" if reader.get("unit_ids") or reader.get("omit_units") else "தொடர்ச்சியான"
    etree.SubElement(section, f"{{{XHTML}}}p").text = (
        f"உறையவைக்கப்பட்ட 722 மூல அலகுகளில் OLP-{reader['first_unit']:04d} முதல் "
        f"OLP-{reader['last_unit']:04d} வரையிலான {scope_kind} "
        f"{reader['unit_count']} அலகுகளை இந்த வாசகர் உள்ளடக்குகிறது."
    )
    disclosure = ai_disclosure(reader)
    etree.SubElement(section, f"{{{XHTML}}}p").text = disclosure
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
        f"இந்த வாசகர் {crosswalk['declared_range']} என்ற எல்லைக்குள் "
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
    etree.SubElement(metadata, f"{{{DC}}}creator").text = "Open Logic Project பங்களிப்பாளர்கள்"
    etree.SubElement(metadata, f"{{{DC}}}publisher").text = "OpenLogic தமிழ்ப் பதிப்புத் திட்டம்"
    etree.SubElement(metadata, f"{{{DC}}}rights").text = "கிரியேட்டிவ் காமன்ஸ் பண்புக்கூறல் 4.0 பன்னாட்டு உரிமம் (CC BY 4.0)"
    etree.SubElement(metadata, f"{{{DC}}}description").text = (
        f"உறையவைக்கப்பட்ட 722 மூல அலகுகளில் OLP-{reader['first_unit']:04d} முதல் "
        f"OLP-{reader['last_unit']:04d} வரையிலான {reader['unit_count']} அலகுகள். "
        "கணிதத்திற்கான MathML உடைய மறுஓட்ட EPUB. "
        + ai_disclosure(reader)
    )
    modified = etree.SubElement(metadata, f"{{{OPF}}}meta", property="dcterms:modified")
    modified.text = "2026-09-28T00:00:00Z"
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
        if resource in svg_paths:
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
    parser.add_argument("--state", type=Path, help="Receipt directory; defaults to build/ in this source tree")
    arguments = parser.parse_args()
    repo = arguments.repo.resolve()
    state = (arguments.state or repo / "build").resolve()
    state.mkdir(parents=True, exist_ok=True)
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

    crosswalk = segment_inventory(repo, reader, " ".join(visible_text), state)
    if not crosswalk["unit_ids_complete"]:
        fail("Source crosswalk is incomplete")
    crosswalk["reference_pdf_vocabulary"] = reference_pdf_vocabulary(repo, reader, " ".join(visible_text))
    if crosswalk["reference_pdf_vocabulary"] is not None and not crosswalk["reference_pdf_vocabulary"]["pass"]:
        fail(f"EPUB omits Tamil vocabulary visible in the validated PDF: {crosswalk['reference_pdf_vocabulary']['pdf_tokens_missing_from_epub'][:10]}")
    if not crosswalk["literal_tamil_visible_coverage_pass"] and crosswalk["reference_pdf_vocabulary"] is None:
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
