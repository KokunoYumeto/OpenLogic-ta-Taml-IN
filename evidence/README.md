# Evidence and expert review

This folder binds the Tamil draft to the frozen OpenLogic source, the Tamil originals actually consulted, per-segment evidence, structural QA, and semantic review.

translation-decisions.jsonl is the maintained asynchronous expert-review ledger. It records every current terminology decision and known difficult translation or source-correction choice, with exact representative source/target locations, checked authorities, rationale, alternatives, uncertainty, and a concrete review question. A provisional entry is open to correction and does not claim expert approval. For decisions made before the ledger requirement, the original choice and rationale come from the existing contemporaneous term record; locations, alternatives and review questions are explicitly identified as a retrospective backfill.

The ledger’s locations are decision anchors rather than an exhaustive occurrence concordance. segment-canon-use.jsonl is the complete current per-segment provenance record. Scope and QA files describe only the published or drafted tranche named in each file.

The current 51-unit checkpoint is bound by:

- `source-manifest.jsonl`: all 722 frozen English units, paths, byte counts and SHA-256 hashes;
- `canon-sources.jsonl` and `canon-passages.jsonl`: consulted Tamil authorities, exact locators, source hashes and bounded excerpts/context;
- `term-decisions.jsonl`: term-level decisions and the canon passages supporting them;
- `segment-canon-use.jsonl`: 456 one-to-one source/translation segment records, each naming canon passages actually consulted;
- `source-corrections.json`: the canonical source-error/correction ledger, including shared `OLSIZ-001` through `OLSIZ-010` and the three conditional reader-reference fallbacks;
- `translation-decisions.jsonl`: terminology, semantic and source-correction decisions with review anchors;
- `qa-batches/`: all 36 current deterministic textual-QA receipts;
- `checkpoint-current.json`, `qa-current.json`, and `semantic-review-current.json`: the bounded 51/722 status and semantic samples;
- `tex-sfr-patch-receipt.json` and `sfr-render-qa.json`: the exact v0.2.1 guarded three-pass/BibTeX build receipt, zero-undefined-reference and zero-literal-`??` checks, embedded-font checks, and visual inspection record for all 99 pages of the 51-unit reader. `tex-sfr-receipt.json` retains the v0.2.0 build evidence.
- `manager-canon-visual-spotcheck.json`: an independent three-source visual check that the cited printed terminology is actually present on the hashed canon renders.
- `shared-source-audit-olsiz-011-retracted.json` and `shared-source-audit-olsiz-011-retraction.json`: the explicit tombstone and correction for a manager false positive. Exact byte inspection showed a valid three-backslash row-break-plus-`hline` token; no source correction was applied. They are retained so downstream editions cannot silently inherit the withdrawn claim.

Canon originals are not redistributed here where their reuse license is unestablished. Their public URLs, exact local-byte hashes, locators, rendered-page hashes and evidence limitations remain in the ledgers so the consultation can be independently reconstructed. The earlier tagged reader covers seven Sets units; the newer 51-unit reader is explicitly an interim edition and is not described as the complete 722-unit edition.
