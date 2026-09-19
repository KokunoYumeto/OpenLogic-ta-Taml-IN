# Tamil EPUB readers

These EPUB 3.3 readers are reflowable counterparts to the bounded Tamil PDF
readers in `readers/`. They are built from the same translated TeX masters.
Mathematics is emitted as native MathML by TeX4ht; the EPUBs do not wrap PDF
pages or rasterized page images.

The TeX-to-XHTML phase must be run through `build/build-epub-html.ps1`. That
script owns `Global\InterlanguageTeXSlotV1` for the complete `make4ht` process
tree and records a receipt outside the repository. `package_epub.py` then
normalizes the XHTML, creates a source-unit crosswalk, packages a deterministic
EPUB, and writes a packaging receipt. `audit_epub.py` performs independent ZIP,
package, language, navigation, MathML, source-coverage, and local-link checks and
runs EPUBCheck 5.3.0.

Pass the pinned validator as `--epubcheck-jar PATH`, or set the
`EPUBCHECK_JAR` environment variable. The validator binary is not redistributed
in this source tree.

Each reader states its exact OLP unit range and that it is an interim,
machine-translated development reader without a claim of independent human
review. The authoritative frozen English source revision is
`9620cc73f9c8e0ad003c514a5d3748f29611c4c0`.
