# v0.1.06: Improve chord evidence without inventing harmony

Plan Type: Work plan
Workstream: ToneMatchTMP v0.1.06 chord precision
Version: 01
Status: Superseded by approved plan/20261031-062555--revision-plan--v0-1-06-conservative-precision--v02.md
Created: 2026-10-22 21:43:21 Asia/Seoul
Last Updated: 2026-10-31 06:22:58 Asia/Seoul
Related Plan: Completed v0.1.05 uncertainty patch; this is a new independently approved accuracy scope
Current Completion State: Controlled precision gains observed, release blocked by transient and harmonic false positives
Completed So Far: Approved plan, classifier/CQT/metric RED checks, frozen-diagnostic RED check
Remaining Work: Regression tests, bounded evidence and classification improvements, integrated comparisons, review, versioned build and release
Current Blockers: FFT residual inference still creates new false chords; CQT low-signal and fixture endpoint repairs remain incomplete
Next Step: Obtain approval for a narrower conservative revision; do not publish the current candidate

## Approval and intent

The user explicitly approved the preceding understanding report with “넵 승인할게요”. The approved scope is a v0.1.06 precision patch, retaining CQT and FFT, improving actual-note versus harmonic discrimination, preserving arpeggiated evidence, improving omitted-tone, extension and slash-bass decisions, comparing errors and processing cost against the previous version, and publishing a developer ZIP and GitHub release after verification. This is not approval for additional UI features, external AI models, remote processing of user audio, or a general rewrite. Continue without another approval prompt for ordinary implementation, verification and bounded repairs within this record.

Honor the user's no-screen-manipulation instruction. Do not activate or move windows, open browser tabs, play audio, launch visible native applications, exercise input hardware, or physically print. Run command-line work and explicitly hidden child processes only. Use the existing hard Tk guard for the non-GUI suite and disclose GUI-containing tests as deferred. Do not represent headless model tests as a native pointer or visual click-through. Do not run general discovery outside that guard if it can construct a Tk root.

Follow the global AGENTS instructions and the existing project conventions. Use Asia/Seoul for human-facing timestamps. Preserve v0.1.05 source, immutable release tag and published assets. The clean baseline at approval is main commit 7017e91, with v0.1.05 tagged source 83e88c10f62f6b174b2f95cf0e68b751a14f4db0. Establish comparisons against the tagged release, not against a continuously changing checkout. Any generated comparison must record the actual source hashes and baseline reference.

## Objective and limits

Improve the existing whole-mix chord analyzer rather than add another visible mode. The result should miss fewer supported chords while preserving abstention on noise, single-note material, insufficient evidence, and genuinely ambiguous harmony. The primary goal is not an increased number of named intervals. Wrong confident output is worse than a useful unresolved interval with honest alternatives. Preserve the chart's primary unknown marker, bounded alternatives, explanatory evidence, manual correction workflow, exports, persistence, playback alignment and device-selector lifecycle.

The read-only research identified three reproducible mechanisms. The FFT front end can remove an independently played chord tone when its frequency lies near a low note's harmonic. The complete-template gate prevents an omitted perfect fifth from entering otherwise plausible seventh or ninth candidates. The CQT per-bin temporal median can erase sequential notes occupying less than half a window. Separate these mechanisms in tests and changes. Do not claim that each is the cause of the user's particular Room 335 errors without annotated ground truth.

The existing Room 335 MP3 is authorized for local operational regression only. Never upload, commit, redistribute or package it. Its detected coverage is not accuracy. Synthetic signals with explicit note construction can establish narrow correctness properties; they are not a held-out commercial-music benchmark. Do not advertise a general accuracy percentage based on these fixtures. State any residual unresolved cases, including ambiguous names such as C6 versus Am7, rather than force one interpretation solely because it is common.

## Technical approach and constraints

Retain the existing Python, NumPy, SciPy and librosa stack and the C++ ABI. Prefer vectorized bounded operations and reuse already computed spectra. Do not add a new dependency or model download. C++ migration is not part of this patch unless profiling establishes an unavoidable bottleneck that can be addressed without changing the ABI or build trust boundary; if it would materially expand scope, report it instead of silently rewriting the engine. Correctness changes come before numerical or language-level optimization.

Use the reviewed primary research as motivation, not copied source code or a guarantee. NNLS-style harmonic dictionaries and separate bass chroma are useful comparison ideas, but introducing a large solver or costly per-observation optimization is not mandatory. Choose the smallest evidence-based front-end change that fixes the reproduced failure and survives negative controls. Test a soft harmonic explanation or residual contribution rather than erasing every peak near an integer multiple. Do not count every harmonic as an independent note either. Protect single instruments with strong overtones and actual chords sharing those harmonic locations.

Preserve register information long enough to distinguish bass evidence from the pooled pitch-class profile. Do not equate the lowest weak spectral bump with a stable slash bass, and do not assume that the bass must be the root. Keep support requirements for slash labels explicit and conservative. Any new evidence must remain finite, bounded and compatible with existing JSON/export validators. If an optional metadata field would not round-trip safely, prefer expressing the improvement within the existing evidence contract rather than adding an unvalidated field.

For CQT time aggregation, preserve repeated or decaying note evidence within a stable harmonic interval without pooling across a real chord change. Compare a robust upper-energy statistic or bounded note memory to the current median using deterministic spectra and actual synthetic PCM. Verify abrupt changes, short real harmonies, passing melody tones, silence and batch boundaries. Merely increasing the evidence window or reducing observation hop is not sufficient. Preserve phase-safe channel handling, tuning estimation, the twenty-minute input bound, event budget, cancellation checks and monotonic progress.

For omission-aware interpretation, allow only explicitly justified omissions. A perfect fifth may be optional in selected extended templates when root, characteristic third and the claimed extension or seventh remain supported. Do not permit a bare root and third to imply a full major chord, invent a missing root, or treat a missing altered fifth as optional. Do not claim a seventh, ninth, eleventh or thirteenth without its defining observed evidence. Penalize unnecessary complexity and preserve competing names as alternatives. Keep full-template behavior consistent with the scalar/vectorized scoring contract. Test every allowed family across transpositions and preserve unknown handling for inadequate inputs.

Existing temporal decoding already has local candidate support and duration weighting. Preserve its acoustic anchor and avoid turning likely musical progressions into invented chords. This patch may refine local evidence consistency or bass stability within the current decoder contract. A trained key model or new global progression engine is not required and must not be added as an unrelated feature. Use context only to arbitrate supported candidates, not to manufacture missing notes. Preserve genuine fast changes and modulation in the existing timing regressions.

## Work sequence

First, add observable regressions before changing the corresponding behavior. Capture the known FFT low-bass C-triad failure, a harmonic-rich single-note negative control, omitted-fifth extended chord evidence, and sequential-note CQT aggregation. Run each focused test in its failing state and record that the failure is the intended one, not a missing dependency or incorrect fixture. Add realistic variation in octave, root, amplitude, articulation and noise so a single special-case signal is not the only proof.

Second, develop the front-end/classifier slice and the CQT aggregation slice with exclusive file ownership. The parent remains responsible for integration. The classifier owner may edit voicing.py and focused classifier tests; the CQT owner may edit song_chords.py and focused CQT tests. Neither should alter the other's file without coordination. Other agents may inspect or independently validate, but do not launch external worker scripts, create user-owned chats, change model settings or assume isolated worktrees. Every worker must use the actual shared runtime and preserve concurrent changes.

Third, run the affected song, voicing, score, temporal path, reanalysis, uncertainty and method suites. Inspect old expectations before updating tests: a changed acceptance contract may justify a documented expectation change, but an inconvenient regression is not a reason to remove or weaken a test. Preserve the counterexamples that prevent false chords from noise and dyads. If a proposed change only improves coverage while adding wrong labels, stop and narrow the change before moving forward.

Fourth, run the existing uncertainty comparison and timing comparison against v0.1.05 with both front ends. Extend the quality tool only when required to include the newly reproduced cases and evaluate the same fixture against both versions. Record correct recognized duration, incorrectly recognized duration, unknown duration, candidate behavior and processing time independently. Include transposed and octave-varied cases not used to tune the implementation. Keep development fixtures explicitly labeled as such. Do not remove a failing stress case to make the aggregate appear better.

Fifth, validate the actual local Room 335 input with CQT and FFT without playback or upload. Check progress, cancellation, event continuity, finite evidence, original-mix source identity, manual edit preservation, reopen consistency and HTML/PDF export data. Record coverage and runtime as operational measurements only. Confirm that user audio and temporary analysis paths cannot enter the public package. Preserve source analysis rather than replacing it with a manual edit or a candidate.

Sixth, run the complete guarded non-GUI suite with warnings treated as errors, followed by an independent read-only review. Review changes for false-positive risk, behavior outside the intended chord slice, compatibility of evidence and persistence, cancellation/performance regressions, and source-to-artifact provenance. A single bounded repair loop within this approved surface is authorized for defects found by verification or review. Reopen planning for a new dependency, model, UI surface, trust boundary, audio upload or materially different product behavior. A persistent same-root-cause review failure must not be hidden by repeated unbounded repairs.

## Writable surface and record keeping

The approved writable surface includes the existing chord analysis modules, directly affected tests, deterministic quality/comparison tools, hidden verification helpers if a narrow proof gap requires them, and the normal version/build/release/documentation metadata. Do not redesign unrelated tone recipes, equipment catalogs, playback, source separation or UI styling. Changes to shared import/export handling must be minimal compatibility repairs supported by a failing regression, not a new format or feature. Preserve historical version documentation and publish new version evidence instead of overwriting older reports.

Maintain this plan and the v0.1.06 session summary at meaningful implementation and verification checkpoints. Record red/green evidence, commands, measured failures, reviewed decisions and next actions, keeping logs in project-local run or work directories. Worker notes may be returned to the parent for a coordinated plan update; workers must not concurrently rewrite the shared plan. Use apply_patch for source and Markdown edits. Use existing generation/build commands for mechanical artifacts rather than hand-editing generated binaries or reports.

## Acceptance and publication gates

Accept the source only when the reproduced defects have targeted passing tests, the affected existing suites and guarded full suite pass, and comparative quality evidence shows a useful improvement without unexplained false-positive regressions. Timing checks must preserve short changes and not merely make labels smoother. Treat any threshold choices as conservative engineering parameters, not calibrated probabilities. Report processing cost after warm-up separately from startup/JIT effects where the tool supports that distinction.

After source acceptance, bump all current version metadata to 0.1.06 and write release notes, build history, developer handoff and a new QA report. Explicitly document what improved in controlled tests, what is merely operationally verified on Room 335, and what remains untested because screen interaction is prohibited. Preserve the existing CQT/FFT user choices; do not add a new user toggle to expose an unfinished algorithm. Do not reintroduce guitar fingering or separated-stem displays into the whole-song chord view.

Build a new unsigned Windows portable developer package through the established hidden build procedure. Verify its native self-test, source snapshot, dependency and font resources, version markers and manifest. Extract the exact candidate ZIP to a fresh validated task directory and run the hidden frozen self-test there. Compare every manifest entry and source hash. Never overwrite a previous version's package, release tag or published asset. No recursive deletion outside an explicit validated build target is authorized.

Freeze a clean reviewed source commit, bind the version tag and archive to that commit, then publish v0.1.06 as a developer prerelease on the existing repository. Verify uploaded asset sizes and SHA256 digests and read the published release back. Publication is complete only when the remote assets agree with the locally verified files. Keep credentials out of logs and use the existing authenticated release mechanism without displaying tokens. If an external permission or service blocks publication, report the exact stage and do not claim the source-only patch is released.

The final handoff must distinguish implemented, tested, packaged and published states. Include the release link when publication succeeds, the most useful measured improvements and remaining limitations. Keep the prior portable folder and previous results available for rollback. Do not claim perfect transcription, independently measured real-song accuracy, or visual QA that did not occur.

## Scoreboard

Current Score: 35/100
Score Source: provisional
Last Updated: 2026-10-31 06:22:58 Asia/Seoul
Score Rationale: Useful targeted improvements are retained, but a persistent false-positive cause and two uncompleted boundary repairs prevent release; the first bounded loop requires replanning.
What Improved: Specific causal failures and measurable acceptance criteria replace a broad request for accuracy.
What Remains Unsatisfactory: The released analyzer still exhibits the reproduced limitations; the real song has no verified chord annotation.
Next Score Action: Demonstrate red-to-green improvements without degrading negative controls and publish only the verified result.

### Score history

- 2026-10-22 21:43:21 Asia/Seoul — 40 provisional: New approved precision workstream; no accuracy percentage or user satisfaction score is inferred.
- 2026-10-31 06:22:58 Asia/Seoul — 35 provisional: First-loop harmonic fix still fails with a weak unrelated tone. No real-song accuracy or user score is inferred. Preserve evidence and seek approval for a smaller safe scope.

## Progress log

- 2026-10-31 06:22:58 Asia/Seoul — Read-only continuation. Parent reproduced current C5 versus baseline ? for a formant-rich single tone plus a weak Bb on 2026-10-27; the weak independent anchor bypasses the guard. Same root cause survives loop 1, so return to planning under the parent-session skill. Proposed narrower revision restores only conservative FFT harmonic suppression while retaining CQT and omission-aware classification; attempted FFT low-bass gain would be explicitly deferred. Quiet-region and exact-frame fixture regressions remain RED and will be included in the revised scope. No source implementation, build or publication in this turn.

- 2026-10-27 21:33:35 Asia/Seoul — Attempt2 ran 383 tests with 17 errors from two distinct newly introduced boundary bugs: missing low-signal observation field and cumulative floating-point fixture endpoint. Comparisons aborted. Refresh same first repair loop for guarded low-signal return and integer-frame truth construction; strict correctness gates remain unchanged. Original false-label assertions no longer fail in this run, but full acceptance is not yet established.

- 2026-10-27 21:31:16 Asia/Seoul — Resumed retained first-loop repairs. FFT guard requires genuine nonharmonic evidence before residual harmonic energy can support polyphony; CQT preserves median evidence before narrowly considering sequential notes. Expanded precision controls to 56 method cases; package gate updated accordingly. Running 383 guarded tests and attempt2 comparisons, with independent read-only re-review. No build/tag/publication. Provisional score stays 40 because integration acceptance is pending.

- 2026-10-25 21:45:45 Asia/Seoul — Continued the existing first bounded repair after interruption; no completed repair/re-review is claimed. Parent added per-case trace gates with RED-to-GREEN five tests, resolved baseline commit and before/after hashes. Package helper requires that report to pass. Workers retain exclusive FFT/CQT/precision-fixture ownership. No new dependency or public release action.

- 2026-10-25 15:14:14 Asia/Seoul — Integrated verification completed: 372 tests with two trace failures; 34 precision and 32 uncertainty comparisons pass, but eleven-sequence trace loses one transition and drops from 0.9935761 to 0.9888930. Independent reviewer reproduces FFT false positives from formant-enhanced single-note harmonics. Open first bounded repair within existing analyzer/tests/tool surfaces; preserve failed receipts and do not weaken correctness gates. Source accuracy gains are narrow synthetic evidence, not release acceptance or real-song accuracy.

- 2026-10-25 15:14:14 Asia/Seoul — User requested continuation after runtime interruption. Sources held static for guarded full suite (372 selected, 92 GUI deferred), precision/uncertainty/trace comparisons and independent read-only reviews. Classifier focused suite and CQT three target tests pass, but early full-suite failures block acceptance; preserve attempt1 receipts. No version bump/build/publish. Score remains 40 pending complete regression evidence.

- 2026-10-25 10:25:17 Asia/Seoul — Initial classifier regression suite passes, but added odd-harmonic negative controls exposed eight new false positives; test-first same-parity envelope repair is being checked before acceptance. CQT targeted aggregation/shoulder/arpeggio tests now pass, with broader controls pending. Precision metric/provenance suite passes 14 tests. Prepared versioned workspace package verification helper with strict precision/source/frozen gates; three offline publisher tests pass. No final comparison, build or publication yet.

- 2026-10-25 10:23:21 Asia/Seoul — Continued user-approved scope. Retained partial FFT/classifier and CQT changes and the new precision tool; all require current verification. Assigned disjoint completion/audit work. Reuse existing private-file verifier. Score remains 40 pending measured improvement; no version bump, commit or publication yet.

- 2026-10-22 21:43:21 Asia/Seoul — User approval received. Baseline is clean main 7017e91 and immutable v0.1.05 source. Plan created before any implementation. No screen interaction or media transfer is authorized.
- 2026-10-24 08:16:33 Asia/Seoul — Resumed after worker execution interruption. Three new focused test files exist; production analyzers remain unchanged. Verify those tests and capture RED, then continue the same approved scope. Provisional score remains 40; no implemented or measured improvement yet.
- 2026-10-24 08:19:04 Asia/Seoul — RED confirmed: classifier five tests with 78 expected subtest failures (low-bass deletion and optional-fifth rejection); CQT two intended failures (grid and actual decaying PCM); metric tool import missing; frozen diagnostic missing new precision checks. Added hidden frozen checks for low-bass FFT and omitted-fifth evidence reopening. They await analyzer implementation; no passing improvement claim yet. Existing negative controls remain required.
