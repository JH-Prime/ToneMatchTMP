# Uncertain chord display and export receipt

Status: Implemented and focused verification complete; parent integration/release pending
Updated: 2026-10-13 21:22 Asia/Seoul
Scope: app.py, report.py, chart_pdf.py, i18n.py, tests/test_uncertainty_display.py
Authority: Approved v0.1.05 plan; parent additionally authorized i18n.py for the shared candidate notice.

## Behavior

- Unknown primary chord remains `?`; candidate symbols are shown only as alternatives in the details, not as accepted chord labels.
- Tk text rendering and HTML no longer suppress unknown-event observed notes, candidates, support counts, or reasons.
- Reasons use the model worker's shared `chord_chart.uncertainty_description` helper. Generic legacy unknowns are not assigned a fabricated reason.
- All-unknown results with candidates receive one localized candidate-availability notice, reused in UI, HTML, and PDF.
- Unknown legacy template pitch classes are not relabeled as observed notes when measured-note metadata is absent.
- PDF details include reasons for analyzed unknown intervals and synthetic gaps; existing candidate/evidence lines, sixteen-bar grid, wrapping, and pagination remain intact.
- Manual corrections remove stale automatic uncertainty/candidates in the effective view; restoring the original correction state brings those details back. No fingering or instrument-only claims were added.

## Red / green evidence

Focused command from the repository root:

```powershell
..\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_uncertainty_display.py -v
```

Initial RED: 7 tests executed, 15 failing subtests, confirming hidden candidates/observed notes and missing weak-match, low-signal, and legacy reason text across the actual rendering paths. After production edits, all 7 passed. A further regression case established that unknown `pitch_classes` fallback could falsely be called observed notes: three renderer subtests failed, and the targeted fallback fix made all 8 tests pass.

The tests execute `ToneMatchApp._render_voicing` with only its widget boundary mocked; HTML uses the production generator with only the final file write captured; PDF uses its production detail/wrapping functions. Tk and Toplevel constructors are guarded to raise.

Latest focused integration command: Python unittest loader for `test_uncertainty_display`, `test_chart_pdf`, `test_chord_edits`, and `test_chord_chart`, with Tk/Toplevel constructors patched to raise. Result: **34 tests passed in 1.159 seconds**. `git diff --check` passed. No existing GUI test module was executed.

## Offscreen PDF verification

Generated two synthetic uncertainty PDFs with the production exporter, one Korean and one English, each containing 40 events, all six reason codes, and candidate-bearing versus candidate-free intervals. Each PDF has five pages (two chart pages and three detail continuation pages). All 40 event identifiers, all six localized reasons, and candidate names survived pypdf extraction; no N.C. symbol was introduced.

Rasterized both files with `pdftoppm -scale-to 1000 -png` and inspected all ten PNG pages with file-image viewing, not screen capture. No overlapping text, clipping, missing glyphs, or footer collision was observed. Existing fixed-height partial chart pages and cross-page detail continuation behavior remain unchanged.

Local temporary verification outputs are under `../work/v105-uncertainty-pdf-zkqys2i9/`; they are synthetic QA artifacts, not release inputs or user deliverables.

## Read-only review and limits

Reviewed own scoped diff for semantics, manual-edit precedence, output escaping, bounded candidate display (three), dependency direction, and scope drift. No blocking issue found in this slice. No dependency added. Imported JSON validation is owned by the model worker and still needs parent integration review.

No native app window, browser, audio playback, hardware action, or GUI automation was used. Tk layout/click behavior is not claimed as visually verified; PDF verification was offscreen only. Full guarded suite, analyzer quality/performance, frozen build, and publication belong to the parent acceptance gate. No commit was made by this worker.
