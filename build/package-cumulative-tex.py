from __future__ import annotations

from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import re
import subprocess
import tarfile


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN")
RELEASE_COMMIT = "b6eefd2cd47c305944554d99a9992ebe81a1e807"
OUTPUT = REPO / "release" / "openlogic-ta-Taml-IN-cumulative-reader-203-units.tex"

SECTIONS = [
    {
        "title": "கணங்கள், தொடர்புகள், சார்புகள் மற்றும் எண்கணிதக் கட்டமைப்புகள்",
        "roots": [
            "translation/content/sets-functions-relations/sets/sets.tex",
            "translation/content/sets-functions-relations/relations/relations-complete.tex",
            "translation/content/sets-functions-relations/functions/functions.tex",
            "translation/content/sets-functions-relations/size-of-sets/size-of-sets-complete.tex",
            "translation/content/sets-functions-relations/arithmetization/arithmetization.tex",
            "translation/content/sets-functions-relations/infinite/infinite.tex",
        ],
        "notes": [
            "translation/sets-notes.tex",
            "translation/relations-notes.tex",
            "translation/functions-notes.tex",
            "translation/size-notes.tex",
            "translation/arithmetization-notes.tex",
            "translation/infinite-notes.tex",
        ],
        "bibliography": True,
    },
    {
        "title": "நிறுவல் முறைமைகள்: தொடர்கணிதம், இயற்கை வருவித்தல், அட்டவணை மரங்கள்",
        "roots": [
            "translation/content/first-order-logic/proof-systems/proof-systems.tex",
            "translation/content/first-order-logic/sequent-calculus/sequent-calculus.tex",
            "translation/content/first-order-logic/natural-deduction/natural-deduction.tex",
            "translation/content/first-order-logic/tableaux/tableaux.tex",
        ],
    },
    {
        "title": "அடிகோள் வருவித்தல்",
        "roots": [
            "translation/content/first-order-logic/axiomatic-deduction/axiomatic-deduction.tex"
        ],
    },
    {
        "title": "கணிப்புத்தன்மை",
        "roots": ["translation/content/computability/computability.tex"],
    },
    {
        "title": "டியூரிங் பொறிகள்",
        "roots": ["translation/content/turing-machines/turing-machines.tex"],
    },
    {
        "title": "முழுமையின்மையும் எண்கணிதமாக்கலும்",
        "roots": [
            "translation/content/incompleteness/introduction/introduction.tex",
            "translation/content/incompleteness/arithmetization-syntax/arithmetization-syntax.tex",
        ],
    },
    {
        "title": "ராபின்சன் Q இல் பிரதிநிதித்துவப்படுத்தல்",
        "roots": [
            "translation/content/incompleteness/representability-in-q/representability-in-q.tex"
        ],
    },
]

SUPPORT = {
    "upstream/sty/open-logic.sty": "olt-open-logic.sty",
    "upstream/open-logic-locale.sty": "olt-open-logic-locale.sty",
    "upstream/sty/open-logic-referencing.sty": "olt-open-logic-referencing.sty",
    "upstream/sty/open-logic-formulas.sty": "olt-open-logic-formulas.sty",
    "upstream/sty/open-logic-tokenize.sty": "olt-open-logic-tokenize.sty",
    "upstream/sty/open-logic-selective.sty": "olt-open-logic-selective.sty",
    "upstream/sty/bussproofs-extra.sty": "olt-bussproofs-extra.sty",
    "upstream/sty/ptolemaicastronomy.sty": "olt-ptolemaicastronomy.sty",
    "upstream/open-logic-config.sty": "olt-open-logic-config.sty",
    "upstream/open-logic-envs.sty": "olt-open-logic-envs.sty",
    "translation/tamil-config.sty": "olt-tamil-config.sty",
    "translation/tamil-pdf-math.sty": "olt-tamil-pdf-math.sty",
    "upstream/bib/open-logic.bib": "olt-open-logic.bib",
    "upstream/bib/natbib-oup.bst": "olt-natbib-oup.bst",
}

IMPORT_RE = re.compile(
    r"\\olimport(?P<star>\*)?(?:\[(?P<directory>[^\]]+)\])?"
    r"\{(?P<name>[^}]+)\}(?:\[(?P<section>[^\]]+)\])?"
)
ASSET_RE = re.compile(r"\\olasset(?:\[[^\]]+\])?\{(?P<path>[^}]+)\}")


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


archive_bytes = subprocess.check_output(
    ["git", "archive", "--format=tar", RELEASE_COMMIT], cwd=REPO
)
payloads: dict[str, bytes] = {}
with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
    for member in archive.getmembers():
        if member.isfile():
            stream = archive.extractfile(member)
            assert stream is not None
            payloads[member.name] = stream.read()

manifest = {
    row["unit_id"]: row
    for row in (
        json.loads(line)
        for line in payloads["evidence/source-manifest.jsonl"]
        .decode("utf-8-sig")
        .splitlines()
        if line.strip()
    )
}
manifest_by_translation_path = {
    "translation/" + row["source_path"]: row for row in manifest.values()
}

translation_paths: set[str] = set()


def collect_translation(path: str) -> None:
    path = normalized(PurePosixPath(path))
    if path in translation_paths:
        return
    assert path in manifest_by_translation_path, path
    assert path in payloads, path
    translation_paths.add(path)
    text = active_tex(payloads[path].decode("utf-8"))
    parent = PurePosixPath(path).parent
    for match in IMPORT_RE.finditer(text):
        assert not match.group("star"), (path, match.group(0))
        target_parent = parent
        if match.group("directory"):
            target_parent /= match.group("directory")
        collect_translation((target_parent / (match.group("name") + ".tex")).as_posix())


for section in SECTIONS:
    for root in section["roots"]:
        collect_translation(root)

embedded_units = {
    manifest_by_translation_path[path]["unit_id"]: path for path in translation_paths
}
assert len(embedded_units) == len(translation_paths) == 206
reader_units = {
    unit_id
    for unit_id, path in embedded_units.items()
    if (
        4 <= manifest[unit_id]["order"] <= 54
        or 63 <= manifest[unit_id]["order"] <= 125
        or 208 <= manifest[unit_id]["order"] <= 273
        or 276 <= manifest[unit_id]["order"] <= 279
        or 281 <= manifest[unit_id]["order"] <= 288
        or 290 <= manifest[unit_id]["order"] <= 300
    )
}
structural_drivers = set(embedded_units) - reader_units
assert len(reader_units) == 203
assert structural_drivers == {"OLP-0275", "OLP-0280", "OLP-0289"}
assert not any(347 <= manifest[unit]["order"] <= 352 for unit in embedded_units)

unit_names = {
    path: f"olt-unit-{manifest_by_translation_path[path]['unit_id']}.tex"
    for path in translation_paths
}
note_paths = [path for section in SECTIONS for path in section.get("notes", [])]
note_names = {
    path: "olt-note-" + PurePosixPath(path).stem + ".tex" for path in note_paths
}

asset_paths: set[str] = set()
asset_argument_to_path: dict[str, str] = {}
for path in translation_paths:
    text = active_tex(payloads[path].decode("utf-8"))
    for match in ASSET_RE.finditer(text):
        argument = match.group("path")
        if argument.startswith(r"\olpath/"):
            target = "upstream/" + argument[len(r"\olpath/") :]
        else:
            target = "upstream/" + argument
        assert target in payloads, (path, argument, target)
        asset_paths.add(target)
        asset_argument_to_path[argument] = target
asset_names = {
    path: f"olt-asset-{index:02d}{PurePosixPath(path).suffix}"
    for index, path in enumerate(sorted(asset_paths), start=1)
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
    text = payloads[path].decode("utf-8")
    for source, target in support_replacements.items():
        text = text.replace(source, target)
    mandatory_project_input = re.compile(r"\\input\{\\olpath/(?:sty/|open-logic-(?:locale|config|envs))")
    assert not mandatory_project_input.search(text), path
    return text.encode("utf-8")


embedded: list[tuple[str, bytes, str, str]] = []
for path, name in SUPPORT.items():
    assert path in payloads
    data = rewritten_support(path) if path.endswith(".sty") else payloads[path]
    embedded.append((name, data, path, sha256(payloads[path])))
for path, name in sorted(unit_names.items()):
    embedded.append((name, payloads[path], path, sha256(payloads[path])))
for path, name in sorted(note_names.items()):
    assert path in payloads
    embedded.append((name, payloads[path], path, sha256(payloads[path])))
for path, name in sorted(asset_names.items()):
    embedded.append((name, payloads[path], path, sha256(payloads[path])))

assert len({name for name, _, _, _ in embedded}) == len(embedded)
for name, data, path, _ in embedded:
    assert b"\\end{filecontents*}" not in data, path
    assert data.endswith(b"\n"), path

lines: list[str] = [
    "% OpenLogic Tamil cumulative reader source bundle",
    f"% Frozen release commit: {RELEASE_COMMIT}",
    "% Scope: 203 counted reader units plus three necessary structural chapter drivers.",
    "% The exact original translation blobs are embedded below with their Git SHA-256 identities.",
    "% Save this file under its published filename and run XeLaTeX/BibTeX in a writable directory.",
    "% Standard TeX packages and the Nirmala UI and Consolas fonts are required; no project-local input is required.",
    "%",
]
for unit_id in sorted(reader_units):
    path = embedded_units[unit_id]
    lines.append(
        f"% Reader-Unit: {unit_id} {path} {sha256(payloads[path])}"
    )
for unit_id in sorted(structural_drivers):
    path = embedded_units[unit_id]
    lines.append(
        f"% Structural-Driver: {unit_id} {path} {sha256(payloads[path])}"
    )
lines.append("")

for name, data, original_path, original_sha in embedded:
    lines.extend(
        [
            f"% Embedded-Source: {original_path} SHA256 {original_sha}",
            rf"\begin{{filecontents*}}{{{name}}}",
            data.decode("utf-8").removesuffix("\n"),
            r"\end{filecontents*}",
            "",
        ]
    )

lines.extend(
    [
        r"\documentclass[11pt,a4paper,openany]{memoir}",
        r"\newcommand{\olpath}{.}",
        r"\usepackage{fontspec}",
        r"\ifLuaTeX",
        r"\setmainfont{Nirmala UI}[Script=Tamil,Renderer=HarfBuzz,WordSpace=1.3,ItalicFont={Nirmala UI},ItalicFeatures={FakeSlant=0.15},FontFace={m}{sc}{Font={Nirmala UI}},FontFace={m}{scit}{Font={Nirmala UI},FakeSlant=0.15}]",
        r"\setsansfont{Nirmala UI}[Script=Tamil,Renderer=HarfBuzz,WordSpace=1.3]",
        r"\else",
        r"\setmainfont{Nirmala UI}[Script=Tamil,Renderer=OpenType,WordSpace=1.3,ItalicFont={Nirmala UI},ItalicFeatures={FakeSlant=0.15},FontFace={m}{sc}{Font={Nirmala UI}},FontFace={m}{scit}{Font={Nirmala UI},FakeSlant=0.15}]",
        r"\setsansfont{Nirmala UI}[Script=Tamil,Renderer=OpenType,WordSpace=1.3]",
        r"\fi",
        r"\setmonofont{Consolas}",
        r"\input{olt-open-logic.sty}",
        r'\ifXeTeX\XeTeXlinebreaklocale "ta"\XeTeXlinebreakskip=0pt plus 1pt\XeTeXgenerateactualtext=1\fi',
        r"\setlrmarginsandblock{25mm}{25mm}{*}",
        r"\setulmarginsandblock{22mm}{25mm}{*}",
        r"\checkandfixthelayout",
        r"\linespread{1.17}",
        r"\emergencystretch=2em",
        r"\hbadness=6000",
        r"\input{olt-tamil-config.sty}",
        r"\input{olt-tamil-pdf-math.sty}",
        r"\tagtrue{novice,math,compsci,FOL,TMs,lambda,prvTrue,prvFalse,prvEx,prvAll,prfSC,prfND,prfAX,prfTab}",
        r"\addto\captionsenglish{\renewcommand{\partname}{பகுதி}\renewcommand{\chaptername}{அத்தியாயம்}\renewcommand{\contentsname}{பொருளடக்கம்}\renewcommand{\bibname}{மேற்கோள் நூல்}\renewcommand{\proofname}{நிறுவல்}\renewcommand{\figurename}{படம்}}",
        r"\setlocalecaption{english}{definition}{வரையறை}",
        r"\setlocalecaption{english}{example}{எடுத்துக்காட்டு}",
        r"\setlocalecaption{english}{lemma}{துணைத்தேற்றம்}",
        r"\setlocalecaption{english}{proposition}{கூற்று}",
        r"\setlocalecaption{english}{corollary}{தொடர்விளைவு}",
        r"\setlocalecaption{english}{problem}{பயிற்சி}",
        r"\setlocalecaption{english}{problems}{பயிற்சிகள்}",
        r"\setlocalecaption{english}{theorem}{தேற்றம்}",
        r"\setlocalecaption{english}{remark}{குறிப்பு}",
        r"\setlocalecaption{english}{axiom}{அடிகோள்}",
        r"\setlocalecaption{english}{note}{குறிப்பு}",
        r"\setlocalecaption{english}{case}{நிலை}",
        r"\setlocalecaption{english}{convention}{மரபு}",
        r"\setlocalecaption{english}{history}{வரலாற்றுக் குறிப்புகள்}",
        r"\hypersetup{pdftitle={OpenLogic தமிழ் — 203 அலகுகளின் திரட்டப்பட்ட வாசிப்புப் பதிப்பு},pdfauthor={OpenLogic Tamil translation programme},pdfsubject={Machine translation; seven accepted readers; 203 counted units from 722 frozen units}}",
        r"\makeatletter",
    ]
)

for path in sorted(translation_paths):
    source_path = path.removeprefix("translation/")
    directory = PurePosixPath(source_path).parent.as_posix()
    name = unit_names[path]
    lines.append(
        rf"\expandafter\def\csname TA@file@{source_path}\endcsname{{{name}}}"
    )
    lines.append(
        rf"\expandafter\def\csname TA@dir@{source_path}\endcsname{{{directory}}}"
    )

lines.extend(
    [
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
    ]
)

for argument, path in sorted(asset_argument_to_path.items()):
    flat = asset_names[path]
    expanded_argument = argument.replace(r"\olpath", ".")
    for key in sorted({argument, expanded_argument}):
        lines.append(rf"\expandafter\def\csname TA@asset@{key}\endcsname{{{flat}}}")

lines.extend(
    [
        r"\RenewDocumentCommand\olasset{O{\olphotowidth} m}{%",
        r"  \edef\TAassetkey{#2}%",
        r"  \ifcsname TA@asset@\TAassetkey\endcsname",
        r"    \centerline{\expandafter\includegraphics\expandafter[width=#1]{\csname TA@asset@\TAassetkey\endcsname}}%",
        r"  \else\PackageError{OpenLogic Tamil}{Embedded asset not found: #2}{}\fi}",
        r"\makeatother",
        r"\AtBeginEnvironment{align*}{\fontsize{9.5}{12}\selectfont}",
        r"\AtBeginEnvironment{multline*}{\fontsize{9.5}{12}\selectfont}",
        r"\AtBeginEnvironment{eqnarray*}{\fontsize{9.5}{12}\selectfont}",
        r"\begin{document}",
        r"\raggedright",
        r"\raggedbottom",
        r"\pagestyle{plain}",
        r"\chapter*{திறந்த தருக்கவியல்}",
        r"\noindent தமிழ் மொழிபெயர்ப்பு — 203 அலகுகளின் திரட்டப்பட்ட மூலப்பதிப்பு",
        "",
        r"\noindent மூல ஆசிரியர்கள்: Open Logic Project. இந்தப் பிரதி இயந்திர மொழிபெயர்ப்பு; சுயாதீன மனிதச் சரிபார்ப்பு செய்யப்பட்டதாகக் கூறப்படவில்லை. முழுப் பதிப்பு இன்னும் தயாராகவில்லை.",
        "",
        r"\noindent இந்த ஒரே கோப்பு ஏழு ஏற்றுக்கொள்ளப்பட்ட வாசிப்புப் பகுதிகளின் 203 எண்ணப்பட்ட அலகுகளையும், அவற்றை இணைக்கத் தேவையான மூன்று அமைப்புசார் அத்தியாய இயக்கிகளையும் உட்பொதிக்கிறது. மொழிபெயர்ப்பு நிரலின் 343 அலகுகள் அனைத்தையும் உள்ளடக்கியதாக இது கூறவில்லை.",
        r"\clearpage",
        r"\tableofcontents*",
    ]
)

for section_index, section in enumerate(SECTIONS, start=1):
    lines.extend(
        [
            r"\cleardoublepage",
            rf"\part*{{{section['title']}}}",
            rf"\addcontentsline{{toc}}{{part}}{{{section['title']}}}",
        ]
    )
    for root in section["roots"]:
        lines.append(rf"\TAIncludePath{{{root.removeprefix('translation/')}}}")
    for note in section.get("notes", []):
        lines.append(rf"\input{{{note_names[note]}}}")
    if section.get("bibliography"):
        lines.extend(
            [
                r"\nocite{Frege1953}",
                r"\bibliographystyle{olt-natbib-oup}",
                r"\bibliography{olt-open-logic}",
            ]
        )

lines.extend([r"\end{document}", ""])
OUTPUT.parent.mkdir(exist_ok=True)
OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")

artifact = OUTPUT.read_bytes()
assert b"OLP-0347" not in artifact and b"OLP-0352" not in artifact
assert b"C:\\Users" not in artifact and b"c:\\users" not in artifact.lower()

# Verify that every embedded original translation block is byte-identical to
# the release commit. Support style blocks may contain only path rewrites.
artifact_text = artifact.decode("utf-8")
for path, flat in unit_names.items():
    begin = f"\\begin{{filecontents*}}{{{flat}}}\n"
    end = r"\end{filecontents*}"
    start = artifact_text.index(begin) + len(begin)
    finish = artifact_text.index(end, start)
    extracted = artifact_text[start:finish].encode("utf-8")
    assert extracted == payloads[path], path

executable = artifact_text[artifact_text.rindex(r"\documentclass") :]
assert "../translation" not in executable and "../upstream" not in executable
assert len(re.findall(r"^% Reader-Unit: OLP-\d{4} ", artifact_text, re.MULTILINE)) == 203
assert len(re.findall(r"^% Structural-Driver: OLP-\d{4} ", artifact_text, re.MULTILINE)) == 3

receipt = {
    "schema": "openlogic-tamil-cumulative-tex-source/1",
    "release_commit": RELEASE_COMMIT,
    "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
    "reader_scope": {
        "counted_reader_units": 203,
        "structural_chapter_drivers": sorted(structural_drivers),
        "embedded_translation_files": 206,
        "component_readers": 7,
        "programme_accepted_units": 343,
        "programme_total_units": 722,
        "unaccepted_units_included": [],
    },
    "completeness": {
        "exact_translation_blobs_verified": len(translation_paths),
        "embedded_project_support_files": len(SUPPORT),
        "embedded_editorial_note_files": len(note_paths),
        "embedded_diagram_sources": len(asset_paths),
        "project_local_inputs_generated_by_asset": True,
        "external_requirements": "Standard TeX packages plus Nirmala UI and Consolas fonts",
        "pdf_rebuilt_for_packaging": False,
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
            "translation_sha256": sha256(payloads[embedded_units[unit_id]]),
        }
        for unit_id in sorted(reader_units)
    ],
    "structural_driver_files": [
        {
            "unit_id": unit_id,
            "source_path": embedded_units[unit_id],
            "translation_sha256": sha256(payloads[embedded_units[unit_id]]),
        }
        for unit_id in sorted(structural_drivers)
    ],
}
receipt_path = STATE / "CUMULATIVE-TEX-SOURCE.json"
receipt_path.write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(receipt["asset"], ensure_ascii=False, indent=2))
