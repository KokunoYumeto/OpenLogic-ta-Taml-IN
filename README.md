# OpenLogic — தமிழ் (ta-Taml-IN)

India-standard Tamil translation of the [Open Logic Text](https://openlogicproject.org/).
Programme catalogue: [OpenLogic translations](https://github.com/KokunoYumeto/OpenLogic-translations).

The full edition is in progress. **108 of 722 frozen content units are drafted, source-aligned and textually audited** (Sets through Infinite Sets, propositional syntax and semantics, the first-order proof-systems survey, and the complete sequent-calculus, natural-deduction and tableaux chapter sources).
The first tagged reader remains the complete **Sets chapter: 7 source units, 6 sections, 69 aligned segments**.
The wider 51-unit reader is a verified interim edition: 99 A4 pages covering Sets, Relations, Functions, Size of Sets, number-system construction and Infinite Sets. Patch release v0.2.1 replaces five references to chapters outside this reader with descriptive Tamil fallbacks; the live references return automatically when those destinations are included in a later complete edition. It passed a three-pass guarded XeLaTeX/BibTeX build, font embedding and copy/search checks, plus visual inspection of every rendered page.
The proof-systems reader is a second verified interim edition: 89 A4 pages covering 49 source units in the proof-systems survey, sequent calculus, natural deduction and tableaux. Its exact stable PDF passed a guarded two-pass XeLaTeX build, embedded-font and copy/search checks, and visual inspection of every page. Together, the 51-unit and 49-unit readers cover 100 distinct source units. Eight additional drafted propositional-logic units have textual and semantic QA but are not yet in an all-page visually verified reader.

## Read and edit

- [கணங்கள் — Tamil Sets chapter PDF](readers/sets-ta-Taml-IN.pdf): 13 pages including attribution and a separate edition note.
- [கணங்கள் முதல் முடிவுறாத கணங்கள் வரை — combined Tamil PDF](readers/sets-functions-relations-ta-Taml-IN.pdf): 99 pages, 51 source units and six chapters, including separate source-correction notes.
- [நிரூபண முறைகள் — proof-systems Tamil PDF](readers/proof-systems-sequent-natural-deduction-tableaux-ta-Taml-IN.pdf): 89 pages and 49 source units covering the proof-systems survey, sequent calculus, natural deduction and tableaux.
- Editable Tamil: translation/content/sets-functions-relations/, translation/content/propositional-logic/, translation/content/first-order-logic/proof-systems/, translation/content/first-order-logic/sequent-calculus/, translation/content/first-order-logic/natural-deduction/, and translation/content/first-order-logic/tableaux/.
- Frozen, unchanged English sources and original components: upstream/.
- Reader master: build/tamil-batch001.tex.
- Combined 51-unit checkpoint master: build/tamil-sfr.tex.
- Propositional syntax-and-semantics source master: build/tamil-pl-syn.tex.
- Proof-systems, sequent-calculus, natural-deduction and tableaux reader master: build/tamil-proof-systems-sequent.tex.

This is machine translation with source comparison and author semantic review. Independent human or native-speaker approval is not claimed.
Every stable reader was checked page by page for Tamil shaping, formulas, diagrams, references and clipping. All 108 drafted units pass mathematical, citation, identifier and structural parity checks or a specifically audited source correction. The evidence records 792 aligned segments and the exact accepted hashes of both wider readers. The 89-page proof-systems reader has no missing-glyph or undefined-reference warning and no literal `??` marker; three tiny overfull diagnostics are confined to internal signed-formula nodes and visual inspection confirms that no content reaches or crosses a page margin.

PDF text reuse has measured limitations. Poppler correctly extracts five tested Tamil phrases and representative union, intersection and Cartesian-product formulas. PyMuPDF duplicates some Tamil syllables or loses spacing. Composite negation symbols may still split during extraction in some contexts; blackboard number-set letters may extract as ordinary letters. Use the editable formulas for exact mathematical reuse. This is not a claim of tagged-PDF or universal screen-reader accessibility. A semantic reader remains part of the continuing full-edition work.

## Build

Use a Unicode-capable TeX distribution with XeLaTeX, memoir, the upstream dependencies, fontspec and accsupp. The readers use the Windows system fonts Nirmala UI and Consolas; font files are not redistributed.
Run build/build-tamil.ps1 on Windows. It holds Global\InterlanguageTeXSlotV1 over the captured TeX process tree, every pass, optional BibTeX and log checks. A busy slot returns without starting an engine. The default master produces build/tamil-batch001.pdf. For the combined Sets-through-Infinite-Sets reader, run `build/build-tamil.ps1 -Master tamil-sfr.tex -Passes 3 -BibTeX -ReceiptName TEX-SFR-RECEIPT`. For the proof-systems reader, run `build/build-tamil.ps1 -Master tamil-proof-systems-sequent.tex -Passes 2 -ReceiptName TEX-PROOF-SYSTEMS-TABLEAUX-RECEIPT`.

## Source and evidence

English revision: 9620cc73f9c8e0ad003c514a5d3748f29611c4c0 of [OpenLogicProject/OpenLogic](https://github.com/OpenLogicProject/OpenLogic/tree/9620cc73f9c8e0ad003c514a5d3748f29611c4c0).
All 722 content-file hashes were checked against the frozen manifest. Stable OLP identifiers and original paths remain in the evidence.

The evidence folder contains the source manifest, actual per-segment canon-use records, terminology decisions and scoped QA. The [canonical decision release](evidence/translation-decisions/START_HERE.md) provides the shared cross-language schema, full and priority human-readable views, one CSV row per exact occurrence, and schema-valid machine JSON. It projects all 157 recorded decisions across 6,399 exact occurrences in all 108 translated units. SyncTeX maps 2,740 occurrences in the 49-unit proof-systems reader to its exact stable PDF pages; the other 3,659 page fields remain explicitly pending and no page is guessed. Tamil Nadu SCERT, Tamil Virtual Academy and university originals informed the work. Direct technical attestation, general scholarly register and provisional choices are distinguished. The accompanying variant assessment recommends one India-standard Tamil-script edition with international mathematical notation on the current evidence.

OpenLogic's natural numbers include zero. The source convention is retained and explained in a separate Tamil edition note, because the consulted school text uses a different convention. New editorial or learner material is kept separate from the faithful source.

The ordinary reader graph and remaining wrappers, all remaining translation, integration of the eight drafted propositional-logic units into a verified reader, ongoing terminology review and final full-edition publication are unfinished. An interim release does not complete the programme.

## Attribution and license

Original text: The Open Logic Project, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Tamil translation and new edition notes: OpenLogic Tamil translation programme, CC BY 4.0.
Changes include translation, Tamil inflection support, layout and PDF extraction support. The original English source and component notices are preserved. See [NOTICE.md](NOTICE.md) and [the original license](upstream/LICENSE.md).
