# writing_auxiliar integration report

1. Main dissertation file: `overleaf/Dissertation_Lobão_extracted/meec_thesis.tex`.

2. Source content location: `writing_auxiliar.docx` in the repository root. The file contains LaTeX text as document text, starting with `\chapter{Introduction}` and continuing through complete dissertation chapters.

3. Insertion location: the extracted content was written unchanged to `overleaf/Dissertation_Lobão_extracted/writing_auxiliar.tex`, and the dissertation body in `meec_thesis.tex` now includes it with `\include{writing_auxiliar}`.

4. Files created or modified:
   - Created: `overleaf/Dissertation_Lobão_extracted/writing_auxiliar.tex`
   - Created: `writing_auxiliar_integration_diff.txt`
   - Created: `writing_auxiliar_integration_checks.json`
   - Created: `writing_auxiliar_integration_report.md`
   - Modified: `overleaf/Dissertation_Lobão_extracted/meec_thesis.tex`

5. Text alteration status: no dissertation text from `writing_auxiliar` was rewritten, improved, summarised, corrected, or restyled. The integrated `.tex` file is byte-identical to the extracted textual content used for the preservation check.

6. Labels, citations, equations, tables and figures:
   - Labels changed: no.
   - Citations changed: no.
   - Equations changed: no.
   - Tables changed: no.
   - Figures changed: no.
   - Technical preamble change: `\usepackage{float}` was added because the imported text uses `[H]` float placement.

7. Compilation status: the complete dissertation was compiled successfully with MiKTeX using `pdflatex`, `biber`, `pdflatex`, `pdflatex`. The resulting PDF is `overleaf/Dissertation_Lobão_extracted/meec_thesis.pdf`.

8. Remaining warnings or issues found by static checks:
   - `\label{sec:objectives}` appears twice in the imported source. It was left unchanged to preserve the original text and labels.
   - Three citation keys used by the imported source were not found in `bibliography.bib`: `toth2014vehicle`, `vidal2013hybrid`, `eidsvik2015value`. `bibliography.bib` was not modified.
   - Figure `\includegraphics` commands in the imported text are commented out, so no figure path was changed.
   - LaTeX reports some overfull/underfull boxes. These are layout warnings and no text was changed to address them.

9. Preservation confirmation: `writing_auxiliar_integration_diff.txt` reports no differences between the extracted text from `writing_auxiliar.docx` and `overleaf/Dissertation_Lobão_extracted/writing_auxiliar.tex`. The SHA256 hash recorded in `writing_auxiliar_integration_checks.json` is identical for both extracted source text and integrated LaTeX text.

The content from writing_auxiliar was integrated into the dissertation LaTeX project without rewriting or modifying the original text.
