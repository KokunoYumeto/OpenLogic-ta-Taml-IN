from __future__ import annotations

from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import subprocess


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-ta-Taml-IN")
SOURCE_COMMIT = "449c3bfb90971941eb59715863f31e8e752434ba"
ROOT = "translation/content/set-theory/ordinals/ordinals.tex"
OUTPUT = REPO / "release" / "openlogic-ta-Taml-IN-set-theory-ordinals-11-units.tex"

SUPPORT = {
    "upstream/sty/open-logic.sty": "olt-ord-open-logic.sty",
    "upstream/open-logic-locale.sty": "olt-ord-open-logic-locale.sty",
    "upstream/sty/open-logic-referencing.sty": "olt-ord-open-logic-referencing.sty",
    "upstream/sty/open-logic-formulas.sty": "olt-ord-open-logic-formulas.sty",
    "upstream/sty/open-logic-tokenize.sty": "olt-ord-open-logic-tokenize.sty",
    "upstream/sty/open-logic-selective.sty": "olt-ord-open-logic-selective.sty",
    "upstream/sty/bussproofs-extra.sty": "olt-ord-bussproofs-extra.sty",
    "upstream/sty/ptolemaicastronomy.sty": "olt-ord-ptolemaicastronomy.sty",
    "upstream/open-logic-config.sty": "olt-ord-open-logic-config.sty",
    "upstream/open-logic-envs.sty": "olt-ord-open-logic-envs.sty",
    "translation/tamil-config.sty": "olt-ord-tamil-config.sty",
    "translation/tamil-pdf-math.sty": "olt-ord-tamil-pdf-math.sty",
    "upstream/bib/open-logic.bib": "olt-ord-open-logic.bib",
    "upstream/bib/natbib-oup.bst": "olt-ord-natbib-oup.bst",
}

IMPORT_RE = re.compile(
    r"\\olimport(?P<star>\*)?(?:\[(?P<directory>[^\]]+)\])?"
    r"\{(?P<name>[^}]+)\}(?:\[(?P<section>[^\]]+)\])?"
)


def git_blob(path: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{SOURCE_COMMIT}:{path}"], cwd=REPO
    )


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
manifest_by_translation_path = {
    "translation/" + row["source_path"]: row for row in manifest.values()
}

translation_paths: set[str] = set()


def collect_translation(path: str) -> None:
    path = normalized(PurePosixPath(path))
    if path in translation_paths:
        return
    assert path in manifest_by_translation_path, path
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
embedded_units = {
    manifest_by_translation_path[path]["unit_id"]: path
    for path in translation_paths
}
expected_units = {f"OLP-{number:04d}" for number in range(547, 558)}
assert set(embedded_units) == expected_units
assert len(translation_paths) == 11

unit_names = {
    path: f"olt-ord-unit-{manifest_by_translation_path[path]['unit_id']}.tex"
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
    mandatory_input = re.compile(
        r"\\input\{\\olpath/(?:sty/|open-logic-(?:locale|config|envs))"
    )
    assert not mandatory_input.search(text), path
    return text.encode("utf-8")


embedded: list[tuple[str, bytes, str, str]] = []
for path, name in SUPPORT.items():
    original = git_blob(path)
    payload = rewritten_support(path) if path.endswith(".sty") else original
    embedded.append((name, payload, path, sha256(original)))
for path, name in sorted(unit_names.items()):
    payload = git_blob(path)
    embedded.append((name, payload, path, sha256(payload)))

assert len({name for name, _, _, _ in embedded}) == len(embedded)
for name, payload, path, _ in embedded:
    assert b"\\end{filecontents*}" not in payload, path
    assert payload.endswith(b"\n"), path
    assert "/" not in name and "\\" not in name and ".." not in name

lines = [
    "% OpenLogic Tamil ordinals complete-text source bundle",
    f"% Frozen accepted source commit: {SOURCE_COMMIT}",
    "% Scope: OLP-0547 through OLP-0557, all 11 units of the Ordinals chapter.",
    "% Every Tamil unit below is byte-identical to its accepted Git blob; its SHA-256 is recorded.",
    "% Save this file under any .tex filename and run XeLaTeX, BibTeX, then XeLaTeX twice.",
    "% Standard TeX packages and the Nirmala UI and Consolas fonts are required; no project-local input is required.",
    "%",
]
for unit_id in sorted(embedded_units):
    path = embedded_units[unit_id]
    lines.append(f"% Reader-Unit: {unit_id} {path} {sha256(git_blob(path))}")
lines.append("")

for name, payload, original_path, original_sha in embedded:
    lines.extend(
        [
            f"% Embedded-Source: {original_path} SHA256 {original_sha}",
            rf"\begin{{filecontents*}}{{{name}}}",
            payload.decode("utf-8").removesuffix("\n"),
            r"\end{filecontents*}",
            "",
        ]
    )

mapping_lines = [r"\makeatletter"]
for path in sorted(translation_paths):
    source_path = path.removeprefix("translation/")
    directory = PurePosixPath(source_path).parent.as_posix()
    mapping_lines.append(
        rf"\expandafter\def\csname TA@file@{source_path}\endcsname{{{unit_names[path]}}}"
    )
    mapping_lines.append(
        rf"\expandafter\def\csname TA@dir@{source_path}\endcsname{{{directory}}}"
    )
mapping_lines.extend(
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
        r"\makeatother",
    ]
)
mapping = "\n".join(mapping_lines)

master = git_blob("build/tamil-set-theory-ordinals.tex").decode("utf-8")
master = master.replace(r"\newcommand{\olpath}{../upstream}", r"\newcommand{\olpath}{.}")
master = master.replace(r"\input{\olpath/sty/open-logic.sty}", r"\input{olt-ord-open-logic.sty}")
master = master.replace(r"\input{../translation/tamil-config.sty}", r"\input{olt-ord-tamil-config.sty}")
master = master.replace(
    r"\input{../translation/tamil-pdf-math.sty}",
    r"\input{olt-ord-tamil-pdf-math.sty}" + "\n" + mapping,
)
master = master.replace(
    r"\subfile{../translation/content/set-theory/ordinals/ordinals.tex}",
    r"\TAIncludePath{content/set-theory/ordinals/ordinals.tex}",
)
master = master.replace(
    r"\bibliographystyle{../upstream/bib/natbib-oup}",
    r"\bibliographystyle{olt-ord-natbib-oup}",
)
master = master.replace(
    r"\bibliography{../upstream/bib/open-logic}",
    r"\bibliography{olt-ord-open-logic}",
)
assert master.count(r"\TAIncludePath{content/set-theory/ordinals/ordinals.tex}") == 1
assert "../translation" not in master and "../upstream" not in master

lines.append(master.removesuffix("\n"))
lines.append("")
OUTPUT.parent.mkdir(exist_ok=True)
OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")

artifact = OUTPUT.read_bytes()
artifact_text = artifact.decode("utf-8")
assert b"C:\\Users" not in artifact and b"c:\\users" not in artifact.lower()
assert len(re.findall(r"^% Reader-Unit: OLP-\d{4} ", artifact_text, re.MULTILINE)) == 11

for path, flat in unit_names.items():
    begin = f"\\begin{{filecontents*}}{{{flat}}}\n"
    end = r"\end{filecontents*}"
    start = artifact_text.index(begin) + len(begin)
    finish = artifact_text.index(end, start)
    extracted = artifact_text[start:finish].encode("utf-8")
    assert extracted == git_blob(path), path

receipt = {
    "schema": "openlogic-tamil-ordinals-tex-source/1",
    "source_commit": SOURCE_COMMIT,
    "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
    "scope": {
        "first_unit": "OLP-0547",
        "last_unit": "OLP-0557",
        "counted_reader_units": 11,
        "embedded_translation_files": 11,
        "programme_accepted_units_at_source_commit": 554,
        "programme_total_units": 722,
        "unaccepted_units_included": [],
    },
    "completeness": {
        "exact_translation_blobs_verified": 11,
        "embedded_project_support_files": len(SUPPORT),
        "project_local_inputs_generated_by_asset": True,
        "external_requirements": "Standard TeX packages plus Nirmala UI and Consolas fonts",
        "accepted_pdf_replaced": False,
    },
    "reader_master": {
        "source_path": "build/tamil-set-theory-ordinals.tex",
        "source_sha256": sha256(git_blob("build/tamil-set-theory-ordinals.tex")),
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
(STATE / "SET-THEORY-ORDINALS-TEX-SOURCE.json").write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)
print(json.dumps(receipt["asset"], ensure_ascii=False, indent=2))
