# OpenLogic — தமிழ் (ta-Taml-IN) — English reference

For the reader-facing Tamil edition information, see [தமிழ் முகப்பு](README.md).

India-standard Tamil translation of the [Open Logic Text](https://openlogicproject.org/).
Programme catalogue: [OpenLogic translations](https://github.com/KokunoYumeto/OpenLogic-translations).

All **722 frozen content units** are translated and aligned in 2,242 source/target segments. One complete reader contains 695 main units followed by a labelled appendix with the other 27 source units. Its PDF and reflowable EPUB 3.3 editions are validated.

- [Complete 722-unit Tamil PDF](readers/openlogic-ta-Taml-IN-complete-722.pdf): 1,227 A4 pages with audited internal links between the main text and appendix.
- [Single full-text editable LaTeX for all 722 units](https://github.com/KokunoYumeto/OpenLogic-ta-Taml-IN/releases/download/v1.1.1-complete-722/02-openlogic-ta-Taml-IN-complete-722.tex): every translated unit body is present directly in this file; a [repository copy](build/tamil-complete-722-direct.tex) is also available.
- [Complete editable source archive](https://github.com/KokunoYumeto/OpenLogic-ta-Taml-IN/releases/download/v1.1.1-complete-722/03-openlogic-ta-Taml-IN-complete-source.zip): the single full-text LaTeX, both component full-text files, modular Tamil and frozen English sources, figures, bibliography, build scripts and evidence.
- [Complete 722-unit Tamil EPUB](readers/openlogic-ta-Taml-IN-complete-722.epub): reflowable text, native MathML, navigation and appendix.

The separately downloadable component volumes remain available:

- [Complete main Tamil PDF](readers/tamil-complete.pdf): 1,171 A4 pages.
- [Main Tamil EPUB](readers/openlogic-ta-Taml-IN-complete-main.epub): 695 units.
- [Full-text editable main LaTeX](build/tamil-complete-direct.tex).
- [Tamil source companion PDF](readers/tamil-source-companion.pdf): 56 A4 pages of alternate source sections and explanatory material.
- [Companion Tamil EPUB](readers/openlogic-ta-Taml-IN-complete-companion.epub): the remaining 27 units.
- [Full-text editable companion LaTeX](build/tamil-source-companion-direct.tex). The complete source archive carries both files' build dependencies.

For cross-volume links to work in the separate PDFs, save them together under the exact filenames `tamil-complete.pdf` and `tamil-source-companion.pdf`. The 722-unit PDF uses internal links.

## Earlier component readers

The first tagged reader remains the complete **Sets chapter: 7 source units, 6 sections, 69 aligned segments**.
The wider 51-unit reader is a verified interim edition: 99 A4 pages covering Sets, Relations, Functions, Size of Sets, number-system construction and Infinite Sets. Patch release v0.2.1 replaces five references to chapters outside this reader with descriptive Tamil fallbacks; the live references return automatically when those destinations are included in a later complete edition. It passed a three-pass guarded XeLaTeX/BibTeX build, font embedding and copy/search checks, plus visual inspection of every rendered page.
Fourteen verified component readers cover 257 distinct units. Each component passed a guarded TeX build, embedded-font and copy/search checks, and all-page visual inspection. The existing 384-page cumulative reader concatenates the first seven accepted components (203 units) in frozen-source order, adds section bookmarks, and preserves 626 checked links. The six set-theory readers and the Reference reader are supplied separately. The Cardinals, Cardinal Arithmetic, Choice, Proofs, Induction, Biographies and History of Set Theory chapters are editable source; their PDF readers have not yet been built.

## Read and edit

- [கணங்கள் — Tamil Sets chapter PDF](readers/sets-ta-Taml-IN.pdf): 13 pages including attribution and a separate edition note.
- [கணங்கள் முதல் முடிவுறாத கணங்கள் வரை — combined Tamil PDF](readers/sets-functions-relations-ta-Taml-IN.pdf): 99 pages, 51 source units and six chapters, including separate source-correction notes.
- [நிரூபண முறைகள் — proof-systems Tamil PDF](readers/proof-systems-sequent-natural-deduction-tableaux-ta-Taml-IN.pdf): 89 pages and 49 source units covering the proof-systems survey, sequent calculus, natural deduction and tableaux.
- [அடிகோள் வருவித்தல் — axiomatic-deduction Tamil PDF](readers/axiomatic-deduction-ta-Taml-IN.pdf): 17 pages and 14 source units.
- [கணிப்புத்தன்மை — computability Tamil PDF](readers/computability-ta-Taml-IN.pdf): 63 pages and 44 source units.
- [டியூரிங் பொறிகள் — Turing-machines Tamil PDF](readers/turing-machines-ta-Taml-IN.pdf): 50 pages and 22 source units.
- [முழுமையின்மையும் எண்கணிதமாக்கலும் — Tamil PDF](readers/incompleteness-arithmetization-ta-Taml-IN.pdf): 40 pages and 12 source units.
- [ராபின்சன் Q இல் பிரதிநிதித்துவப்படுத்தல் — Tamil PDF](readers/representability-in-q-ta-Taml-IN.pdf): 26 pages and 11 source units.
- [படிநிலைமுறைக் கணக் கருத்தாக்கம் — set-theory story Tamil PDF](readers/set-theory-iterative-conception-ta-Taml-IN.pdf): 12 pages and 8 source units, including both cumulative-hierarchy diagrams and Frege’s Basic Law V appendix.
- [செர்மேலோ கணக் கோட்பாட்டை நோக்கிய படிகள் — Zermelo-axioms Tamil PDF](readers/set-theory-zermelo-axioms-ta-Taml-IN.pdf): 10 source units covering Separation, Union, Pairs, Powersets, Infinity, $Z^-$, natural-number encodings and arbitrary intersections.
- வரிசையெண்கள்: [17-page Tamil PDF](readers/set-theory-ordinals-ta-Taml-IN.pdf) → [complete-text single-file LaTeX](release/openlogic-ta-Taml-IN-set-theory-ordinals-11-units.tex) → [pinned complete source ZIP](https://codeload.github.com/KokunoYumeto/OpenLogic-ta-Taml-IN/zip/449c3bfb90971941eb59715863f31e8e752434ba). The chapter covers 11 source units: well-orders, order-isomorphisms, von Neumann ordinals, transfinite induction, Replacement, order types, successor and limit ordinals, and the Burali–Forti paradox.
- Stages and ranks: [12-page Tamil PDF](readers/set-theory-stages-ranks-ta-Taml-IN.pdf) → [complete-text single-file LaTeX](release/openlogic-ta-Taml-IN-set-theory-stages-ranks-7-units.tex) → [pinned complete source ZIP](https://codeload.github.com/KokunoYumeto/OpenLogic-ta-Taml-IN/zip/3d20aea0980eddfb823c4e4c9aedf84b4eaedbe3). The seven units cover the $V_\alpha$ hierarchy, transfinite recursion, stage properties, Foundation and Regularity, $\ZF$, set rank and membership induction.
- [மாற்றீடும் பிரதிபலிப்பும் — Replacement-and-Reflection Tamil PDF](readers/set-theory-replacement-reflection-ta-Taml-IN.pdf): 16 pages and 9 source units covering the strength and justification of Replacement, limitation of size, absolute infinity, Reflection, the weak-reflection equivalence and finite axiomatizability.
- Ordinal Arithmetic: [11-page Tamil PDF](readers/set-theory-ordinal-arithmetic-ta-Taml-IN.pdf) → [editable reader master](build/tamil-set-theory-ord-arithmetic.tex) → [six-unit Tamil TeX chapter](translation/content/set-theory/ord-arithmetic/ord-arithmetic.tex), covering addition, rank examples, multiplication and exponentiation.
- [கண அளவெண்கள் — editable Cardinals Tamil TeX](translation/content/set-theory/cardinals/cardinals.tex): six accepted units, covering Cantor’s Principle, cardinals as ordinals, the ZFC milestone, finite and infinite cardinals, and Hume’s Principle; reader PDF pending.
- [கண அளவெண் எண்கணிதம் — editable Cardinal Arithmetic Tamil TeX](translation/content/set-theory/card-arithmetic/card-arithmetic.tex): six accepted units, covering cardinal operations, simplification, exponentiation, the continuum hypothesis and fixed points; reader PDF pending.
- [தேர்வு — editable Choice Tamil TeX](translation/content/set-theory/choice/choice.tex): nine accepted units, covering Tarski–Scott, Hartogs, Well-Ordering, Countable Choice, the Banach–Tarski paradox and Vitali's circle construction; reader PDF pending.
- [நிறுவல்கள் — editable Proofs Tamil TeX](translation/content/methods/proofs/proofs.tex): twelve accepted units including the Methods part opener, covering definitions, inference patterns, worked examples, contradiction, reading proofs and study guidance; reader PDF pending.
- [தொகுத்தறிதல் — editable Induction Tamil TeX](translation/content/methods/induction/induction.tex): seven accepted units covering induction on naturals, strong induction, inductive definitions, structural induction, relations and functions; reader PDF pending.
- [வாழ்க்கை வரலாறுகள் — editable Biographies Tamil TeX](translation/content/history/biographies/biographies.tex): thirteen accepted units including the History part opener and eleven biographies from Cantor through Zermelo; reader PDF pending.
- [கணக் கோட்பாட்டின் வரலாறும் தொன்மக் கதைகளும் — editable History of Set Theory Tamil TeX](translation/content/history/set-theory/set-theory.tex): seven accepted units on infinitesimals, limits, Cantor’s correspondence and Hilbert’s space-filling curve. A visible edition note identifies the limits of the source’s informal curve argument; reader PDF pending.
- Reference alphabets: [5-page Tamil PDF](readers/reference-alphabets-ta-Taml-IN.pdf) → [editable reader master](build/tamil-reference-alphabets.tex) → [three-unit Tamil TeX](translation/content/reference/reference.tex). The Greek and Fraktur glyph pairings retain the frozen source.
- [203-unit cumulative Tamil reader](readers/openlogic-ta-Taml-IN-cumulative-reader-203-units.pdf): 384 A4 pages containing the seven accepted components above, in source order.
- Editable Tamil: `translation/content/`. Each accepted file retains its frozen relative path and stable OLP unit binding in `evidence/`.
- Frozen, unchanged English sources and original components: upstream/.
- Reader master: build/tamil-batch001.tex.
- Combined 51-unit checkpoint master: build/tamil-sfr.tex.
- Propositional syntax-and-semantics source master: build/tamil-pl-syn.tex.
- Proof-systems, sequent-calculus, natural-deduction and tableaux reader master: build/tamil-proof-systems-sequent.tex.

Machine translation and corrections of the first 570 units were performed with OpenAI Codex — GPT-5.6 Sol, Ultra effort. Translation of the remaining 152 units, later corrections, complete-edition assembly and automated checks were performed with OpenAI Codex — GPT-6 Sol, Ultra effort. The split is verified against this task's session metadata. Independent human or native-speaker approval is not claimed. All 722 units have source/target segment coverage across 2,242 segments, and 1,457 semantic reverse samples were checked. The 1,227 pages of the two complete PDFs passed a low-resolution scan for empty pages, edge clipping, and very low ink coverage; contact sheets and selected full pages were visually inspected. This is not individual human review of every glyph. Source corrections are documented in [the source-correction ledger](evidence/source-corrections.json).

PDF text reuse has measured limitations. Poppler finds seven tested Tamil phrases; all 26 cross-volume links became local links in the combined PDF. One visible nonmembership symbol extracts out of formula order, and other PDF engines may duplicate Tamil syllables or lose spacing. Use the editable formulas for exact mathematical reuse. These PDFs are not claimed to be tagged or universally accessible to screen readers.

## Build

Use a Unicode-capable TeX distribution with XeLaTeX, memoir, the upstream dependencies, fontspec and accsupp. The readers use the Windows system fonts Nirmala UI and Consolas; font files are not redistributed.
Run build/build-tamil.ps1 on Windows. It holds Global\InterlanguageTeXSlotV1 over the captured TeX process tree, every pass, optional BibTeX and log checks. A busy slot returns without starting an engine. The default master produces build/tamil-batch001.pdf. For the combined Sets-through-Infinite-Sets reader, run `build/build-tamil.ps1 -Master tamil-sfr.tex -Passes 3 -BibTeX -ReceiptName TEX-SFR-RECEIPT`. For the proof-systems reader, run `build/build-tamil.ps1 -Master tamil-proof-systems-sequent.tex -Passes 2 -ReceiptName TEX-PROOF-SYSTEMS-TABLEAUX-RECEIPT`. For the iterative-conception chapter, run `build/build-tamil.ps1 -Master tamil-set-theory-story.tex -Passes 3 -BibTeX -ReceiptName TEX-SET-THEORY-STORY-RECEIPT`. For the Zermelo-axioms chapter, run `build/build-tamil.ps1 -Master tamil-set-theory-z.tex -Passes 3 -BibTeX -ReceiptName TEX-SET-THEORY-Z-RECEIPT`. For the ordinals chapter, run `build/build-tamil.ps1 -Master tamil-set-theory-ordinals.tex -Passes 3 -BibTeX -ReceiptName TEX-SET-THEORY-ORDINALS-RECEIPT`. For the stages-and-ranks chapter, run `build/build-tamil.ps1 -Master tamil-set-theory-spine.tex -Passes 3 -BibTeX -ReceiptName TEX-SET-THEORY-SPINE-RECEIPT`. For the Replacement-and-Reflection chapter, run `build/build-tamil.ps1 -Master tamil-set-theory-replacement.tex -Passes 3 -BibTeX -ReceiptName TEX-SET-THEORY-REPLACEMENT-RECEIPT`.

For a **fresh build from the source ZIP**, run `build/build-tamil.ps1 -Master tamil-complete.tex -Passes 3 -BibTeX -ReceiptName TEX-COMPLETE-RECEIPT`, then `build/build-tamil.ps1 -Master tamil-source-companion.tex -Passes 3 -ReceiptName TEX-COMPANION-RECEIPT` from the unpacked root. The companion imports the main volume's references and must be built second. Then run `python build/assemble-complete-722-reader.py --validation current-build` and `python build/audit-complete-722-reader.py --main-pdf build/tamil-complete.pdf --companion-pdf build/tamil-source-companion.pdf`. The assembler reads those freshly built PDFs and their guarded receipts in `build/`, validates current page counts, and rewrites all component-local and cross-volume links. It does not demand the historical PDF hashes, which can differ because of TeX-generated metadata. This route needs `pypdf` and `pdftotext`.

To **reproduce the exact released combined PDF**, put `tamil-complete.pdf` and `tamil-source-companion.pdf` from the same `v1.1.1-complete-722` release in `readers/` under those names. Run `python build/assemble-complete-722-reader.py --validation release-pinned`, then `python build/audit-complete-722-reader.py`. This route checks the published component hashes against the bundled page-scan evidence and produces the combined release bytes. The single full-text TeX can be regenerated with `python build/assemble-complete-722-tex.py`; its audit is `build/tamil-complete-722-direct.qa.json`. The released combined PDF is assembled from the two component TeX builds, while the one-file TeX is provided for editing and alternative builds.

`build/build-epub-html.ps1` generates TeX4ht HTML under the global TeX mutex. From the unpacked source ZIP, the full EPUB sequence is:

```powershell
Copy-Item .\build\tamil-complete.pdf .\readers\tamil-complete.pdf
$epubcheckJar = 'C:\path\to\epubcheck-5.3.0.jar'
.\build\build-epub-html.ps1 -Master tamil-complete.tex -ReaderSlug complete-main -Engine xelatex -ProcessTimeoutMinutes 45
python epub/package_epub.py complete-main
python epub/audit_epub.py complete-main --epubcheck-jar $epubcheckJar
.\build\build-epub-html.ps1 -Master tamil-source-companion.tex -ReaderSlug complete-companion -Engine xelatex -ImportExternalLabels -ProcessTimeoutMinutes 30
python epub/package_epub.py complete-companion
python epub/audit_epub.py complete-companion --epubcheck-jar $epubcheckJar
python build/assemble-complete-722-epub.py
python epub/audit_epub.py complete-722 --epubcheck-jar $epubcheckJar
```

Run the PDF build sequence above first, and adjust `$epubcheckJar` to an installed EPUBCheck 5.3.0 JAR. These commands write local receipts to `build/`. The frozen manifest and accepted component audits are included under `evidence/`. To reassemble the released combined EPUB without rerunning TeX4ht, place the two component EPUBs and the complete PDF from this release in `readers/`, then run the last two commands. The assembler verifies each component against its packaged audit hash; the PDF supplies the rendered vocabulary comparison.

For the Reference alphabets reader, run `build/build-tamil.ps1 -Master tamil-reference-alphabets.tex -Passes 3 -ReceiptName TEX-REFERENCE-ALPHABETS-RECEIPT`.

After the seven accepted component PDFs and their QA receipts are present, `python build/package-cumulative-reader.py` losslessly assembles the cumulative reader and `python build/qa-cumulative-reader.py` verifies page streams, geometry, navigation, links, fonts, extraction and the inspected render set. These scripts do not invoke TeX.

## Source and evidence

English revision: 9620cc73f9c8e0ad003c514a5d3748f29611c4c0 of [OpenLogicProject/OpenLogic](https://github.com/OpenLogicProject/OpenLogic/tree/9620cc73f9c8e0ad003c514a5d3748f29611c4c0).
All 722 content-file hashes were checked against the frozen manifest. Stable OLP identifiers and original paths remain in the evidence.

The evidence folder contains the source manifest, actual per-segment canon-use records, terminology decisions and scoped QA. The [canonical decision release](evidence/translation-decisions/START_HERE.md) provides the shared cross-language schema, full and priority human-readable views, one CSV row per exact occurrence, and schema-valid machine JSON. Tamil Nadu SCERT, Tamil Virtual Academy and university originals informed the work. Direct technical attestation, general scholarly register and provisional choices are distinguished. The accompanying variant assessment recommends one India-standard Tamil-script edition with international mathematical notation on the current evidence.

OpenLogic's natural numbers include zero. The source convention is retained and explained in a separate Tamil edition note, because the consulted school text uses a different convention. New editorial or learner material is kept separate from the faithful source.

The complete PDF and EPUB, the two component volumes, and the editable source package are prepared. EPUBCheck 5.3.0 reported zero errors and warnings for all three EPUBs. Terminology can be refined through later independent review.

## Attribution and license

Original text: The Open Logic Project, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Tamil translation and new edition notes: OpenLogic Tamil translation programme, CC BY 4.0.
Changes include translation, Tamil inflection support, layout and PDF extraction support. The original English source and component notices are preserved. See [NOTICE.md](NOTICE.md) and [the original license](upstream/LICENSE.md).
