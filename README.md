# OpenLogic — தமிழ் (ta-Taml-IN)

India-standard Tamil translation of the [Open Logic Text](https://openlogicproject.org/).
Programme catalogue: [OpenLogic translations](https://github.com/KokunoYumeto/OpenLogic-translations).

The full edition is in progress. **51 of 722 frozen content units are drafted, source-aligned and textually audited** (Sets through Infinite Sets).
The first tagged reader remains the complete **Sets chapter: 7 source units, 6 sections, 69 aligned segments**.
The wider 51-unit reader is a verified interim edition: 99 A4 pages covering Sets, Relations, Functions, Size of Sets, number-system construction and Infinite Sets. It passed a three-pass guarded XeLaTeX/BibTeX build, font embedding and copy/search checks, plus visual inspection of every rendered page.

## Read and edit

- [கணங்கள் — Tamil Sets chapter PDF](readers/sets-ta-Taml-IN.pdf): 13 pages including attribution and a separate edition note.
- [கணங்கள் முதல் முடிவுறாத கணங்கள் வரை — combined Tamil PDF](readers/sets-functions-relations-ta-Taml-IN.pdf): 99 pages, 51 source units and six chapters, including separate source-correction notes.
- Editable Tamil: translation/content/sets-functions-relations/.
- Frozen, unchanged English sources and original components: upstream/.
- Reader master: build/tamil-batch001.tex.
- Combined 51-unit checkpoint master: build/tamil-sfr.tex.

This is machine translation with source comparison and author semantic review. Independent human or native-speaker approval is not claimed.
Both readers were checked page by page for Tamil shaping, formulas, diagrams, references and clipping. All 51 current units pass mathematical, citation, identifier and structural parity checks or a specifically audited source correction. The evidence records 456 aligned segments and the exact 99-page PDF hash.

PDF text reuse has measured limitations. Poppler correctly extracts five tested Tamil phrases and representative union, intersection and Cartesian-product formulas. PyMuPDF duplicates some Tamil syllables or loses spacing. Composite negation symbols may still split during extraction in some contexts; blackboard number-set letters may extract as ordinary letters. Use the editable formulas for exact mathematical reuse. This is not a claim of tagged-PDF or universal screen-reader accessibility. A semantic reader remains part of the continuing full-edition work.

## Build

Use a Unicode-capable TeX distribution with XeLaTeX, memoir, the upstream dependencies, fontspec and accsupp. This first reader uses the Windows system fonts Nirmala UI and Consolas; font files are not redistributed.
Run build/build-tamil.ps1 on Windows. It holds Global\InterlanguageTeXSlotV1 over the captured TeX process tree, every pass, optional BibTeX and log checks. A busy slot returns without starting an engine. The default master produces build/tamil-batch001.pdf. For the combined reader, run `build/build-tamil.ps1 -Master tamil-sfr.tex -Passes 3 -BibTeX -ReceiptName TEX-SFR-RECEIPT`; the output is build/tamil-sfr.pdf.

## Source and evidence

English revision: 9620cc73f9c8e0ad003c514a5d3748f29611c4c0 of [OpenLogicProject/OpenLogic](https://github.com/OpenLogicProject/OpenLogic/tree/9620cc73f9c8e0ad003c514a5d3748f29611c4c0).
All 722 content-file hashes were checked against the frozen manifest. Stable OLP identifiers and original paths remain in the evidence.

The evidence folder contains the source manifest, actual per-segment canon-use records, terminology decisions and scoped QA. Its maintained translation-decisions.jsonl ledger gives experts exact review anchors, authorities checked, rationale, alternatives, uncertainty and concrete questions for every current substantive decision. Tamil Nadu SCERT, Tamil Virtual Academy and university originals informed the work. Direct technical attestation, general scholarly register and provisional choices are distinguished. Recovered laptop canon led to a newly verified integer/whole-number distinction; historical QA was not inherited.

OpenLogic's natural numbers include zero. The source convention is retained and explained in a separate Tamil edition note, because the consulted school text uses a different convention. New editorial or learner material is kept separate from the faithful source.

The ordinary reader graph and remaining wrappers, all remaining translation, full reader integration, ongoing terminology review and final publication verification are unfinished. A chapter release does not complete the programme.

## Attribution and license

Original text: The Open Logic Project, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Tamil translation and new edition notes: OpenLogic Tamil translation programme, CC BY 4.0.
Changes include translation, Tamil inflection support, layout and PDF extraction support. The original English source and component notices are preserved. See [NOTICE.md](NOTICE.md) and [the original license](upstream/LICENSE.md).
