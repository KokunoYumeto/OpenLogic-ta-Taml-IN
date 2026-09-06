# Evidence and expert review

This folder binds the Tamil draft to the frozen OpenLogic source, the Tamil originals actually consulted, per-segment evidence, structural QA, and semantic review.

translation-decisions.jsonl is the maintained asynchronous expert-review ledger. It records every current terminology decision and known difficult translation or source-correction choice, with exact representative source/target locations, checked authorities, rationale, alternatives, uncertainty, and a concrete review question. A provisional entry is open to correction and does not claim expert approval. For decisions made before the ledger requirement, the original choice and rationale come from the existing contemporaneous term record; locations, alternatives and review questions are explicitly identified as a retrospective backfill.

The canonical `translation-decisions/` release expands those anchors into an exhaustive current occurrence concordance: 157 decisions and 6,399 exact source-target occurrences across 108 translated units. It includes full and priority review views, CSV, schema-valid JSON and the frozen cross-language schema. SyncTeX maps 2,740 occurrences in the 49-unit proof-systems reader to exact stable-PDF pages; all 3,659 occurrences outside that reader retain an explicit pending page field. `segment-canon-use.jsonl` is the complete current per-segment provenance record. Scope and QA files describe only the published or drafted tranche named in each file.

The current 108-unit checkpoint is bound by:

- `source-manifest.jsonl`: all 722 frozen English units, paths, byte counts and SHA-256 hashes;
- `canon-sources.jsonl` and `canon-passages.jsonl`: consulted Tamil authorities, exact locators, source hashes and bounded excerpts/context;
- `term-decisions.jsonl`: term-level decisions and the canon passages supporting them;
- `segment-canon-use.jsonl`: 792 one-to-one source/translation segment records, each naming canon passages actually consulted;
- `source-corrections.json`: the canonical source-error/correction ledger, including shared source audits and conditional reader-reference fallbacks;
- `translation-decisions.jsonl`: terminology, semantic and source-correction decisions with review anchors;
- `translation-decisions/`: the canonical expert-review package, including 157 decisions, 6,399 exact occurrences and 2,740 stable reader-page mappings;
- `qa-batches/`: all 52 current deterministic textual-QA receipts;
- `checkpoint-current.json`, `qa-current.json`, and `semantic-review-current.json`: the bounded 108/722 status and 194 semantic-review samples;
- `tex-sfr-patch-receipt.json` and `sfr-render-qa.json`: the exact v0.2.1 guarded three-pass/BibTeX build receipt, zero-undefined-reference and zero-literal-`??` checks, embedded-font checks, and visual inspection record for all 99 pages of the 51-unit reader. `tex-sfr-receipt.json` retains the v0.2.0 build evidence.
- `tex-proof-systems-tableaux-receipt.json` and `proof-systems-tableaux-render-qa.json`: the exact guarded two-pass build receipt, text-extraction and embedded-font checks, and visual inspection record for all 89 pages of the 49-unit proof-systems reader.
- `manager-canon-visual-spotcheck.json`: an independent three-source visual check that the cited printed terminology is actually present on the hashed canon renders.
- `shared-source-audit-olsiz-011-retracted.json` and `shared-source-audit-olsiz-011-retraction.json`: the explicit tombstone and correction for a manager false positive. Exact byte inspection showed a valid three-backslash row-break-plus-`hline` token; no source correction was applied. They are retained so downstream editions cannot silently inherit the withdrawn claim.

Canon originals are not redistributed here where their reuse license is unestablished. Their public URLs, exact local-byte hashes, locators, rendered-page hashes and evidence limitations remain in the ledgers so the consultation can be independently reconstructed. The tagged readers are explicitly interim editions and are not described as the complete 722-unit edition. The two wider verified readers cover 100 distinct units; eight additional drafted units remain outside an all-page visually verified reader.
