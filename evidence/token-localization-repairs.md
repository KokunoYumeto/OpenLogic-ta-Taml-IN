# Literal token and article localization, 2026-09-28

The final source-wide renderer audit examined all 722 translated content files against the actual Tamil token configuration and the frozen upstream token definitions. The source-aligned TeX files correctly retained the token keys, but five natural-language keys still inherited English output:

| Key | Tamil output | Existing decision | Source uses |
|---|---|---|---|
| depth | ஆழம் | TA-T296; same depth noun as TA-T248 | 1 |
| introduction | அறிமுகம் | TA-T092 | 24 |
| elimination | நீக்கல் | TA-T092 | 29 |
| parameter | அளவுரு | TA-T205; lambda binder sense remains fixed by OLP-0357 | 2 |
| relational model | தொடர்புசார் மாதிரி | TA-T169 | 6 |

`translation/tamil-config.sty` now supplies singular/plural and explicit initial forms for all five, together with Tamil article forms. These are existing edition renderings, not newly claimed canon attestations. Their formal definitions, source token keys and mathematical expressions remain unchanged.

The same audit found six previously translated keys whose article forms still inherited English `a`/`an`: main operator, undischarged, axiomatizable, derivability, decidable and lambda definable. Explicit ஒரு/ஓர் forms now cover their twelve actual article-bearing uses. The generated receipt contains exact source paths and one-based lines for those uses. The Tamil `@printtoken` implementation chooses the lowercase article form even when the source has a capital-initial flag; both article switches are nevertheless supplied consistently.

Four unchanged keys are intentional formal exceptions. colorC, colorD and colorE supply the frozen engine color names red, blue and green to graphics commands; translating those strings would break plotting rather than translate visible prose. The source-defined `hp` abbreviation is preserved in two parenthetical technical labels; each adjacent Tamil passage already spells out height preservation. It is a retained technical initialism, not an untranslated ordinary-prose sentence.

`TOKEN-LOCALIZATION-QA.json` verifies all 62 natural-language keys among the 66 used literal keys have Tamil registrations, all 37 article-bearing keys have explicit Tamil or intentionally empty article forms, and the configuration is NFC. The five new text overrides cover 62 uses; the six additional article overrides cover twelve uses. Configuration identity: 19,603 bytes, SHA-256 `b43e39230e26f15e20467aaf6b819c224b160ae80e1a3286209e33dc8fc5c220`.

This is static renderer-configuration QA. It does not claim a compiled PDF, correct shaping/layout in new bytes, complete dynamic-alias coverage or an independent native review. The protected TeX attempt immediately after the source milestone returned slot-unavailable; these configuration changes belong to the accumulated pending build scope. Corpus/terminology/reader-package work continues without polling that slot.
