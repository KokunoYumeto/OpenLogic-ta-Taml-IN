+# Tamil script, notation, register, and regional-variant assessment

Status: active edition policy for `openlogic-ta-Taml-IN`, assessed 2026-09-05.

## Recommendation

Publish one semantic Tamil edition in the Tamil script for readers in India. Keep OpenLogic's international mathematical notation and the modern Tamil Nadu curricular prose register. Do not create parallel Latin-transliteration, Tamil-numeral, classical-register, or Sri Lankan-Tamil editions at this stage.

The TeX token layer remains configurable so a future evidence-backed regional edition can reuse formulas and document structure. A separate edition would be preferable if a Sri Lankan audience later requires sustained lexical and pedagogical differences; a simple script switch would not express those differences accurately.

## Intended audience

The present reader is for Tamil-reading secondary, university, and independent logic learners in India. It uses contemporary mathematical exposition rather than literary or purely philosophical prose.

## Evidence considered

- `TA-SCERT-6-2018-RECOVERED`, `TA-SCERT-11-MATH`, and `TA-SCERT-12-MATH-V2` provide current Tamil Nadu school mathematical prose, international digits, symbolic notation, and a logic chapter.
- `TA-TVA-MATH-QA` and `TA-TVA-MODERN-GRAMMAR-QUANTIFIER` provide India-based higher-education terminology and native Tamil prose.
- `TA-ALAGAPPA-BSC-2021` provides Tamil Nadu university-level mathematical terminology in actual questions.
- `TA-NOOLAHAM-INTERMEDIATE-LOGIC-1967` provides valuable historical Ceylon Tamil logic vocabulary. Its age, region, and Aristotelian scope make it contextual evidence rather than grounds for silently changing the India-standard edition or manufacturing a second regional reader.
- Every cited source, exact passage locator, hash, limitation, and consultation role is recorded in `evidence/canon-sources.jsonl` and `evidence/canon-passages.jsonl`.

## Script and orthography

Use Unicode Tamil script (`Taml`) normalized to NFC. Preserve Latin proper names, symbolic metavariables, and mathematical control notation where the discipline requires them. No readership evidence supports a full Latin transliteration companion, and such a projection would lose distinctions that Tamil readers already receive directly in the standard script.

Use contemporary India-standard spelling. Historical spellings or Sri Lankan forms may be cited when they supply evidence, but they are not imposed on the main prose without current India evidence.

## Numerals and notation

Retain international digits `0–9`, OpenLogic formula notation, and the source's logical symbols. The consulted Tamil Nadu curricular materials use this mixed Tamil-prose/international-notation practice. A Tamil-digit edition would add a visual difference without evidence of a distinct learner need and would complicate formulas, search, copying, accessibility, and cross-language comparison.

## Register and region

Use a modern didactic mathematical register. Formal definitions and displayed inference rules govern newly composed proof-theory terms whenever an exact modern Tamil headword is not attested.

The current evidence does not justify separate colloquial, literary, or Sri Lankan-Tamil products. If expert review or readership demand later establishes a systematic regional vocabulary, create a distinct semantic edition with its own decision ledger and QA. Keep formulas and stable OpenLogic identifiers compatible across editions.

## Build and compatibility implications

- One `ta-Taml-IN` build profile is sufficient now.
- UTF-8 Tamil, NFC checks, Tamil-capable font shaping, ActualText/copy-search QA, and unchanged mathematical identifiers remain required.
- Tokenized terminology makes later evidence-backed replacements reversible without reworking formulas.
- Reader-page mappings belong to exact PDF hashes; a rebuild must regenerate them through SyncTeX.
- The decision register must expose every provisional or sensitive choice and must never guess a pending page.

## Expert question

Please double-check whether any current India-based logic curriculum or substantial learner community requires a second script, Tamil-digit notation, or a systematically different regional/register edition. If so, identify the audience and an authoritative corpus broad enough to support a separate profile.

