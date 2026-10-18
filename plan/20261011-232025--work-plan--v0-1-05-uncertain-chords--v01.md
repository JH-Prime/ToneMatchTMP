# v0.1.05: Preserve uncertain chord evidence and recover bounded missed intervals

Plan Type: Work plan
Workstream: ToneMatchTMP v0.1.05 uncertain chord handling
Version: 01
Status: Complete; verified developer prerelease published and publicly read back
Created: 2026-10-11 23:20:25 Asia/Seoul
Last Updated: 2026-10-18 23:47:33 Asia/Seoul
Related Plan: Completed v0.1.04 chord trace and device lifecycle plan
Current Completion State: Approved uncertainty implementation, verification and v0.1.05 publication complete
Completed So Far: 348 guarded tests, 32 quality cases, 11 unchanged trace fixtures, CQT/FFT actual sample/export checks, independent review and offline Korean/English PDF inspection
Remaining Work: None in the approved patch scope; native UI/listening and real-song accuracy remain disclosed limitations
Current Blockers: None within the no-screen operating constraint
Next Step: User review of v0.1.05; any newly reported fix starts a separately scoped v0.1.06 patch

## Approval and authority

The user has explicitly replied “진행해” to the proposed v0.1.05 scope: reanalyze uncertain intervals at different analysis lengths, preserve up to three supported candidates, distinguish reasons for failed identification, and keep these details consistent in the chart, HTML, PDF, and reopened analysis. This approval includes implementation, tests, and a developer patch release after the evidence gates pass. The preceding understanding report is the scope authority; this document operationalizes it without adding product features.

Continue to follow the global AGENTS instructions and the project conventions. Use the active session timezone, Asia/Seoul, for human-facing records. Retain the user's no-screen-manipulation instruction: do not open windows, control browsers, play audio, exercise hardware, or launch visible applications. Use shell commands and hidden headless subprocesses only. Screen interaction is not necessary to modify a Tk application, but lack of a visual click-through must be disclosed rather than called verified.

## Objective

Make uncertain or missed chord intervals useful without turning absence of evidence into a confident musical claim. The primary outcome is a truthful timeline: recognized chords remain recognized, uncertain intervals retain the musical evidence that actually exists, and silent or non-tonal intervals remain explicitly unresolved. A small bounded second analysis may recover a chord only when that analysis meets the same or stronger support requirements. Do not optimize merely for a higher proportion of named intervals.

The user has already clarified that chords should describe the overall audio rather than guitar alone. Continue to show chord names and, below them, supporting notes and alternatives. Do not reintroduce fingerings, fret diagrams, guitar-only assumptions, or separated instrument audio into the chord view. Keep the existing CQT and FFT choices, manual correction workflow, playback synchronization, and sixteen-bar chart organization. The new work must not weaken the recently fixed device selection lifecycle.

## Established facts and limitations

The current classifier can calculate scores and then return a completely empty unknown observation when coverage or confidence is below its acceptance threshold. Temporal filtering can similarly discard a locally supported label and replace it with a blank unknown observation. This destroys information that could help users distinguish ambiguity from absence of tonal evidence. The UI and HTML renderer also suppress evidence and alternatives for unknown events; preserving data in the analyzer alone therefore cannot solve the visible problem.

The current chart deliberately coerces unknown events to a question mark. Preserve that semantic protection rather than placing a candidate chord into a field that means an accepted result. The PDF renderer already supports some event details, but it needs consistent uncertainty wording. Saved analysis currently tolerates evidence and bounded alternatives; additional metadata must be validated at the import boundary. Manual corrections currently remove stale automatic evidence from the effective view while preserving raw analysis. Maintain that behavior.

The local Room 335 sample is available for regression and performance comparison, but it has no verified chord annotation. Its recognized coverage is not an accuracy measurement. Synthetic audio with known harmony can measure a bounded correctness property and expose regression cases, but it must not be described as an independent real-song accuracy benchmark. A lower unknown rate by itself is never a release acceptance criterion.

## Technical direction and smallest safe assumptions

Use the existing Python, NumPy, librosa, and Tk stack. The requested changes are evidence policy and presentation, not a demonstrated native performance bottleneck. Retain the existing C++ DSP library and ABI without rewriting the classifier in C++ merely to satisfy a language preference. If timing evidence reveals an unacceptable regression, first bound or reuse existing analysis rather than introduce another native subsystem or dependency.

Represent uncertainty as explicit, small metadata attached to the existing evidence and alternatives path. Keep unknown events unknown at the primary chord level. Use a finite set of reasons that distinguishes weak or competing evidence, insufficient tonal evidence, very low signal or silence, and observations rejected for inadequate temporal support. Distinguish synthetic uncovered gaps from analyzed intervals. Legacy results lacking the new metadata must continue to display safely as unresolved without inventing a cause.

Use conservative language in both Korean and English. A question mark means the system did not establish a chord, not that no chord exists in the recording. Silence is not equivalent to the music-theory symbol N.C. A confidence or match score is not a calibrated accuracy percentage. Alternatives are candidate interpretations, not additional simultaneously sounding chords. A manual correction is the user's selected interpretation and must not inherit automatic uncertainty claims.

## Phase one: establish regression proof and the evidence contract

Start with fast tests that reproduce the data loss and display suppression. Include an unknown observation with genuine local pitch evidence and a plausible candidate. Demonstrate that the current implementation loses that information or fails to render it. Also record negative cases such as silence, a lone pitch, flat chroma, and non-tonal noise. These tests should fail for the requested behavioral change before production code is changed.

Agree on a minimal contract shared by analyzer, persistence, chart normalization, and renderers. Prefer extending existing evidence dictionaries over a broad public schema redesign. Keep candidate arrays bounded at three and metadata values finite and validated. Do not accept arbitrary objects, non-finite numbers, huge collections, invalid pitch classes, or unexpected enum values from imported JSON. Preserve compatibility with existing analysis files and avoid changing the saved schema unnecessarily.

Parallel work may proceed only after that contract is stated. Allocate independent file surfaces to avoid conflicting edits: the parent owns classifier and reanalysis logic, one worker owns chart and persistence integration, and another owns the application and export presentation. Every worker reads its applicable instructions, stays within the approved plan, writes tests before behavior changes, and avoids GUI creation. The parent remains responsible for integration and acceptance. Runtime-provided collaboration tools take precedence over imported examples assuming different agent mechanisms.

## Phase two: preserve evidence without relaxing accepted chord thresholds

Keep the current accepted-chord decision policy as the baseline. Where a decision abstains, preserve measured pitch classes, a bounded set of plausible complete-template candidates, and a reason explaining why the observation was not accepted. Never manufacture a missing third, seventh, or root merely because a common progression would make that chord convenient. Do not list candidates for flat/noisy profiles that provide no discriminating support.

When temporal smoothing rejects a locally plausible result, carry its own evidence into the unresolved state. Do not replace it with the neighboring accepted chord. Preserve the intended behavior that brief uncorroborated detections remain uncertain. When observations merge into events, do not combine unrelated uncertain candidate sets across an entire song into one misleading representative. Group or aggregate in a way that keeps local reasons and candidate support meaningful while bounding event count and memory.

Output-size limiting is distinct from analytical uncertainty. If an interval is unknown because of a deliberate output limit, do not reinterpret that as a recoverable failed analysis or attach invented evidence. Preserve source time coverage, monotonic non-overlapping intervals, and the exact overall duration. Keep slash chord identity intact; the recent fix prevents bass-only distinctions from being erased accidentally.

## Phase three: bounded alternate-length reanalysis

Revisit only genuinely uncertain tonal observations, and reuse already computed signal features wherever possible. Limit the number of alternate lengths and candidates; do not recursively retry until a chord is found. Keep the same selected frontend identity: CQT results must remain CQT and FFT results must remain FFT. If alternate analysis is unsupported for one path, document the narrower behavior rather than silently switching methods.

A shorter evidence window may reduce transient contamination; a longer one may improve support for weak sustained harmony. Both can also blur transitions or borrow unrelated notes. Bound reanalysis within observed harmonic boundaries where available, require real local note support, and refuse to span silence or a known change merely to reach an acceptance threshold. Promotion should require consistent, locally corroborated evidence and should not override an already accepted observation solely to increase coverage.

Retain a reason and supporting metadata when reanalysis remains inconclusive. Record enough small diagnostics to determine whether retries were attempted, recovered any intervals, and stayed within their budget. These diagnostics are operational evidence, not user-facing probability claims. Check cancellation in any added loop and ensure the existing progress mechanism does not freeze for long unbounded work. Keep a predictable upper bound for twenty-minute input.

## Phase four: complete the user-visible path

The main chart should continue to show a question mark for unresolved intervals, with an explicit unresolved marker where space permits. Below the chart or in the existing details section, show candidate names and measured evidence without presenting a tentative label as a confirmed chord. If every interval is unresolved but some contain candidates, replace a blanket empty-result impression with clear guidance to inspect those candidates or correct the interval manually.

The application, HTML, PDF, and reopened analysis must agree on the distinction. Use the existing typography and localization conventions. Avoid unrelated layout redesign or new preference controls. Preserve sixteen-bar pagination and bounded detail output so long recordings do not cause a large unresponsive UI update. Keep long symbols and reasons safely escaped in HTML and wrapped or bounded in PDF.

Manual corrections must continue to take precedence in the effective view. Correcting an uncertain event should display the chosen chord without stale automatic claims; undo must restore the original uncertainty data. Do not incidentally enable editing of synthetic timeline gaps whose event index does not refer to an analysis event. Preserve old JSON compatibility and reject malformed new metadata before rendering.

## Phase five: verification and comparison

Run focused unit and boundary tests first, then the repository's guarded headless suite. Do not invoke the full unguarded suite: some existing tests construct real Tk windows. The no-screen runner intentionally excludes native GUI tests and raises if Tk or Toplevel creation slips through. Report the exact executed and deferred counts rather than describing the entire suite as tested.

Test genuine candidate retention, different reasons, no fabricated candidates on silence and noise, stable accepted chords, manual correction and undo, old JSON reopening, invalid imports, chart normalization, renderer visibility, HTML escaping, and PDF generation. Use actual production rendering paths with fake widget boundaries or captured output where necessary; do not test a duplicate miniature renderer.

For analysis quality, compare before and after on deterministic known-harmony fixtures including ambiguous pitch sets, weak chords, fast transitions, low-register chords, silence between chords, noisy material, and unsupported or incomplete harmonies. Measure correct recovery separately from incorrect promotion. Re-run the existing fast-chord trace corpus to ensure alternate-length logic does not undo v0.1.04 timing improvements. Test method identity, bounded runtime, cancellation, and finite output.

Analyze the same local Room 335 sample without playback or upload and record runtime, event counts, recognized coverage, uncertain-candidate coverage, and remaining unknown coverage for each selected method. Explain that those numbers quantify behavior and responsiveness, not truth against a missing reference annotation. Keep the user's MP3 and machine-specific paths out of the public package and logs.

## Phase six: review, packaging, and release

Finish implementation with an independent read-only review focused on false certainty, persistence boundaries, temporal leakage, runtime bounds, and UI consistency. Review the complete diff and ensure unrelated work is untouched. If review finds a defect, record a bounded repair scope before modifying it, add or refine the relevant regression test, re-run the narrow proof, and review again. Do not silently expand the feature scope or claim a passing check that was deferred.

After source tests pass, update the version to v0.1.05 and refresh the release notes, developer handoff, build history, QA report, and relevant usage documentation. Keep historical version dates and previously published release artifacts immutable. Explain the uncertainty policy and its limits in the release notes. The language should describe improved handling and bounded recovery, not promise perfect transcription.

Build the Windows developer portable package using the existing hidden/headless workflow. Explicitly run the guarded suite before using a build option that skips tests. Verify the frozen executable without launching its GUI, including CQT and FFT analysis, reopened corrected results, relevant export paths, and the unchanged native DSP integration. Package only approved source and assets; retain licenses and existing model-management behavior.

Create a fresh v0.1.05 ZIP, checksums, and independent archive-verification receipt. Verify every manifest entry and source snapshot against the release commit, extract into a fresh validated directory, and run the hidden frozen self-test from that extracted copy. Do not overwrite v0.1.04 or reuse stale verification evidence. Publish a developer prerelease on the existing repository only after all required gates pass, verify all uploaded asset digests, and confirm public readback. Record the tag commit, archive digest, asset sizes, and KST publication time. Then leave a clean pushed repository and a concise user handoff with the release link and residual limitations.

## Risks, rollback, and completion criteria

The principal risk is increasing false positives while trying to remove question marks. Address it by keeping abstention explicit, requiring measured notes, restricting second-pass promotion, and checking negative controls. Another risk is merging different uncertain intervals into a misleading single candidate. Address it with local segmentation and evidence-aware aggregation. Data import is a trust boundary; validation must precede rendering. Headless tests cannot establish native visual quality, so do not overstate that evidence.

No external model download, commercial transcription API, new training corpus, account mutation, or UI automation is required. If a new dependency or broader redesign becomes essential, pause and obtain approval rather than stretching this plan. The conservative fallback is always to retain a truthful unresolved interval with its available evidence.

The definition of done is an end-to-end tested uncertainty path, bounded and justified recovery, no regression in relevant existing tests, updated documentation, reviewed source, independently verified frozen package, and confirmed developer prerelease publication. If packaging or network publication is blocked, preserve verified source and artifacts, state precisely what remains, and do not claim release completion. Rollback consists of reverting the scoped source commits or using the immutable previous release; saved legacy analysis remains readable.

## Scoreboard

Current Score: 49/100
Score Source: provisional
Last Updated: 2026-10-18 23:47:33 Asia/Seoul
Rationale: Approved patch delivered with source, frozen, fresh-ZIP and public asset proof; user acceptance and real-song accuracy gains remain unmeasured.
What Improved: The approved scope separates missing evidence from ambiguous evidence and includes the complete display and persistence path.
What Remains Unsatisfactory: Conservative recovery showed no new accepted intervals on the measured cases; native interaction and real-song ground-truth accuracy are unmeasured.
Next Score-Maintenance Action: Preserve verified assets and original analysis, collect user feedback, and scope any future accuracy work separately without claiming unmeasured gains.

### Score history

- 2026-10-11 23:20:25 Asia/Seoul — 38 provisional: Approved plan and confirmed diagnosis; implementation and release evidence pending.
- 2026-10-12 07:48:00 Asia/Seoul — 43 provisional: Candidate preservation, distinct causes, and evidence-aware unknown segmentation pass the first five regressions; score/path parity also passes.
- 2026-10-14 20:40:44 Asia/Seoul — 47 provisional: Earlier guarded346-test run passed after legacy expectation updates; dense timeline repair passes focused tests and independent re-review. Frozen/actual/versioned gates pending.
- 2026-10-18 16:23:50 Asia/Seoul — 47 provisional retained: Final348 tests,32qualitycases and CQT/FFT real-file checks passed; no demonstrated accuracy gain. Interrupted packaging must finish before delivery.
- 2026-10-18 16:32:22 Asia/Seoul — 48 provisional: Hidden build and complete frozen workflow pass, including uncertainty exports and native ABI2; package inputs match verified source. Publication not yet complete.
- 2026-10-18 23:47:33 Asia/Seoul — 49 provisional: Fresh extraction and public three-asset verification pass; v0.1.05 delivered without altering v0.1.04. No user score or accuracy improvement assumed.

## Progress log

- 2026-10-18 23:47:33 Asia/Seoul — Fresh archive verification passed against clean commit83e88c10f62f6b174b2f95cf0e68b751a14f4db0:5464manifestfiles,101sourceinputs andcoldfrozenuncertainty/nativeworkflow. ZIP349587911bytes SHA256BD6638AD742E71039125F996E62B44054265053EDF04014326CC1000699A52E0. Clean checkout preserved from sourcefreeze through publication. Main/tag pushed; developer prerelease published23:46:38KST; anonymous API readback confirmed all3asset sizes/digests. This postpublication documentation records the external gates without rewriting the frozen tag/archive.

- 2026-10-18 16:32:22 Asia/Seoul — Full build exited0 after frozen diagnostics; CQT/FFT/edit/reopen/uncertainty HTML/PDF, mixer export, font and native parity pass. Seventeen optional dependency/hook warnings disclosed. Helper re-review approved exact clean-commit binding/checksums. QA/docs finalized for source freeze; archive and publication receipts remain external gates. No screen interaction, playback, clean-machine or physical-print testing performed.

- 2026-10-18 16:25:54 Asia/Seoul — Release-helper review identified two proof gaps within the approved release gate: archive-to-tag source binding and checksum-file contents. Added clean-HEAD source_commit to the fresh archive receipt, required that commit to equal the published tag, and checked exact checksum entries against ZIP member/file bytes before draft mutation. Three offline helper regressions ran red for missing checks then green; no runtime source or 348-test receipt changed. Re-review requested before source freeze.

- 2026-10-18 16:23:50 Asia/Seoul — Resumed with source hashes still matching the final348-test and quality receipts. October17 PyInstaller output completed, but no frozen receipt/manifest completion was recorded and no build process remained. Rerunning the existing hidden build from unchanged verified source, preserving its October17 source-reference date and all older releases. Feature commit626fba9 is local; release freeze/tag/publication remain pending.

- 2026-10-11 23:20:25 Asia/Seoul — User approval recorded. Repository is clean at the completed v0.1.04 publication state. The planned coding, test, documentation, and release surfaces are authorized; no production edits have started.
- 2026-10-14 20:40:44 Asia/Seoul — First bounded repair completed: CQT output capped at4096 events with explicit output_limit cause and contiguous time coverage. Greedy budget bookkeeping now uses constant-time adjacency after sorting, with100 randomized differential cases agreeing with full-scan reference. Dense10021-event test first failed then passed. Independent re-review tested24001-observation cases, actual JSON reopen,22focused tests, and found no remaining actionable issue.
- 2026-10-14 20:40:44 Asia/Seoul — Extending existing music_diagnostics and actual-file QA helper within the approved frozen/roundtrip verification scope. New self-test assertion ran red for missing uncertainty_reopen_exports; implementation now checks a deliberately abstained synthetic CQT event through JSON, HTML and PDF. Actual-file helper verifies exact raw uncertainty roundtrip and adds numerical candidate/empty-unknown durations, never source names or chord sequences to public reports.
- 2026-10-12 07:48:00 Asia/Seoul — Resumed after interruption. Contract: unknown primary label stays '?'; optional finite uncertainty_reason in evidence, at most three existing-shape candidates, optional boolean reanalysis_recovered. UI localization may add a shared i18n key within the approved display scope. Parent owns voicing.py/song_chords.py; workers own model/persistence and display/export slices.
- 2026-10-12 07:48:00 Asia/Seoul — Five new classifier tests ran red (two failures and five subcase errors), then green. Existing path two tests and scalar/vectorized score parity two tests pass. Independent baseline found naive 0.3-second noise reanalysis can create a false extended chord; recovery therefore requires primary local candidates and agreement between both alternate lengths, with existing temporal support still required.
- 2026-10-13 21:25:00 Asia/Seoul — Bounded CQT retry implemented after five red tests (six missing-function subcase errors); all five and seven existing CQT song tests pass. Two widths share the existing transform and harmonic region, require an original candidate and observed tones, agree on the primary symbol, and pass stronger energy/confidence gates before existing temporal filtering. No FFT retry is added; FFT evidence retention remains supported.
- 2026-10-13 21:25:00 Asia/Seoul — First guarded suite ran346 tests with92 GUI tests deferred, reporting five failures from two legacy assertions: output-limited evidence formerly required an empty dictionary, and unknown candidates formerly had to be invisible. Both expectations conflict with the explicitly approved change; updated them to require only the reason/no chord claims and candidate visibility only in the detail layer. No production behavior was relaxed to satisfy these tests. Model32 and display34 focused checks pass; KO/EN five-page PDFs were inspected offscreen.
