# Implement song-level chord analysis

Mode: write; parent session only.
Approved authority: plan/20261005-101500--revision-plan--v0-1-01-song-chords--v02.md.
Goal: separate full-recording chord inference from guitar-tone inference and remove instrument fingering from the result display.
Read first: engine.py, voicing.py, chord_chart.py, chord_edits.py, app.py, report.py, i18n.py and their tests.
Writable scope: those modules, focused tests, an optional bounded pitch-feature module/comparison test, and plan/run records. Dependency changes only after comparison and distribution review under the approved plan.
Discipline: test-driven-development for changed source contracts; incremental-implementation for source, display, then DSP; karpathy-guidelines for narrow interfaces.
Checks: same original PCM regardless of guitar separation, no replacement of tone/reference PCM, source offsets, cancellation, no private error text, retained slash/suspended/extended symbols and alternatives, no result fingering.
Stop: verified source and presentation slice, then continue the approved algorithm comparison and remaining mixer/PDF stages. Material verification findings allow one bounded repair and re-review; do not publish an incomplete release.

Research checkpoint, 2026-10-05 15:34:23 KST (Asia/Seoul):
- User supplied Reddit thread is commentary, not Chord AI implementation documentation. Its author says Bayesian disambiguation was not implemented.
- Linked primary implementation: https://github.com/scblakely/chordid ; GPL-3.0-or-later, known equal-pitch-collection ambiguities. Do not copy this code into the release without a compatible licensing decision.
- Primary description https://chordify.net/pages/technology-algorithm-explained/ describes trained spectrogram models; this is not proof that template/CQT replacement alone improves this app.
- Compare CQT/noise filtering against current FFT pitch evidence. A mean hard floor can lose quiet defining notes; preserve bass and temporal information and report ambiguity. No new real-song accuracy claim.
- Correction metadata repair is complete: 8 focused model/UI tests passed in 7.439s with warnings as errors. Full integration rerun remains.
