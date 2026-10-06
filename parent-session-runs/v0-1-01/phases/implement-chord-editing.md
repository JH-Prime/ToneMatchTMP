# Chord correction vertical slice

Role: implementer in parent session. Mode: write under approved v0.1.01 plan.
Goal: edit a detected chord, preserve original evidence, undo or restore, save/reopen corrected results safely.
Read first: chord_chart.py, voicing.py/harmony_reference.py supported vocabulary, result rendering and relocalization, report export, hidden chart UI fixtures.
Writable scope: chord_edits.py, chord_edit_ui.py, related tests, app.py, chord_chart.py, report.py, i18n.py, plan and run records.
Verification-only repair: tests/test_developer_mode.py teardown may cancel its own Tk timers before direct root.destroy. The 336-test checkpoint passed but emitted stale Tcl after-command errors; inspection localized these to existing fixtures that create the app before patching after, then destroy the root without cancelling pending jobs. Keep this separate from product behavior and verify a deterministic pending-timer case.
Contract: corrections are a separate index-keyed map; effective display records never inherit old acoustic confidence or stale fingering. Original event list remains unchanged. Unknown labels and full-mix safeguards survive every rendering/export path. JSON imports are bounded, validated, local-only and never start playback. Audio must be explicitly relinked after reopening.
Validation: pure parser/map immutability/continuation/unknown/invalid data/save-reopen tests, actual hidden UI edits/undo/language/persistence, existing chart and HTML tests, full suite checkpoint.
Selected skills: TDD for observable correction/persistence behavior; frontend-ui-engineering for accessible compact editor; api-and-interface-design for additive correction schema and validated local JSON boundary.
Stop condition: material scope change or repeated root-cause repair failure; otherwise read-only review and move to stem mixer.
