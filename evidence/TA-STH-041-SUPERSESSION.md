# TA-STH-041: source-error claim retracted

The earlier TA-STH-041 evidence described the closing formula in `content/set-theory/choice/hartogs.tex` as ill-typed. That classification was a false positive. In the frozen `open-logic-config.sty` at line 956, `\cardeq{X}{Y}` expands to `X \approx Y`. Thus the nested source prints the ordinary chain

`A \disjointsum B \approx A \times B \approx M`.

It does **not** pass a proposition as a set argument. The Tamil edition states `A\disjointsum B\approx M` and `A\times B\approx M` separately. By symmetry and transitivity of equinumerosity, these two statements express the same relations as the source chain. The wording remains as an explicit editorial presentation, not a mathematical repair.

The frozen and current upstream macro files are byte-identical: 50,435 bytes, SHA256 `76af3674c68139572b71de9908d690700cd7e324d221d649930ecda020935724`. The frozen revision is `9620cc73f9c8e0ad003c514a5d3748f29611c4c0`; the later checked revision is `1e960beff9ed7835bf3e3f1335e21af3439cd107`. [Frozen macro definition](../upstream/open-logic-config.sty), [source passage](../upstream/content/set-theory/choice/hartogs.tex), and [Tamil passage](../translation/content/set-theory/choice/hartogs.tex) are available in the repository.

The published v1.1.1 PDF, EPUB, TeX and source ZIP remain available with their original verified hashes. The [current corrected decision register](translation-decisions/DECISIONS.json.gz) supersedes the TA-STH-041 entry in that source ZIP. Historical QA snapshots and release assets retain the earlier wording as provenance; this note supersedes that one classification. The genuine nearby carrier and transported-order corrections TA-STH-039 and TA-STH-040 are unaffected. No reader rebuild is needed because the Tamil mathematical content is unchanged.
