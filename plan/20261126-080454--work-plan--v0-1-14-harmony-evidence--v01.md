# v0.1.14 · Boundaries and chord evidence

Work plan v01 · Approved by the user on 2026-11-26, Asia/Seoul. Baseline release v0.1.13, source 52439fb, current main 40a3466. Status at 08:04 KST: implementation and paired baseline acquisition in progress.

## Musical objective

Improve chord changes within a bar and the evidence that distinguishes thirds, fifths and sevenths in full-mix recordings. Preserve user-selectable CQT and FFT, slash bass and extended spellings. Keep an uncertain symbol, localized reason and supported alternatives when the sound does not distinguish chord identities. Preserve existing editing, reporting, playback synchronization, PDF and mixer contracts. Loading earlier saved results must remain possible.

## Implementation and evaluation

1. Reproduce controlled changes and single-note partials. Inspect boundary placement, evidence windows and classification. Apply bounded processing within the existing engine and keep silence and ambiguous partials conservative. Add targeted regressions for the musical cases and the presentation path.
2. Freeze the comparison baseline at the published tag. Run both methods on identical full recordings and reference spans, comparing exact name with bass, root, false confirmations, abstention and boundary timing. Broaden the recorded sample across styles and performers. Document the unit of a sample, reference source, exclusions, denominators, and any regressions.
3. Inventory the accessible Drive scores, including pagination and duplicate arrangements. Use short verified fragments across as many different works as possible in synthetic full-mix controls. Keep score-derived synthesis, controlled signals, and actual performance metrics separate. Keep the private scores, audio, identifiers and transcriptions outside public source and packages.
4. Run guarded tests without native windows or playback. Update versions, documentation, QA and function reference. Generate the Development ZIP and verify frozen diagnostics, archive integrity and previous-version cache handling. Publish distinct prerelease assets and validate the actual downloads. Preserve every older tag/file and the existing signing policy.

## Acceptance and rollback

Compare the production entry point before and after on identical PCM. Note where measurements do not establish commercial-recording accuracy. Retain changes only with a reproducible musical or diagnostic benefit, review material regressions on independent controls. No UI/audio device acceptance is inferred. A failed prepublication build can be repaired locally. After publication a correction requires another version.

## Scoreboard

2026-11-26 08:04 KST · provisional 30/100. Scope approved and original tag/releases confirmed. Measurements, implementation, package and publication remain outstanding.

2026-11-28 KST · 80/100. Completed the production-path comparisons and 580 guarded tests. The matched sample includes two full-mix recordings, all 180 GuitarSet comping performances and 154 score-derived renders from 77 usable files. Both improvements and regressions are recorded in the QA report. The developer archive and public download checks follow the accepted source commit.
