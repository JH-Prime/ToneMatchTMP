# Printable sixteen-bar charts

Mode: write; approved v02 fifth phase.
Goal: A4 symbol-first PDF with four bars per row and sixteen bars per chart page, manual edits, source timing and evidence/candidate appendix without fingering.
Inputs: chord_chart.py, chord_edits.py, app export/menu and shutdown lifecycle, PDF skill and official ReportLab font documentation.
Writable scope: chart_pdf.py, tests/test_chart_pdf.py and test_chart_pdf_ui.py, narrow app/i18n integration, resources/fonts and licenses, dependency/build notices, active plan/run records.
Design: bundled OFL Nanum Gothic TTF (no host font dependency), ReportLab vector output, explicit no-overwrite atomic commit, bounded export inputs/cancellation, background app worker. Open PDF only on explicit preview action, never dispatch a print job.
Verification: tests first; extract PDF text/page count with pypdf; render representative Korean/English/dense/final partial pages with bundled Poppler and inspect images. Preserve all dense events through linked detail pages. Full warnings-as-errors and frozen distribution later.
Limits: no automatic beat/bar accuracy claim; no human printing, real-song correctness or signed-build claim.
