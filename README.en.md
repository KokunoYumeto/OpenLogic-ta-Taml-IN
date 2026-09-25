# OpenLogic — தமிழ் (ta-Taml-IN) — English reference

For the reader-facing Tamil edition information, see [தமிழ் முகப்பு](README.md).

India-standard Tamil translation of the [Open Logic Text](https://openlogicproject.org/).
Programme catalogue: [OpenLogic translations](https://github.com/KokunoYumeto/OpenLogic-translations).

The full edition is in progress. **597 of 722 frozen content units are translated, source-aligned and textually and semantically audited**. The accepted source now extends through the complete Choice chapter; 125 units remain.
The first tagged reader remains the complete **Sets chapter: 7 source units, 6 sections, 69 aligned segments**.
The wider 51-unit reader is a verified interim edition: 99 A4 pages covering Sets, Relations, Functions, Size of Sets, number-system construction and Infinite Sets. Patch release v0.2.1 replaces five references to chapters outside this reader with descriptive Tamil fallbacks; the live references return automatically when those destinations are included in a later complete edition. It passed a three-pass guarded XeLaTeX/BibTeX build, font embedding and copy/search checks, plus visual inspection of every rendered page.
Twelve verified component readers cover 248 distinct units. Each component passed a guarded TeX build, embedded-font and copy/search checks, and all-page visual inspection. The existing 384-page cumulative reader concatenates the first seven accepted components (203 units) in frozen-source order, adds section bookmarks, and preserves 626 checked links. The five set-theory readers are supplied separately. The Ordinal Arithmetic, Cardinals, Cardinal Arithmetic and Choice chapters are editable source; their PDF readers have not yet been built.

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
- [வரிசையெண் எண்கணிதம் — editable Ordinal Arithmetic Tamil TeX](translation/content/set-theory/ord-arithmetic/ord-arithmetic.tex): six accepted units; reader PDF pending.
- [கண அளவெண்கள் — editable Cardinals Tamil TeX](translation/content/set-theory/cardinals/cardinals.tex): six accepted units, covering Cantor’s Principle, cardinals as ordinals, the ZFC milestone, finite and infinite cardinals, and Hume’s Principle; reader PDF pending.
- [கண அளவெண் எண்கணிதம் — editable Cardinal Arithmetic Tamil TeX](translation/content/set-theory/card-arithmetic/card-arithmetic.tex): six accepted units, covering cardinal operations, simplification, exponentiation, the continuum hypothesis and fixed points; reader PDF pending.
- [தேர்வு — editable Choice Tamil TeX](translation/content/set-theory/choice/choice.tex): nine accepted units, covering Tarski–Scott, Hartogs, Well-Ordering, Countable Choice, the Banach–Tarski paradox and Vitali's circle construction; reader PDF pending.
- [203-unit cumulative Tamil reader](readers/openlogic-ta-Taml-IN-cumulative-reader-203-units.pdf): 384 A4 pages containing the seven accepted components above, in source order.
- Editable Tamil: `translation/content/`. Each accepted file retains its frozen relative path and stable OLP unit binding in `evidence/`.
- Frozen, unchanged English sources and original components: upstream/.
- Reader master: build/tamil-batch001.tex.
- Combined 51-unit checkpoint master: build/tamil-sfr.tex.
- Propositional syntax-and-semantics source master: build/tamil-pl-syn.tex.
- Proof-systems, sequent-calculus, natural-deduction and tableaux reader master: build/tamil-proof-systems-sequent.tex.

The first 570 units were translated and author reviewed with OpenAI Codex GPT-5.6 Sol, Ultra reasoning. OLP-0574–OLP-0600 and this metadata update were produced with OpenAI Codex GPT-6 Sol, Ultra reasoning. Independent human or native-speaker approval is not claimed.
Every component reader was checked page by page for Tamil shaping, formulas, diagrams, references and clipping. All 597 accepted units pass mathematical, citation, identifier and structural parity checks or a specifically audited source correction. The evidence records 1,551 aligned segments and 759 reverse-paraphrase samples. Seven Ordinal Arithmetic, two Cardinals, seven Cardinal Arithmetic and twelve Choice corrections are documented in [the source-correction ledger](evidence/source-corrections.json). For the cumulative reader, every page content stream and page box is identical to its accepted component, all fonts remain embedded, and representative boundary and interior pages were rendered and visually inspected.

PDF text reuse has measured limitations. Poppler correctly extracts five tested Tamil phrases and representative union, intersection and Cartesian-product formulas. PyMuPDF duplicates some Tamil syllables or loses spacing. Composite negation symbols may still split during extraction in some contexts; blackboard number-set letters may extract as ordinary letters. Use the editable formulas for exact mathematical reuse. This is not a claim of tagged-PDF or universal screen-reader accessibility. A semantic reader remains part of the continuing full-edition work.

## Build

Use a Unicode-capable TeX distribution with XeLaTeX, memoir, the upstream dependencies, fontspec and accsupp. The readers use the Windows system fonts Nirmala UI and Consolas; font files are not redistributed.
Run build/build-tamil.ps1 on Windows. It holds Global\InterlanguageTeXSlotV1 over the captured TeX process tree, every pass, optional BibTeX and log checks. A busy slot returns without starting an engine. The default master produces build/tamil-batch001.pdf. For the combined Sets-through-Infinite-Sets reader, run `build/build-tamil.ps1 -Master tamil-sfr.tex -Passes 3 -BibTeX -ReceiptName TEX-SFR-RECEIPT`. For the proof-systems reader, run `build/build-tamil.ps1 -Master tamil-proof-systems-sequent.tex -Passes 2 -ReceiptName TEX-PROOF-SYSTEMS-TABLEAUX-RECEIPT`. For the iterative-conception chapter, run `build/build-tamil.ps1 -Master tamil-set-theory-story.tex -Passes 3 -BibTeX -ReceiptName TEX-SET-THEORY-STORY-RECEIPT`. For the Zermelo-axioms chapter, run `build/build-tamil.ps1 -Master tamil-set-theory-z.tex -Passes 3 -BibTeX -ReceiptName TEX-SET-THEORY-Z-RECEIPT`. For the ordinals chapter, run `build/build-tamil.ps1 -Master tamil-set-theory-ordinals.tex -Passes 3 -BibTeX -ReceiptName TEX-SET-THEORY-ORDINALS-RECEIPT`. For the stages-and-ranks chapter, run `build/build-tamil.ps1 -Master tamil-set-theory-spine.tex -Passes 3 -BibTeX -ReceiptName TEX-SET-THEORY-SPINE-RECEIPT`. For the Replacement-and-Reflection chapter, run `build/build-tamil.ps1 -Master tamil-set-theory-replacement.tex -Passes 3 -BibTeX -ReceiptName TEX-SET-THEORY-REPLACEMENT-RECEIPT`.

After the seven accepted component PDFs and their QA receipts are present, `python build/package-cumulative-reader.py` losslessly assembles the cumulative reader and `python build/qa-cumulative-reader.py` verifies page streams, geometry, navigation, links, fonts, extraction and the inspected render set. These scripts do not invoke TeX.

## Source and evidence

English revision: 9620cc73f9c8e0ad003c514a5d3748f29611c4c0 of [OpenLogicProject/OpenLogic](https://github.com/OpenLogicProject/OpenLogic/tree/9620cc73f9c8e0ad003c514a5d3748f29611c4c0).
All 722 content-file hashes were checked against the frozen manifest. Stable OLP identifiers and original paths remain in the evidence.

The evidence folder contains the source manifest, actual per-segment canon-use records, terminology decisions and scoped QA. The [canonical decision release](evidence/translation-decisions/START_HERE.md) provides the shared cross-language schema, full and priority human-readable views, one CSV row per exact occurrence, and schema-valid machine JSON. Tamil Nadu SCERT, Tamil Virtual Academy and university originals informed the work. Direct technical attestation, general scholarly register and provisional choices are distinguished. The accompanying variant assessment recommends one India-standard Tamil-script edition with international mathematical notation on the current evidence.

OpenLogic's natural numbers include zero. The source convention is retained and explained in a separate Tamil edition note, because the consulted school text uses a different convention. New editorial or learner material is kept separate from the faithful source.

The ordinary reader graph and remaining wrappers, all remaining translation, integration of the 349 accepted units outside the twelve component readers, reflowable EPUB3 production, ongoing terminology review and final full-edition publication are unfinished. An interim release does not complete the programme.

## Attribution and license

Original text: The Open Logic Project, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Tamil translation and new edition notes: OpenLogic Tamil translation programme, CC BY 4.0.
Changes include translation, Tamil inflection support, layout and PDF extraction support. The original English source and component notices are preserved. See [NOTICE.md](NOTICE.md) and [the original license](upstream/LICENSE.md).
