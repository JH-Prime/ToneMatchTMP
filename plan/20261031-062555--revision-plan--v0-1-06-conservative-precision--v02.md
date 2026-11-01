# v0.1.06: Conservative precision release

Plan Type: Revision plan
Workstream: ToneMatchTMP v0.1.06 chord precision
Version: 02
Status: Source and frozen build accepted; preparing clean-commit archive verification
Created: 2026-10-31 06:25:55 Asia/Seoul
Last Updated: 2026-11-01 16:52:40 Asia/Seoul
Supersedes: plan/20261022-214321--work-plan--v0-1-06-chord-precision--v01.md
Current Completion State: Source, actual-file, C++ and frozen workflow verification passed
Completed So Far: Approved implementation, 387 final tests, all comparisons, actual checks, docs and hidden build
Remaining Work: Clean source commit, fresh archive verification, tag/push/publication and public readback
Current Blockers: None identified; release stages still pending
Next Step: Freeze reviewed source, create immutable archive and verify a fresh extraction before publication

## Approval and revised objective

The user answered “넵” to the explicit proposal to restore the problematic FFT change to the prior behavior, retain CQT and extended-chord improvements, fix the quiet-region and verification-data errors, re-run all checks and release. This approval resolves the previous plan's re-planning gate. It authorizes a narrower release, not another open-ended attempt to infer independent notes from harmonic residual energy. The experimental FFT low-bass detection gain is explicitly deferred. Do not claim that the deferred gain exists or remove its failure evidence from development records.

The objective is a reliable v0.1.06 developer prerelease with fewer supported-chord omissions where the retained evidence permits them, and no demonstrated new false-positive regression relative to v0.1.05. The user's priority is precision in existing functions rather than new UI or modes. Preserve CQT and FFT selection, whole-mixture chord interpretation, unknown intervals, explanations and alternatives, corrections, persistence, chart alignment and exports. The product must still decline to name a chord when local evidence is inadequate. Detecting more named intervals is not itself success.

The immutable comparison baseline remains v0.1.05 at commit 83e88c10f62f6b174b2f95cf0e68b751a14f4db0. The repository HEAD before this work remains 7017e91. Preserve the published tag, assets, original source results and old portable folder for rollback. The current uncommitted changes are the retained task work; do not reset or discard the whole worktree. Restore only the narrowly identified peak-suppression function and leave independently approved classifier changes in place.

## Why the direction changed

The initial residual-envelope experiment retained independently played notes near a low bass harmonic, but it also promoted resonant harmonics to chords. A guard for entirely harmonic-explainable spectra passed several negative controls yet failed when a weak unrelated tone was added. A parent-confirmed example is a formant-rich C2 signal plus a small Bb3 sinusoid: v0.1.05 remains unknown while the new path names C5 for the full interval. The added Bb is not evidence that the strong third harmonic is an independently played G. This is the same inference failure that survived the first bounded repair.

Do not respond by adding more harmonic-neighbor offsets, relaxing confidence gates or tuning one amplitude threshold to that example. Return the FFT independent-peak extraction to the conservative baseline behavior. This may again leave some valid low-bass voicings unresolved; that is an acknowledged limitation, not a hidden regression against the published release. Keep the low-bass synthetic fixtures in comparisons so the limitation stays visible, and add the weak-anchor counterexamples to regressions so the rejected experiment cannot silently return.

The CQT changes and omission-aware scoring are separable from that FFT function. The CQT front end calls the shared classifier with its own spectral evidence. It can retain resolved peaks, reject adjacent filter shoulders and weak cross-octave accumulation, and preserve the median primary interpretation before considering sequential-note evidence. The shared scorer can accept selected extended chords with a missing perfect fifth without altering the conservative FFT spectrum. Retain those bounded changes subject to full verification.

## Existing defects to complete

Repair the CQT quiet-region contract before accepting any operational result. A low-signal unknown intentionally lacks observed-pitch information. The new minority-evidence gate currently accesses that optional field unconditionally, raising a KeyError in silent gaps between audible regions. Preserve the low-signal result directly; do not use CQT filter bleed from neighboring audio to fill silence with a chord. Keep the existing zero and very-quiet PCM regressions with a nonempty transform, and verify a real audible-chord, silent-gap, audible-chord sequence as well.

Repair synthetic truth construction using integer frame boundaries. Adding floating-point durations for several generated blocks caused an annotation endpoint to exceed the exact PCM duration by a tiny rounding error. Do not weaken the strict annotation validator or increase its time tolerance to hide this construction bug. Derive every start and end from accumulated sample counts, preserving contiguous and exactly bounded truth. Keep the failing endpoint regression and ensure both the trace corpus and expanded precision corpus use consistent construction.

Retain all original correctness tests unless the revised objective explicitly changes their claim. In particular, tests demanding the abandoned new FFT low-bass gain must be renamed or rewritten to enforce conservative baseline behavior, not merely deleted or skipped. The frozen diagnostic and packaging gate must similarly stop requiring that abandoned gain. Replace that requirement with an actual harmonic-rejection check in the frozen runtime, including the weak-anchor counterexample. Keep omitted-fifth evidence roundtrip and all existing music-workflow gates.

## Implementation discipline and ownership

Apply the global AGENTS contract, the parent-session workflow, the local simplicity overlay, test-driven development and systematic debugging. Tests should reproduce the intended failure before the corresponding implementation changes. Existing recorded RED evidence can establish a known failure, but run the focused regressions against the final repaired source as well. Work through small coherent edits and preserve unrelated user changes. Use apply_patch for source and documentation edits, and normal generation commands for generated reports and build artifacts.

Parallel work may use the current runtime's actual internal agents with disjoint file ownership. Do not launch external background workers or assume isolated worktrees. One worker may restore the FFT function and its directly affected tests. Another may fix the CQT quiet-region branch and related tests. The parent owns the integer-frame fixture repair, shared run records, frozen diagnostic integration and release acceptance. A separate reviewer can inspect changes after implementation is held stable. No worker should rewrite the shared plan, change versions, commit, publish or touch another owner's files without coordination.

Keep the writable surface limited to chord analyzers, directly affected tests and comparison tools, hidden runtime diagnostics, and normal version/build/release documentation. Do not redesign equipment catalogs, tone recipes, source separation, playback, the chart UI or fonts. Do not add a dependency, external model, model download, remote processing path or new C++ ABI. Retain the current Python/NumPy/SciPy/librosa stack and existing native DSP. The removed inference should not be replaced by an unrelated solver in this release.

Maintain this revision and parent-session-runs/v0-1-06/session-summary.md as the durable current state. Record meaningful RED/GREEN, comparison, review, build and publication transitions with Asia/Seoul timestamps. Preserve attempt reports rather than overwriting failures with successful results. Update the conservative provisional score when evidence materially changes; this is a workflow rating, never an acoustic accuracy percentage or invented user score.

## Verification strategy

First run the targeted classifier, vectorized-score, CQT precision, trace-metric and frozen-diagnostic tests. Verify the exact restored function against the baseline source and inspect the remaining diff to ensure omission-aware scoring and observed-only evidence survived. Verify that a missing perfect fifth does not become an observed note through serialization. Root, third and named extension evidence remain mandatory; missing altered fifths, missing roots and bare thirds do not imply a completed chord.

Then run the complete guarded headless suite with warnings treated as errors. The test runner must reject creation of Tk or Toplevel windows. Disclose the GUI-containing tests as deferred; do not remove their names from the receipt. A passing source test suite is not native click or visual QA. Do not run unrestricted test discovery or any command that could show or focus a window. No audio playback, input-device testing, browser opening or physical printing is authorized.

Compare the same generated PCM against immutable v0.1.05 and the current source with both front ends. Retain the expanded precision set, uncertainty corpus and eleven-sequence trace corpus. Add the weak unrelated-note harmonic controls without suppressing existing failures. Check exact correct, incorrect and unknown durations independently, plus root, triad and bass agreement where meaningful. Ambiguous ground truth may accept explicitly declared equivalent labels without double counting duration. Keep per-case gates for wrong promotions, increased error, reduced correct duration, lost transitions and increased boundary error; aggregate gains must not conceal an individual regression.

Record source hashes before and after comparisons and reject results if source changed during the run. Resolve the baseline to the expected immutable commit and ensure any dependency shared with baseline modules matches. Warm both analyzers equivalently before reporting timing. Treat elapsed time as a measurement in this environment, not a universal speed guarantee. Existing boundary error values and observation hops are not guarantees of real-world transcription accuracy.

Use the authorized local Room 335 MP3 only for operational validation after source acceptance. Analyze the full file and the existing excerpt with CQT and FFT, without playback or upload. Verify monotonic progress, cancellation, unchanged input, whole-mix identity, bounded finite events, corrections, reopening and HTML/PDF exports. The song has no verified chord annotation. Report coverage and runtime only as operational measures, never as a measured accuracy improvement. Do not commit, package or redistribute private audio, extracted audio or private absolute paths.

## Review and bounded repairs

After the full verification set passes, perform an independent read-only review of the final diff and acceptance evidence. Review false-positive risk, optional-field handling, schema compatibility, preservation of abstention, cancellation and resource bounds, source provenance, package privacy and rollback safety. Review tests before implementation and reject missing evidence, not just failing assertions. A successful small synthetic corpus does not prove universal accuracy, so keep realistic limitations in the documentation.

This user-approved revision permits one bounded repair pass for defects uncovered inside this narrower surface. Record each concrete repair scope before editing and rerun the relevant proof plus final integration checks. If the same root cause survives that completed repair, return to planning instead of adding unbounded heuristics or weakening gates. If completion requires a new dependency, model, UI, trust boundary or materially different behavior, ask for direction before making the expansion. Ordinary versioning, tests, build and publication already fit this approval and do not require another confirmation.

## Build and release acceptance

Only after source and comparison acceptance, bump current metadata consistently to 0.1.06 and preserve historical dates and changelog entries. Update English and Korean documentation, developer handoff, research notes, build history and a new versioned QA report. Clearly distinguish the retained improvements, the deferred FFT low-bass experiment, controlled-test evidence and unmeasured real-song accuracy. Do not advertise complete transcription or claim native visual testing that did not happen.

Build the unsigned Windows x64 portable developer package using the established hidden procedure. The no-screen build must use the already-passed guarded suite and skip the build script's unrestricted GUI tests. Require the native ABI 2 parity check, CQT/FFT runtime workflow, harmonic rejection, omitted-fifth persistence, export/font resources and dependency loading. Check build warnings individually and document any retained optional warnings. Do not silently treat required runtime warnings or missing modules as harmless.

Bind the archive to a clean reviewed source commit. Include the matching source, documentation, licenses, QA and comparison receipts; exclude media, model weights, development caches and private paths. Preserve all previous version artifacts. Use exclusive creation for the new archive and verification receipt so retries do not overwrite a candidate unnoticed. Extract the candidate to a new validated task directory, verify every manifest entry and source hash, and run the hidden frozen self-test from that fresh extraction.

Publish a new v0.1.06 developer prerelease on the existing GitHub repository only after the archive gate passes. The tag must point to the verified source commit, and HEAD must be clean and match it at publication. Use the established credential handling without exposing secrets. Upload the developer ZIP, checksums and archive-verification receipt, confirm remote sizes and digests, publish, then read the public release back. Do not replace an already published tag or asset. If permission or network issues prevent publication, report the exact completed stage rather than claiming a release.

Completion means the approved narrower implementation is tested, reviewed, packaged and published with matching assets, or a precise external blocker is reported. The final response should be concise, link the release when available, mention the most useful verified changes and the deliberate FFT deferral, and disclose any important untested surface. Keep the previous portable version and original results available for rollback.

## Scoreboard

Current Score: 47/100
Score Source: provisional
Last Updated: 2026-11-01 16:52:40 Asia/Seoul
Score Rationale: Controlled comparisons, actual workflows and frozen build pass; archive and public delivery remain pending.
What Improved: The risky residual inference is no longer a required release objective; known failures have explicit bounded repairs.
What Remains Unsatisfactory: Real-song accuracy remains unmeasured and the new archive is not yet publicly verified.
Next Score Action: Demonstrate clean regressions and comparisons, then finish a verified portable prerelease.

### Score history

- 2026-10-22 21:43:21 Asia/Seoul — 40 provisional: Initial approved precision workstream.
- 2026-10-31 06:22:58 Asia/Seoul — 35 provisional: Persistent false positives forced replanning.
- 2026-10-31 06:25:55 Asia/Seoul — 35 provisional: User approved this conservative revision; acceptance remains pending.
- 2026-11-01 10:50:15 Asia/Seoul — 43 provisional: Source and comparison acceptance demonstrated.
- 2026-11-01 16:52:40 Asia/Seoul — 47 provisional: Actual-file and frozen runtime verification passed; publication pending.

## Progress log

- 2026-10-31 06:25:55 Asia/Seoul — User approved the proposed narrower scope with “넵”. Revision written before resumed implementation. Prior plan superseded; screen, privacy, baseline and publication constraints retained.
- 2026-10-31 06:29:13 Asia/Seoul — Integer-frame truth construction fixed after recorded RED; six trace-metric tests and seventeen precision-metric tests pass. Added three weak-anchor negative fixtures, expanding comparison to 31 inputs/62 method rows. Frozen diagnostic test now requires harmonic rejection instead of the deliberately deferred low-bass gain; RED execution is in progress. File-scoped workers handle exact baseline FFT restoration and CQT low-signal guard.
- 2026-11-01 10:47:24 Asia/Seoul — Resumed saved work; no previous worker was live. Confirmed quiet-region guard was saved but FFT restoration was not. Reproduced eight failing precision subcases, restored only the FFT peak function and proved exact source identity with v0.1.05; all nine precision tests now pass. Pre-restoration attempt3 receipts/logs are diagnostic only and will not be packaged. Independent read-only review is underway; final source comparisons follow on the stable repaired code.
- 2026-11-01 10:50:00 Asia/Seoul — Source accepted: 387 guarded tests pass, 92 GUI cases disclosed as deferred. Precision 62, uncertainty 32 and trace 11 cases pass their strict individual gates. Precision newly correct 14.4s, newly incorrect 0s; trace agreement unchanged. Independent reviewer confirmed exact FFT restoration, 98,400 scalar/vector scores, CQT quiet handling and observed-only omission evidence. Metadata advanced to v0.1.06; provisional score 43. Actual-file/build/archive/publication remain pending.
- 2026-11-01 10:51:08 Asia/Seoul — Final versioned source receipt passes 387 tests in 69.655s with 92 GUI cases deferred. Authorized full-file and excerpt checks pass for CQT/FFT including cancellation, progress and exports. CQT coverage fell to 43.22%; FFT is 43.23%, neither a correctness ranking. Started hidden no-screen build with the existing pinned Zig 0.15.2 toolchain; no new download. QA records source/actual checks as passed and frozen build as pending.
- 2026-11-01 16:52:40 Asia/Seoul — Resumed after usage interruption. Build completed with no new source changes. Frozen harmonic rejection, omission evidence, CQT/FFT, exports/mixer and native ABI 2 parity pass. Reviewed 17 optional packaging warnings and finalized QA as source/frozen passed, retaining external archive/publication gates. Documentation now distinguishes all completed stages from pending delivery. Parent reviewed strict comparison implementation; no gate weakening or new blocker found.
