from __future__ import annotations

from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import subprocess


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN")
SOURCE_COMMIT = "3d20aea0980eddfb823c4e4c9aedf84b4eaedbe3"
ROOT = "translation/content/set-theory/spine/spine.tex"
MASTER = "build/tamil-set-theory-spine.tex"
OUTPUT = REPO / "release" / "openlogic-ta-Taml-IN-set-theory-stages-ranks-7-units.tex"
PDF = REPO / "readers" / "set-theory-stages-ranks-ta-Taml-IN.pdf"
PDF_SHA256 = "a22bd7308a8c725f70eca6e1262401d43f5fda37743f9cc7f64fd6826bc0c58d"

SUPPORT = {
    "upstream/sty/open-logic.sty": "olt-spine-open-logic.sty",
    "upstream/open-logic-locale.sty": "olt-spine-open-logic-locale.sty",
    "upstream/sty/open-logic-referencing.sty": "olt-spine-open-logic-referencing.sty",
    "upstream/sty/open-logic-formulas.sty": "olt-spine-open-logic-formulas.sty",
    "upstream/sty/open-logic-tokenize.sty": "olt-spine-open-logic-tokenize.sty",
    "upstream/sty/open-logic-selective.sty": "olt-spine-open-logic-selective.sty",
    "upstream/sty/bussproofs-extra.sty": "olt-spine-bussproofs-extra.sty",
    "upstream/sty/ptolemaicastronomy.sty": "olt-spine-ptolemaicastronomy.sty",
    "upstream/open-logic-config.sty": "olt-spine-open-logic-config.sty",
    "upstream/open-logic-envs.sty": "olt-spine-open-logic-envs.sty",
    "translation/tamil-config.sty": "olt-spine-tamil-config.sty",
    "translation/tamil-pdf-math.sty": "olt-spine-tamil-pdf-math.sty",
    "upstream/bib/open-logic.bib": "olt-spine-open-logic.bib",
    "upstream/bib/natbib-oup.bst": "olt-spine-natbib-oup.bst",
}
IMPORT_RE = re.compile(
    r"\\olimport(?P<star>\*)?(?:\[(?P<directory>[^\]]+)\])?"
    r"\{(?P<name>[^}]+)\}(?:\[(?P<section>[^\]]+)\])?"
)


def git_blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{SOURCE_COMMIT}:{path}"], cwd=REPO)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def active_tex(text: str) -> str:
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def normalized(path: PurePosixPath) -> str:
    parts: list[str] = []
    for part in path.parts:
        if part in ("", "."):
            continue
        if part == "..":
            assert parts
            parts.pop()
        else:
            parts.append(part)
    return PurePosixPath(*parts).as_posix()


manifest = {
    row["unit_id"]: row
    for row in (
        json.loads(line)
        for line in git_blob("evidence/source-manifest.jsonl")
        .decode("utf-8-sig")
        .splitlines()
        if line.strip()
    )
}
manifest_by_path = {
    "translation/" + row["source_path"]: row for row in manifest.values()
}
translation_paths: set[str] = set()


def collect_translation(path: str) -> None:
    path = normalized(PurePosixPath(path))
    if path in translation_paths:
        return
    assert path in manifest_by_path, path
    payload = git_blob(path)
    translation_paths.add(path)
    parent = PurePosixPath(path).parent
    for match in IMPORT_RE.finditer(active_tex(payload.decode("utf-8"))):
        assert not match.group("star"), (path, match.group(0))
        target_parent = parent
        if match.group("directory"):
            target_parent /= match.group("directory")
        collect_translation((target_parent / (match.group("name") + ".tex")).as_posix())


collect_translation(ROOT)
embedded_units = {manifest_by_path[path]["unit_id"]: path for path in translation_paths}
assert set(embedded_units) == {f"OLP-{number:04d}" for number in range(558, 565)}
assert len(translation_paths) == 7
unit_names = {
    path: f"olt-spine-unit-{manifest_by_path[path]['unit_id']}.tex"
    for path in translation_paths
}

support_replacements = {
    r"\olpath/locale/\ollangid/open-logic-locale.sty": SUPPORT["upstream/open-logic-locale.sty"],
    r"\olpath/open-logic-locale.sty": SUPPORT["upstream/open-logic-locale.sty"],
    r"\olpath/sty/open-logic-referencing.sty": SUPPORT["upstream/sty/open-logic-referencing.sty"],
    r"\olpath/sty/open-logic-formulas.sty": SUPPORT["upstream/sty/open-logic-formulas.sty"],
    r"\olpath/sty/open-logic-tokenize.sty": SUPPORT["upstream/sty/open-logic-tokenize.sty"],
    r"\olpath/sty/open-logic-selective.sty": SUPPORT["upstream/sty/open-logic-selective.sty"],
    r"\olpath/sty/bussproofs-extra.sty": SUPPORT["upstream/sty/bussproofs-extra.sty"],
    r"\olpath/sty/ptolemaicastronomy.sty": SUPPORT["upstream/sty/ptolemaicastronomy.sty"],
    r"\olpath/open-logic-config.sty": SUPPORT["upstream/open-logic-config.sty"],
    r"\olpath/locale/\ollangid/open-logic-envs.sty": SUPPORT["upstream/open-logic-envs.sty"],
    r"\olpath/open-logic-envs.sty": SUPPORT["upstream/open-logic-envs.sty"],
}


def rewritten_support(path: str) -> bytes:
    text = git_blob(path).decode("utf-8")
    for source, target in support_replacements.items():
        text = text.replace(source, target)
    assert not re.search(
        r"\\input\{\\olpath/(?:sty/|open-logic-(?:locale|config|envs))", text
    ), path
    return text.encode("utf-8")


embedded: list[tuple[str, bytes, str, str]] = []
for path, name in SUPPORT.items():
    original = git_blob(path)
    data = rewritten_support(path) if path.endswith(".sty") else original
    embedded.append((name, data, path, sha256(original)))
for path, name in sorted(unit_names.items()):
    data = git_blob(path)
    embedded.append((name, data, path, sha256(data)))
assert len({name for name, _, _, _ in embedded}) == len(embedded) == 21
for name, data, path, _ in embedded:
    assert b"\\end{filecontents*}" not in data, path
    assert data.endswith(b"\n"), path
    assert "/" not in name and "\\" not in name and ".." not in name

lines = [
    "% திறந்த தருக்கவியல் — படிநிலைகளும் தரநிலைகளும்: முழு உரையுடன் ஒரே LaTeX கோப்பு.",
    f"% ஏற்கப்பட்ட உறையவைக்கப்பட்ட மூலக் கமிட்: {SOURCE_COMMIT}",
    "% உள்ளடக்கம்: OLP-0558 முதல் OLP-0564 வரை, அத்தியாயத்தின் ஏழு அலகுகளும்.",
    "% கீழுள்ள ஒவ்வொரு தமிழ் அலகும் ஏற்கப்பட்ட Git மூலத்துடன் எழுத்துக்கு எழுத்து ஒத்தது.",
    "% இந்தக் கோப்பை .tex ஆகச் சேமித்து XeLaTeX, BibTeX, XeLaTeX இரு முறை இயக்குக.",
    "% பொதுவான TeX தொகுப்புகளும் Nirmala UI, Consolas எழுத்துருக்களும் தேவை.",
    "%",
]
for unit_id in sorted(embedded_units):
    path = embedded_units[unit_id]
    lines.append(f"% Reader-Unit: {unit_id} {path} {sha256(git_blob(path))}")
lines.append("")
for name, data, original_path, original_sha in embedded:
    lines.extend([
        f"% Embedded-Source: {original_path} SHA256 {original_sha}",
        rf"\begin{{filecontents*}}{{{name}}}",
        data.decode("utf-8").removesuffix("\n"),
        r"\end{filecontents*}",
        "",
    ])

mapping_lines = [r"\makeatletter"]
for path in sorted(translation_paths):
    relative = path.removeprefix("translation/")
    directory = PurePosixPath(relative).parent.as_posix()
    mapping_lines.append(
        rf"\expandafter\def\csname TA@file@{relative}\endcsname{{{unit_names[path]}}}"
    )
    mapping_lines.append(
        rf"\expandafter\def\csname TA@dir@{relative}\endcsname{{{directory}}}"
    )
mapping_lines.extend([
    r"\newcommand{\TAIncludePath}[1]{%",
    r"  \ifcsname TA@file@#1\endcsname",
    r"    \begingroup",
    r"    \edef\TAcurrentdir{\csname TA@dir@#1\endcsname}%",
    r"    \edef\TAcurrentfile{\csname TA@file@#1\endcsname}%",
    r"    \expandafter\subfile\expandafter{\TAcurrentfile}%",
    r"    \endgroup",
    r"  \else\PackageError{OpenLogic Tamil}{Embedded source path not found: #1}{}\fi}",
    r"\RenewDocumentCommand\olimport{s o m o}{%",
    r"  \begingroup",
    r"  \IfBooleanT{#1}{\PackageError{OpenLogic Tamil}{Starred olimport is not present in this reader}{}}%",
    r"  \IfNoValueTF{#4}{\def\ol@sectioncs{section}}{\def\ol@sectioncs{#4}}%",
    r"  \IfNoValueTF{#2}{\edef\TAtarget{\TAcurrentdir/#3.tex}}{\edef\TAtarget{\TAcurrentdir/#2/#3.tex}}%",
    r"  \expandafter\TAIncludePath\expandafter{\TAtarget}%",
    r"  \endgroup}",
    r"\makeatother",
])
mapping = "\n".join(mapping_lines)

master = git_blob(MASTER).decode("utf-8")
master = master.replace(r"\newcommand{\olpath}{../upstream}", r"\newcommand{\olpath}{.}")
master = master.replace(r"\input{\olpath/sty/open-logic.sty}", r"\input{olt-spine-open-logic.sty}")
master = master.replace(r"\input{../translation/tamil-config.sty}", r"\input{olt-spine-tamil-config.sty}")
master = master.replace(
    r"\input{../translation/tamil-pdf-math.sty}",
    r"\input{olt-spine-tamil-pdf-math.sty}" + "\n" + mapping,
)
master = master.replace(
    r"\subfile{../translation/content/set-theory/spine/spine.tex}",
    r"\TAIncludePath{content/set-theory/spine/spine.tex}",
)
master = master.replace(
    r"\bibliographystyle{../upstream/bib/natbib-oup}",
    r"\bibliographystyle{olt-spine-natbib-oup}",
)
master = master.replace(
    r"\bibliography{../upstream/bib/open-logic}",
    r"\bibliography{olt-spine-open-logic}",
)
master = master.replace(
    r"\hypersetup{pdftitle={OpenLogic Tamil: Stages and Ranks},pdfauthor={OpenLogic Tamil translation programme},pdfsubject={Machine translation; OLP-0558 through OLP-0564; 7 of 722 frozen source units}}",
    r"\hypersetup{pdftitle={திறந்த தருக்கவியல் — படிநிலைகளும் தரநிலைகளும்},pdfauthor={OpenLogic தமிழ் மொழிபெயர்ப்பு நிரல்},pdfsubject={GPT-5.6 Sol (Ultra) இயந்திர மொழிபெயர்ப்பு; OLP-0558 முதல் OLP-0564 வரை; 722 மூல அலகுகளில் 7},pdflang={ta-IN}}",
)
master = master.replace(
    "கூறப்படவில்லை. முழுப் பதிப்பு இன்னும் தயாராகவில்லை.",
    "கூறப்படவில்லை. முழுப் பதிப்பு இன்னும் தயாராகவில்லை.\n"
    "மொழிபெயர்ப்பும் கணிதச் சரிபார்ப்பும் OpenAI Codex — GPT-5.6 Sol,\n"
    "Ultra முயற்சி நிலையில் செய்யப்பட்டன.",
)
assert master.count(r"\TAIncludePath{content/set-theory/spine/spine.tex}") == 1
assert "GPT-5.6 Sol" in master
assert "../translation" not in master and "../upstream" not in master
lines.extend([master.removesuffix("\n"), ""])
OUTPUT.parent.mkdir(exist_ok=True)
OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")

artifact = OUTPUT.read_bytes()
artifact_text = artifact.decode("utf-8")
assert b"c:\\users" not in artifact.lower()
assert len(re.findall(r"^% Reader-Unit: OLP-\d{4} ", artifact_text, re.MULTILINE)) == 7
for path, flat in unit_names.items():
    begin = f"\\begin{{filecontents*}}{{{flat}}}\n"
    start = artifact_text.index(begin) + len(begin)
    finish = artifact_text.index(r"\end{filecontents*}", start)
    assert artifact_text[start:finish].encode("utf-8") == git_blob(path), path
assert PDF.stat().st_size == 153034 and sha256(PDF.read_bytes()) == PDF_SHA256

receipt = {
    "schema": "openlogic-tamil-spine-tex-source/1",
    "source_commit": SOURCE_COMMIT,
    "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
    "scope": {
        "first_unit": "OLP-0558",
        "last_unit": "OLP-0564",
        "counted_reader_units": 7,
        "embedded_translation_files": 7,
        "programme_accepted_units_at_source_commit": 561,
        "programme_total_units": 722,
        "unaccepted_units_included": [],
    },
    "completeness": {
        "exact_translation_blobs_verified": 7,
        "embedded_project_support_files": len(SUPPORT),
        "project_local_inputs_generated_by_asset": True,
        "external_requirements": "Standard TeX packages plus Nirmala UI and Consolas fonts",
        "accepted_pdf_replaced": False,
        "master_metadata_translation": "Tamil PDF title, subject, language and AI model disclosure in the source companion only",
    },
    "reader_pdf": {
        "path": PDF.relative_to(REPO).as_posix(),
        "bytes": PDF.stat().st_size,
        "sha256": PDF_SHA256,
    },
    "reader_master": {
        "source_path": MASTER,
        "source_sha256": sha256(git_blob(MASTER)),
        "assembled_executable_sha256": sha256(master.encode("utf-8")),
    },
    "asset": {
        "filename": OUTPUT.name,
        "bytes": len(artifact),
        "sha256": sha256(artifact),
    },
    "reader_units": [
        {
            "unit_id": unit_id,
            "source_path": embedded_units[unit_id],
            "translation_sha256": sha256(git_blob(embedded_units[unit_id])),
        }
        for unit_id in sorted(embedded_units)
    ],
    "support_files": [
        {
            "source_path": path,
            "embedded_name": name,
            "source_sha256": sha256(git_blob(path)),
            "embedded_sha256": sha256(
                rewritten_support(path) if path.endswith(".sty") else git_blob(path)
            ),
            "transformation": "project-local input path rewrite"
            if path.endswith(".sty")
            else "byte-identical",
        }
        for path, name in SUPPORT.items()
    ],
}
(STATE / "SET-THEORY-SPINE-TEX-SOURCE.json").write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)
print(json.dumps(receipt["asset"], ensure_ascii=False, indent=2))
