# ToneMatch v0.1.04 — evidence-preserving chord trace refinement

Plan Type: revision-plan
Workstream: CQT timing, harmonic context, and bounded chord-path optimization
Version: 02
Status: Source and frozen executable verified; fresh ZIP verification/publication in progress
Created: 2026-10-11 02:56:44 KST (Asia/Seoul)
Last Updated: 2026-10-11 23:07:15 KST (Asia/Seoul)
Supersedes: plan/20261011-023540--work-plan--v0-1-04-chord-trace--v01.md
Current Completion State: 11 trace tests pass on onset-bounded 50 ms observations; scalar scoring and path equivalence pass. Eight headless lifecycle tests pass after the approved selector fix.
Completed So Far: Confirmed existing CQT tuning, candidate evidence gates, fixed overlapping windows, and dynamic-programming trace.
Remaining Work: Regression baseline, bounded implementation increments, comparison metrics, full verification, review, version and release preparation.
Current Blockers: No algorithm implementation blocker. Real-song ground-truth annotations are unavailable; that limits accuracy claims.
Next Step: Create and independently verify the immutable v0.1.04 ZIP, then publish only after digest/source gates pass.

## Approval, objective, and scope

The user approved proceeding after the previous understanding report with “진행ㄹ해”. The approved objective is to improve the accuracy and temporal stability of the song-level chord trace in the next patch, using the supplied music-theory discussion as a source of testable ideas rather than a specification or benchmark. The user explicitly prohibits screen manipulation. Honor that prohibition throughout development, verification, and handoff. Do not activate applications, capture the desktop, open browser tabs, move windows, or launch visible test interfaces. Use command-line tests and isolated, noninteractive analysis. Tests that necessarily display a window must be reported as deferred rather than quietly run.

Preserve the user-approved product direction: analyze the original full mix, not a guitar-only stem, and display chord names with supporting evidence and alternatives rather than fingering diagrams. Preserve both CQT and FFT as selectable methods. Preserve slash chords, suspended and extended harmonies, uncertainty, corrections, chart playback synchronization, saved results, and exports. A smoother line is not necessarily a more accurate line. The new behavior must preserve genuine changes and silence rather than painting familiar harmony across missing evidence.

The local source already contains the v0.1.03 UI repair and method selection. Its verified developer archive is separate from the work in this plan, and has not yet been published. Do not overwrite that archive, silently alter its included documentation, or claim publication. Preserve the previous source and evidence checkpoint before changing files for this patch. Treat the v0.1.03 plan as the related predecessor, superseded as the active implementation plan but with its publication status explicitly retained. This patch must not turn historical verification into a claim about newly changed source.

## Confirmed facts and planning assumptions

The application uses Python, NumPy, SciPy, librosa, Tkinter, an optional C++ DSP library, and a Windows portable packaging workflow. Song-level CQT operates on phase-safe channel magnitudes with harmonic weighting. It estimates a bounded global tuning offset from a small sample of the beginning, middle, and end of the audio. It collapses pitch salience into pitch classes and compares a comprehensive existing chord-template vocabulary. Temporal decoding already chooses a path over locally supported candidates. Therefore, adding another generic Viterbi framework would duplicate existing machinery and increase risk without identifying a real benefit.

The observed baseline uses analysis windows of 1.2 seconds at 0.6-second intervals. Its transition cost does not scale with the time represented by an observation. The candidate transition loop compares each current candidate with every previous candidate despite charging one uniform cost whenever the harmonic label changes. These facts identify bounded opportunities to evaluate: finer temporal evidence, duration-consistent persistence, and exact elimination of redundant path comparisons. They do not, by themselves, prove the source of every incorrect chord in the user's recording.

The Reddit discussion primarily addresses how musicians interpret sheet music and harmony. Its useful hypotheses are to consider bass and sustained chord tones, distinguish passing melody tones, and consult neighboring harmony without assuming the bass is always the root. AudioLabs' primary educational material on HMM chord recognition supports sequence-level decoding while warning that aggressive smoothing can blur genuine changes. Neither source establishes expected performance on this application or on Room 335. Do not treat discussion votes, synthetic success, or detected duration as calibrated musical accuracy.

Use the existing runtime and dependencies first. Do not add an audio model, a download, a new FFT library, an external service, or a forced key-signature prior. Do not port the engine to C++ merely because the user permits it. Optimize an identified bottleneck only when observable behavior can be preserved and measured. A simple exact path optimization in the existing language is lower risk than a new ABI, and the core numerical transforms already execute in optimized numerical libraries.

## Implementation sequence and checkpoints

Begin with a small deterministic regression corpus generated from known pitches and exact change times. Include steady triads, minor and suspended chords, inversions, transient passing melody, sustained extensions, genuinely brief chord changes, silence, and a modulation that cannot be explained by a single fixed diatonic key. Add detuned examples on both sides of standard tuning and a change close to a CQT processing-batch boundary. Include multiple roots and at least one held-out timing offset so the patch is not merely fitted to a single synthetic signal. Record the baseline's failures and metrics before modifying production logic. A test must fail for the intended observable defect, not because an import is missing or the test itself uses a wrong chord spelling.

The first behavioral increment should improve temporal discrimination using the smallest supported change to the CQT observation sequence. Prefer reusing the existing transform frames at a finer temporal sampling rate with bounded batch duration over recomputing a transform per observation. Evaluate the tradeoff between shorter evidence windows and bass-frequency resolution, which comes from CQT filters rather than only the aggregation interval. Ensure that the song's final partial interval and batch seams retain chronological, contiguous events. Keep the legacy FFT front end unchanged unless a shared correction is required and protected by regression tests.

The second increment should make temporal persistence consistent with the actual time represented by an observation. Avoid increasing the apparent strength of a hypothesis simply by sampling it more often. Retain locally required pitch evidence, uncertainty, and alternate names for identical pitch sets. Prefer a duration-aware weighting of existing evidence over learned transition priors with no training data. Do not force conventional progressions or add absent notes from neighboring chords. Passing melody and a real extended chord can share the same instantaneous pitches; use persistence as a limited aid, document ambiguity, and preserve sustained extensions in the test corpus.

The bass contract is conservative. Bass may support the identity of a candidate and must remain available for slash notation, but a changing bass line must not automatically replace the upper harmony's root. Test root-position and inversion changes with stable upper pitches, and verify that transient low-frequency noise does not create a confident alternative root. If a new bass estimator would require broad spectral redesign without a reproducible failing case, retain the existing estimator and state that limitation rather than introduce speculative complexity. Confirm improvements at the event level where the user actually sees the result.

The optimization increment must preserve the exact result of the selected path objective. Uniform change penalties permit comparing the best overall predecessor and the best predecessor with the same harmonic label rather than evaluating all pairs. Prove equivalence against a simple independent reference decoder over deterministic randomized candidate sequences, including tied scores, unknown states, and changes in candidate membership. Preserve stable tie breaking so repeated runs and saved comparisons remain predictable. Bound memory by the existing maximum audio duration and avoid accumulating full-song CQT arrays. Measure improvement separately from changes in the observation rate, because a faster decoder can coexist with more overall work at finer resolution.

After each increment, run the focused regression tests and the directly affected existing suites. Stop on a failure and diagnose it before adding another feature. Record the actual failure and the narrow repair scope in the session record. One bounded repair and re-review loop is authorized for defects within this approved behavior and file surface. Reopen planning if the proposed repair requires a new model, dependency, UI surface, irreversible migration, external media transfer, or substantial redefinition of the accuracy goal.

## Writable scope and interfaces

Keep changes concentrated in the song chord analysis and shared temporal decoder, focused tests, a reproducible developer verification utility when needed, and version, research, QA, and handoff documents. Packaging metadata and self-tests may change only to carry the new version and verify the changed algorithm in the frozen executable. Do not edit unrelated tone recipes, equipment catalogs, mixer behavior, installers, user settings, or old immutable release files.

Maintain the existing output schema. Existing event fields, confidence meaning, alternatives, method identity, timing units, and original-mix source identity must remain consumable by the chart, correction, JSON, HTML, and PDF paths. Add diagnostic fields only when they clearly explain the timing or context policy and remain bounded scalars or compact metadata. The confidence value remains a heuristic evidence score, not a probability of correctness. State that distinction in documentation and evidence reports.

Cancellation must remain observable between bounded pieces of analysis and before returning final results. Progress must remain monotonic and finish at completion. Invalid method selection, empty or nonfinite PCM, unsupported shapes, sample-rate limits, and the maximum duration must retain their existing precise errors. Preserve phase-opposed stereo, quiet defining tones, noise rejection, and empty unknown intervals. Do not hide failed analysis by returning a fabricated successful timeline.

## Validation and measurement

Report separate metrics for harmonic identity and timing. Use duration-weighted agreement against the known synthetic annotations, plus absolute boundary errors for transitions with an unambiguous expected identity. State the tested chord vocabulary and distinguish strict symbol comparisons from root/type comparisons and pitch-set equivalence. A C6 versus Am7 ambiguity is not automatically a defect when the same tones support both; check that alternatives remain available rather than demand an arbitrary exclusive label. Do not choose a looser metric merely to improve the reported score.

For boundary validation, select a target grounded in the new sampling resolution and the synthetic change construction. Report unknown gaps rather than excluding them from accuracy. Include tests that detect an overly persistent decoder by requiring short real changes and modulation to survive, and tests that detect an overly eager decoder by adding brief passing tones to an unchanged backing chord. Do not promise perfect transcription of dense polyphonic audio.

Run the existing song-chord, voicing, method-routing, chart, playback, correction, serialization, and export suites as applicable. Run the full headless-safe suite before accepting the patch. Inspect tests before running the full suite to prevent unwanted visible Tk windows or hardware use; if some tests cannot be safely hidden or isolated, preserve them and report the exact excluded surface. Do not perform actual playback through the user's audio device. Use virtual or fake streams only where existing tests intentionally isolate external effects.

Use the supplied Room 335 MP3 only locally and only for the already authorized analysis. Never upload, commit, package, or copy it into public artifacts. It has no trusted chord annotation; record successful processing, coverage, runtime, event continuity, and evidence diagnostics as operational checks, not as a real-song accuracy measurement. Compare CQT and FFT without automatically declaring whichever yields more events to be better.

Verify the global tuning estimator on existing and new detuned examples before changing its policy. If it already satisfies the bounded consensus tests, retain it rather than invent a claimed tuning improvement. Check batch boundaries for inconsistent labels or timing. Measure decoder cost independently using fixed generated inputs and document the machine-dependent nature of timings. Do not gate correctness on a fragile wall-clock threshold in unit tests.

## Release, rollback, and honest completion

Increase the application patch version to v0.1.04 when the intended source change passes the focused tests. Update the developer notes, build history, research references, and QA evidence with actual results. Do not modify v0.1.03 ZIP contents. Preserve existing user edits and uncommitted records; first checkpoint the known preceding work so changes can be attributed. Use explicit file staging and non-destructive Git operations.

Build a new Windows developer artifact only after the source gates pass and the build is allowed to run without visible windows. Check the packaged native self-test, chord workflow, resource inventory, private-path exclusion, and source/artifact consistency using the established release process. A release is not complete until the upload is verified and the public version and asset digest agree. If packaging or publication cannot be completed in this turn, clearly distinguish implemented source, tested source, built package, and published release, and leave a reproducible next step. Never present a preexisting v0.1.03 artifact as the new algorithm version.

Rollback should remain straightforward: the previous source checkpoint and immutable releases stay available, no saved project migration is required, and FFT remains a selectable independent front end. Avoid automatic replacement of user corrections or old saved chord results. New diagnostics describe newly run analysis only. Review correctness, maintainability, security, performance, and rollback safety before handing off any completed increment.

## Definition of done and unresolved limits

The patch is accepted when regression tests demonstrate a reproducible improvement in the targeted temporal cases, earlier supported harmonies and uncertainty behavior remain valid, the exact path optimization agrees with the reference objective, the headless-safe regression suite passes, and the versioned evidence clearly distinguishes synthetic correctness from real-song uncertainty. Packaging and publication have their own subsequent gates and must be reported explicitly. No UI redesign or visible verification is part of this algorithm patch.

Remaining scientific uncertainty is expected. Dense mixes, overtones, reverb, instrument leakage, missing chord tones, tuning drift, and alternate harmonic interpretations can still cause errors. This patch is a bounded engineering improvement, not a claim of professional-grade perfect transcription. If deterministic evidence shows that shorter aggregation regresses low-register or extended harmonies, select the smallest corrective window/context policy within this plan and verify the complete corpus again. If that is insufficient, stop the behavioral expansion and document the evidence rather than weakening tests.

## Scoreboard

Current Score: 48/100
Score Source: provisional
Last Updated: 2026-10-11 23:07:15 KST (Asia/Seoul)
Rationale: Headless regressions, private-file integration, independent review and packaged executable self-tests pass. Fresh ZIP and public asset verification remain outstanding.
What Improved: CQT timing regressions, exact decoder/scoring equivalence, and device lifecycle recovery are covered.
What Remains Unsatisfactory: Native pointer/visual verification is intentionally deferred; real-song accuracy is not labeled, and the ZIP is not yet verified/published.
Next Score Action: Finish immutable archive validation and public digest readback.

Score History:
- 2026-10-11 02:35:40 KST (Asia/Seoul): 28/100 provisional. Approved scope recorded; no claim of implementation or measured improvement.

## Progress log

- 2026-10-11 23:07:15 KST: Continued from durable build output. v0.1.04 frozen self-test passed all music workflow and C++ ABI 2 checks. Headless suite passed 318 cases in 56.648s with warnings as errors; 92 GUI cases deferred and guarded. Both private-file frontends passed edit/reopen/export/cancel checks. Independent review reported no actionable findings and 23 focused tests passed. QA status covers source and frozen gates; archive/publication remain external gates. Score 48/100 provisional, not musical accuracy.
- 2026-10-11 08:28:10 KST: Eight lifecycle test methods exercised real completion/error/availability handlers without Tk windows. RED reproduced eight failing subcases; GREEN passed all eight methods in 0.023 seconds. Terminal events retire analysis state before refreshing controls; idle chord mode permits modeler selection but leaves tone-only settings disabled. Other active operations still lock controls; result refresh does not retire a live task. Updated the deferred native UI expectation. Independent read-only algorithm review is running under the runtime's proactive delegation instruction; no delegated writes or screen use.
- 2026-10-11 02:50:52 KST: User highlighted tempo-relative timing. Added 180 BPM quarter-note changes and 60 ms clean-boundary targets within the approved timing scope. Plain 50 ms hops reproduced mixed-boundary false extensions; an independent short STFT now locates changes only, while CQT remains the pitch source and evidence windows shift inside detected harmonic regions. A low-note beating regression required enough STFT frequency resolution; all nine audio trace tests now pass. No generic 50 ms accuracy guarantee is claimed. Previous 307 headless tests passed before this additional boundary work; 87 GUI-containing cases were deliberately excluded. Re-run the headless suite on the final source.
- Exact path optimization passed 100 randomized objective comparisons; 6000 observations with 24 candidates improved median decode time from 1.112 s to 0.152 s in the isolated measurement. Fine observation profiling found template scoring used 1.68 of 2.48 profiled seconds on a 12-second synthetic clip. The next bounded optimization groups the same template operations with NumPy and requires scalar-score/classification equivalence; no C++ ABI or dependency change.

- Five audio regressions passed after the timing/merge increment. Existing song, voicing and method suites passed 49 tests in 34.453 seconds. Added duration evidence and randomized reference-path tests; RED showed a brief extension was incorrectly strengthened by more observations. Duration weighting made all seven new tests pass (5.870 seconds), including 100 deterministic path cases. Existing FFT observations retain their original default weight. Next step is separately measured exact decoder optimization.

- Baseline RED confirmed: the 0.8-second E chord became unknown; transition errors were 0.23 and 0.17 seconds. Shortened CQT evidence windows to 0.6 seconds with 0.2-second hops while preserving approximately six-second transform batches. Initial finer-grid check exposed duplicate identical symbols when a non-chord bass leaked across a transition. Grouping now follows the actual chord/slash symbol, retaining genuine inversions while avoiding those duplicate events. Focused verification follows before further changes.

- Preserved v0.1.03 documentation and evidence in commit 1edefc6. Added five labeled-signal regressions. First run reproduced a missing 0.8-second E chord but also exposed a test-only sharp spelling mismatch; corrected that fixture before interpreting timing results. Production algorithm remains unchanged.

- 2026-10-11 02:35:40 KST (Asia/Seoul): Read the active global instructions and approved scope. Confirmed no screen manipulation, preserved predecessor release state, and recorded the implementation/verification contract before writing code.


## Approved UI lifecycle amendment — 2026-10-11 02:56:44 KST

The user reported that the multi-effects selector cannot be used after chord analysis in v0.1.02. A command-line harness executed the checked-in v0.1.02 event and completion handlers and reproduced two distinct facts without creating Tk windows. Chords-only purpose intentionally keeps the selector disabled even when idle. Independently, when a done event is handled before the analysis worker has fully returned, availability observes the still-live worker and disables the selector. A subsequent empty event poll does not restore it, although the worker is then dead. The same lifecycle behavior is present in the current source.

After an understanding report and an explicit scope question, the user approved “두 가지 모두 수정”. This revision adds the modeler selector and analysis completion lifecycle to the writable scope. This approval does not permit screen manipulation, visible windows, unrelated device-catalog changes, or automatic changes to the analysis purpose. Retain the original algorithm objectives and all earlier limitations.

Add a headless regression that drives the real event-drain and completion methods through controllable completion ordering. Mock widgets and external effects, not the state transitions being fixed. Cover success, failure, and cancellation; verify the selector remains locked while analysis is actually in progress and becomes selectable after completion. Verify idle recovery when the completion event is consumed just before the thread exits. Do not clear the worker merely because a displayed result is refreshed: reopening a result, language changes, manual chord edits, and actual worker completion are different events.

Use the existing queue completion boundary to retire the completed analysis state. Avoid per-poll widget mutation if an explicit terminal event can establish the state once. Do not join a worker on the UI thread. The worker has already finished all analysis work before publishing its terminal event; only task bookkeeping and return remain. If future job identities are needed, treat that as a separate design question rather than adding speculative orchestration now. Keep the immutable analysis request independent of any later selected hardware.

Allow the idle modeler selector in chords-only purpose. The analysis engine must continue ignoring modeler recipes in that purpose, including when an unsupported future hardware slot is selected. Keep tone-specific pickup, mix, output, and compute controls disabled when they do not apply. Do not automatically switch to tone analysis when a modeler is selected. Update only necessary Korean/English explanatory text if the existing text would falsely imply that the chosen device affects chord extraction. Preserve the user's selected device for the next tone analysis.

Confirm that other active operations and hardware probes still enforce their existing interlocks. Device selection must not undermine the snapshot request of an ongoing analysis. Existing results must retain their recorded device identity until a new tone analysis actually runs. Ensure failed or cancelled analysis does not leave a stale success state, and avoid modal dialogs in tests by replacing only the message-box boundary.

Include these cases in the headless-safe suite. Update the previous UI expectation that chords-only always disables the device selector so the test documents the newly approved behavior. Do not claim native click/dropdown verification, since the user prohibits operating the screen. A deterministic mocked-widget lifecycle test proves the state fix, not pixel layout or real pointer routing. Report this validation boundary plainly.

The publication gate now includes this lifecycle fix and its tests; do not release v0.1.04 with the newly confirmed lock defect unresolved. Keep v0.1.03 archive preservation and prior publication status intact. A new dependency or a broader event-framework rewrite is not authorized. Finish with a read-only review of both the music algorithm and task-state cleanup, and update the durable session record with exact test results and remaining packaging work.

Score History continuation:
- 2026-10-11 02:56:44 KST (Asia/Seoul): 42/100 provisional. Focused timing/fast-tempo/scalar-equivalence improvements are demonstrated; a reproduced selector lifecycle bug and release verification remain. This is not an accuracy score.
