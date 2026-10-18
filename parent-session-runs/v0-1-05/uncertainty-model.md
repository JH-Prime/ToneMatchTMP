# v0.1.05 uncertainty model and persistence receipt

Updated: 2026-10-13 21:22:06 Asia/Seoul
Status: Assigned model slice implemented and focused verification passed; parent integration and release pending.
Approved plan: `plan/20261011-232025--work-plan--v0-1-05-uncertain-chords--v01.md`

## Scope and design

- Owned files: `chord_chart.py`, `chord_edits.py`, `tests/test_uncertainty_model.py`, and this receipt only. No commit created.
- Chart normalization now deep-copies existing evidence and alternatives into every event continuation without changing the protected unknown label `?`.
- Synthetic gaps have `event_index=None`, no alternatives, and `evidence.uncertainty_reason=unobserved_gap`; they remain non-editable observations, not detected no-chord labels.
- `uncertainty_description(event, language='ko')` supplies shared Korean/English wording for six finite reasons: `low_signal`, `insufficient_tonal_evidence`, `weak_match`, `temporal_instability`, `unobserved_gap`, `output_limit`.
- Known events and all manually edited events return an empty automatic uncertainty description. Legacy unknown events receive a generic unresolved description without invented causes.
- Saved JSON validates the optional reason as a string in the finite enum. No saved schema bump or extra dependency is required; old results remain loadable.
- The parent selected a minimal optional `evidence.reanalysis_recovered` Boolean contract. Imports reject other types and reject `true` for an unknown chord or `?` symbol. Absent metadata and explicit `false` remain compatible. No event-level window-width metadata is added.
- Existing manual correction behavior already removes automatic evidence/alternatives from the effective event while preserving raw analysis and undo. Regression tests cover both named corrections and explicit user `?` corrections.
- Evidence window counts have a named finite maximum of 25,000 instead of 10,000, accommodating 20-minute CQT analysis at 50ms observation spacing and integer-sample rounding. This does not enlarge the separate event collection, file size, or edit limits.

## Test-first evidence

Before production changes, `python -m unittest discover -s tests -p test_uncertainty_model.py -v` ran 8 tests and failed: 9 failed assertions/subcases and 9 missing-helper errors/subcases. Failures reproduced missing chart evidence, missing synthetic gap reason, and acceptance of invalid new reason values. Legacy reopening and unknown-label normalization already passed.

After implementation, the same focused suite passed all 8 tests in 0.058 seconds.

The combined regression run passed 30 tests in 0.892 seconds with warnings treated as errors and `tkinter.Tk`/`tkinter.Toplevel` patched to raise on attempted GUI creation. Modules: `test_uncertainty_model`, `test_chord_chart`, `test_chord_edits`. These cover chart timing/page continuity, raw-data immutability, independent continuation copies, old/new JSON reopen, malformed imports, chord syntax, correction and undo, and reason localization. No GUI creation, playback, audio device access, or browser operation occurred.

The later agreed recovery-status boundary received an additional test-first loop. A fixture spelling typo (`minor7` instead of the existing `min7`) was corrected before implementation; the corrected red test demonstrated seven invalid recovery-status subcases accepted by old code. After the narrow validation change, all 31 combined regression tests passed in 0.915 seconds, with the same warnings-as-errors and hard GUI guards. There are now 9 tests in the new model test module.

On October 13, the parent requested the scoped evidence-count bound repair because newly preserved unknown evidence can cover a full 20-minute track. A new test first failed for counts 24,001 and 25,000 with `Invalid evidence counts`. After changing only the evidence-window limit, all 32 combined regression tests passed in 0.978 seconds with warnings-as-errors and the same Tk/Toplevel guards. The new module now has 10 tests. Negative counts, Booleans, floats, strings, and 25,001 are still rejected for both supported and analyzed window counts. Recovery-status validation remains present and its cases pass.

`git diff --check` passed after this slice. Read-only self-review found no additional actionable issue in the assigned production diff. The parent owns the full headless suite, analyzer promotion policy, independent review, packaging, and publication.

## Boundaries and remaining integration risks

- Reason and event recovery-status metadata are validated. Analysis-level reanalysis counters use the existing general diagnostics boundary; no extra event recovery fields were introduced.
- This model slice cannot establish analysis accuracy or renderer layout quality. It preserves uncertainty rather than promoting candidates. UI/export integration is a separate owned slice.
- Existing import limits (8 MiB, finite tree values, bounded event collections, at most three alternatives) remain unchanged. This is not a general import-hardening refactor.
- No screen-based visual verification was performed because the user prohibited screen operations.
