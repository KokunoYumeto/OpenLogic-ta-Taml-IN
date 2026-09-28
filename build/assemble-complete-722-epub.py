#!/usr/bin/env python3
"""Assemble the audited main and appendix EPUB bodies into one 722-unit reader."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from lxml import etree

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "epub"))
from package_epub import (  # noqa: E402
    EPUB, MATHML, SVG, XHTML, XML, PUBLIC_COMPANION_PDF_URL,
    configured_unit_ids, css_payload, deterministic_zip, file_record,
    load_configuration, reference_pdf_vocabulary, segment_inventory,
    visible_body_text, write_container, write_opf, write_scope_page,
    write_title_page,
)

COMPONENTS = (
    ("complete-main", "main", "695 அலகுகளைக் கொண்ட முதன்மை நூல்"),
    ("complete-companion", "appendix", "27 மாற்று மூலப்பிரிவு அலகுகளின் இணைப்பு"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_audit(repo: Path, state: Path, name: str) -> dict:
    path = state / name
    if not path.is_file():
        path = repo / "evidence" / name
    require(path.is_file(), f"Missing component EPUB audit: {name}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not name.startswith(("/", "\\")) and "\\" not in name and all(part not in {"", ".", ".."} for part in path.parts)


def replace_text_once(root: etree._Element, old: str, new: str) -> None:
    matches = 0
    for node in root.iter():
        for field in ("text", "tail"):
            value = getattr(node, field)
            if value and old in value:
                matches += value.count(old)
                setattr(node, field, value.replace(old, new))
    require(matches == 1, f"Expected exactly one companion introduction phrase: {old}")


def write_navigation(path: Path, reader: dict, components: list[dict]) -> None:
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
    title = etree.SubElement(ordered, f"{{{XHTML}}}li")
    etree.SubElement(title, f"{{{XHTML}}}a", href="title.xhtml#title").text = reader["title"]
    for component in components:
        item = etree.SubElement(ordered, f"{{{XHTML}}}li")
        etree.SubElement(item, f"{{{XHTML}}}a", href=component["href"]).text = component["label"]
        child_list = etree.SubElement(item, f"{{{XHTML}}}ol")
        for heading in component["headings"]:
            child = etree.SubElement(child_list, f"{{{XHTML}}}li")
            child.set("class", f"level-{heading['level']}")
            etree.SubElement(child, f"{{{XHTML}}}a", href=component["href"] + "#" + heading["id"]).text = heading["label"]
    scope = etree.SubElement(ordered, f"{{{XHTML}}}li")
    etree.SubElement(scope, f"{{{XHTML}}}a", href="scope.xhtml#scope").text = "722 அலகுகளின் மூலப் பொருத்தப் பட்டியல்"
    path.write_bytes(etree.tostring(root, encoding="utf-8", xml_declaration=True, doctype="<!DOCTYPE html>"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--state", type=Path, help="Receipt directory; defaults to build/ in this source tree")
    args = parser.parse_args()
    repo = args.repo.resolve()
    state = (args.state or repo / "build").resolve()
    state.mkdir(parents=True, exist_ok=True)
    _, reader = load_configuration(repo, "complete-722")
    main_qa = load_audit(repo, state, "EPUB-AUDIT-COMPLETE_MAIN.json")
    appendix_qa = load_audit(repo, state, "EPUB-AUDIT-COMPLETE_COMPANION.json")
    qa_by_slug = {"complete-main": main_qa, "complete-companion": appendix_qa}
    require(all(qa["status"] == "pass" and qa["epubcheck"]["messages"] == 0 for qa in qa_by_slug.values()), "Component EPUB audit is incomplete")

    staging = repo / "epub" / "work" / "complete-722" / "unpacked"
    if staging.exists():
        shutil.rmtree(staging)
    oebps = staging / "OEBPS"
    oebps.mkdir(parents=True)
    (staging / "mimetype").write_bytes(b"application/epub+zip")
    (oebps / "styles").mkdir()
    (oebps / "styles" / "reader.css").write_bytes(css_payload())

    records: list[dict] = []
    visible: list[str] = []
    for slug, prefix, label in COMPONENTS:
        qa = qa_by_slug[slug]
        _, component_reader = load_configuration(repo, slug)
        source = repo / "readers" / component_reader["filename"]
        require(source.is_file() and source.stat().st_size == qa["epub"]["bytes"] and file_record(source)["sha256"] == qa["epub"]["sha256"], f"Audited {slug} EPUB changed")
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            require(len(names) == len(set(names)) and all(safe_name(name) for name in names), f"Unsafe component EPUB: {slug}")
            for name in names:
                if not name.startswith("OEBPS/") or name in {"OEBPS/package.opf", "OEBPS/nav.xhtml", "OEBPS/title.xhtml", "OEBPS/scope.xhtml"}:
                    continue
                relative = PurePosixPath(name).relative_to("OEBPS")
                destination = oebps / prefix / Path(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(name))

        body_path = oebps / prefix / "content" / f"{slug}.xhtml"
        root = etree.parse(str(body_path)).getroot()
        body = root.find(f"{{{XHTML}}}body")
        require(body is not None, f"Component body missing: {slug}")
        if slug == "complete-main":
            links = root.xpath(".//*[@href]" )
            matching = [node for node in links if node.get("href") == PUBLIC_COMPANION_PDF_URL]
            require(len(matching) == 1, "Main EPUB companion link changed")
            matching[0].set("href", "../../appendix/content/complete-companion.xhtml")
        else:
            replace_text_once(root, "முதன்மை EPUB வாசிப்பு நூல் தனியாக வழங்கப்படுகிறது.", "முதன்மை வாசிப்பு நூல் இதற்கு முன் இடம்பெறுகிறது.")
            replace_text_once(root, "முதன்மை நூலின் இடங்களைச் சுட்டுகின்றன.", "முதன்மை நூலுக்கும் உரியவை.")
        body_path.write_bytes(etree.tostring(root, encoding="utf-8", xml_declaration=True, doctype="<!DOCTYPE html>"))
        visible.append(visible_body_text(body))

        headings: list[dict] = []
        for node in body.xpath(".//*[self::x:h1 or self::x:h2 or self::x:h3]", namespaces={"x": XHTML}):
            label_text = " ".join("".join(node.itertext()).split())
            if label_text and node.get("id"):
                headings.append({"level": int(etree.QName(node).localname[1]), "id": node.get("id"), "label": label_text})
        records.append({"slug": slug, "label": label, "href": f"{prefix}/content/{slug}.xhtml", "headings": headings,
                        "input": {"path": source.relative_to(repo).as_posix(), **file_record(source)}})

    crosswalk = segment_inventory(repo, reader, " ".join(visible), state)
    require([row["unit_id"] for row in crosswalk["units"]] == configured_unit_ids(reader), "Combined EPUB does not cover 722 distinct units")
    crosswalk["reference_pdf_vocabulary"] = reference_pdf_vocabulary(repo, reader, " ".join(visible))
    require(crosswalk["reference_pdf_vocabulary"] is not None and crosswalk["reference_pdf_vocabulary"]["pass"], "Combined EPUB omits Tamil vocabulary visible in the validated 722-unit PDF")
    crosswalk["component_epub_sha256"] = {row["slug"]: row["input"]["sha256"] for row in records}

    write_title_page(oebps / "title.xhtml", reader)
    write_scope_page(oebps / "scope.xhtml", reader, crosswalk)
    write_navigation(oebps / "nav.xhtml", reader, records)
    resources = sorted(
        (PurePosixPath(path.relative_to(oebps).as_posix()) for path in oebps.rglob("*") if path.is_file() and path.name != "package.opf"),
        key=lambda value: value.as_posix(),
    )
    spine = [PurePosixPath("title.xhtml"), PurePosixPath("main/content/complete-main.xhtml"), PurePosixPath("appendix/content/complete-companion.xhtml"), PurePosixPath("scope.xhtml")]
    math_paths, svg_paths = set(), set()
    for relative in resources:
        if relative.suffix != ".xhtml":
            continue
        document = etree.parse(str(oebps / Path(*relative.parts))).getroot()
        if document.xpath(".//*[local-name()='math' and namespace-uri()=$ns]", ns=MATHML):
            math_paths.add(relative)
        if document.xpath(".//*[local-name()='svg' and namespace-uri()=$ns]", ns=SVG):
            svg_paths.add(relative)
    write_opf(oebps / "package.opf", reader, resources, spine, math_paths, svg_paths, all_images_have_alt=True)
    write_container(staging)
    output = repo / "readers" / reader["filename"]
    output.parent.mkdir(parents=True, exist_ok=True)
    epub_record = deterministic_zip(staging, output)
    crosswalk_path = state / "EPUB-SOURCE-CROSSWALK-COMPLETE_722.json"
    crosswalk_path.write_text(json.dumps(crosswalk, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema": "openlogic-tamil-complete-722-epub-package/1",
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "status": "packaged-awaiting-independent-audit",
        "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
        "reader": reader,
        "component_epubs": {row["slug"]: row["input"] for row in records},
        "source_units": 722,
        "navigation_headings": sum(len(row["headings"]) for row in records),
        "rendered_pdf_vocabulary": crosswalk["reference_pdf_vocabulary"],
        "crosswalk": {"path": crosswalk_path.name, **file_record(crosswalk_path)},
        "epub": {"path": output.relative_to(repo).as_posix(), **epub_record},
    }
    (state / "EPUB-PACKAGE-COMPLETE_722.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
