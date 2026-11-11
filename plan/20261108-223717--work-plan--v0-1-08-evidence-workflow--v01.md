# v0.1.08: Preserve uncertain evidence and repair existing workflows

Plan Type: Work plan
Workstream: ToneMatchTMP v0.1.08
Version: 01
Status: Source and frozen build accepted; preparing immutable archive
Created: 2026-11-08 22:37:17 Asia/Seoul
Last Updated: 2026-11-11 21:33:32 Asia/Seoul
Related Plan: plan/20261102-231452--revision-plan--v0-1-07-cqt-auto-update--v02.md (completed historical release; preserved)
Current Completion State: Source, frozen diagnostics, source/native/version/privacy checks and release review accepted
Completed So Far: Four corrections and recorder race repair;456headless;62/31/32/11 comparisons; localCQT/FFT; helper10tests; independent reviews; frozen build and115source inputs verified
Remaining Work: Freeze clean commit, exclusive developer ZIP, fresh archive/updater verification, publication and readback
Current Blockers: None
Next Step: Commit final accepted source/docs/QA, create archive exclusively and verify it without further source changes

## Authority and objective

The user asked to resume the existing project, compare its handoff documents with actual source and GitHub release state, prioritize reproducible correctness and stability problems, and deliver each accepted patch through versioning, tests, documentation, developer ZIP, Git push, release publication and asset verification. A read-only investigation produced four specific findings. The parent presented these four items together and explicitly asked whether to proceed through release. The user's subsequent instruction, "이어서 해줘", approves continuation of this concrete scope. Do not ask for the same implementation or publication authorization again. The ban on screen manipulation, window launch and audio playback remains active throughout this work.

Deliver a small maintenance patch that preserves the truth of observed musical evidence and repairs existing navigation, recording completion and saved-result workflows. Keep analysis based on the entire source mix, preserve both CQT and the existing FFT option, and retain slash chords, suspended and extended harmonies, explicit unknown results, alternatives, manual corrections, playback synchronization, stem mixing and individual exports, and sixteen-bar PDF charts. This is not a new transcription model or a claim of measured actual-song accuracy. No C++ transition, dependency addition, tuning threshold change or new device/effect browser is justified by the findings.

Use the active ToneMatchTMP repository supplied by the user. Read the global AGENTS.md before substantial work on each turn. No project or ancestor AGENTS.md was present during discovery. Use the parent-session checkpoint as the durable current status. The parent retains integration and acceptance responsibility; narrowly assigned workers may operate on disjoint files under the runtime's shared-workspace rules. Keep logs and intermediate artifacts in work, and run records in this repository's parent-session-runs directory. Avoid dumping full historical documents into chat or repeating entire audit contexts.

## Accepted baseline and immutable history

Local main and remote main both initially identify 4ae311590cc61e272556d9bb9b928bf82391cae1. The working tree was clean. The public v0.1.07 tag resolves to e8142f80151d5d92b05bc6c3e5c091934e63a093, and the corresponding developer prerelease is published. Public API asset sizes and SHA-256 digests agree with all three local delivery artifacts. Its ZIP is 349720420 bytes with digest c66397312135437b0073448e21771318c1dc40fc1edd262b25b924d5b3b2a69e. There is no public v0.1.08 tag or release at discovery. Preserve every existing tag and asset. Do not rebuild or replace v0.1.07.

The guarded baseline suite passed all 433 selected tests in 83.017 seconds, with zero failures, errors or skips among selected tests. Ninety-two GUI-containing tests were deliberately deferred. The project environment is Python 3.12.14 with recursion limit 1000. The observed application recursion includes JSON depth validation capped at 24 and bounded helpers; the baseline has no RecursionError. Keep the limit unchanged. These facts establish source operation, not a new clean-machine, audible, graphical or musical ground-truth result.

Treat older sections in the handoff and build history as historical. In particular, earlier guitar-stem-first analysis and guitar-shape display contracts do not override the current whole-mixture chord-name workflow. The previously completed plan remains a completed release record; this plan is a successor workstream, not a rewrite of that immutable release. Append new build-history entries and preserve earlier hashes, dates and qualification language.

## Preserve time-local uncertain evidence

The shared event merger currently groups unknown observations by their primary unknown label, reason and candidate symbols, omitting the observed pitch classes. Since unknown observations have zero confidence, selecting the maximum-confidence representative retains the first observation. Synthetic two-second C followed by two-second D is therefore displayed as one four-second unknown event whose evidence contains only C. Both frontends reproduce the loss. This is an evidence-presentation error even though the primary question mark correctly avoids asserting a chord.

Keep distinct observed pitch-class sets separate when merging unknown observations, using the existing event model rather than inventing a second timeline or adding new stored schema fields. Normalize order and duplicates for identity so equivalent sets continue to merge. Preserve existing behavior for known chords, uncertainty reasons, alternatives and confidence semantics. Do not union notes across changing time regions: that would suggest simultaneous evidence that was never observed. Do not promote a single note to a chord, fill unknown spans from neighbors, or alter FFT peak extraction and CQT harmonic rejection.

First add a failing regression for the original merge failure and a controlled PCM case that exercises both frontends. Protect identical evidence merging, different evidence separation, continuous event coverage and the existing event budget. Check that JSON reopening, manual edits and restoration, HTML and PDF carry the retained evidence. If increased event diversity reaches the established output limit, retain the existing explicit output-limit handling instead of silently dropping timeline coverage or raising the limit. Any comparison failure must be explained by observable behavior and fixed within this evidence-preservation contract; never weaken accepted musical correctness gates to make a release pass.

## Repair navigation and recording completion

The chart's left/right action currently treats displayed bar number minus one as its list position. This fails for a pickup bar numbered zero and for a negative first-downbeat offset whose first visible bar is numbered above one. Navigate through the actual ordered chart bars. Preserve source-relative seeking, page switching, current selection, loop behavior and endpoint clamping. Test positive, zero and negative first-downbeat settings, movement in both directions, page crossings and stale or missing selection as appropriate to existing behavior. Use headless view doubles around the real handler, never an actual Tk root or playback output.

The recording worker publishes a terminal event immediately before its thread returns. Unlike the analysis terminal handler, recording completion and failure do not retire the worker reference before checking availability. If the UI processes the event during that interval, device, analysis and language controls are set back to disabled and later empty queue polls do not recover them. Retire the completed recording job at the terminal-event boundary, then reuse existing availability logic. Keep controls locked when another legitimate operation remains active. Preserve the recorded file, status and error reporting; do not add polling timers, broad state frameworks or blocking thread joins.

Add regressions that hold the fake recording thread alive when success or failure is consumed, then mark it stopped and process an empty poll. Verify usable controls immediately at completion and afterward. Preserve cancellation/stop behavior and genuine other-operation locks. Existing analysis completion, failure and cancellation tests must remain green. The worker is terminal when it emits its final event; no ongoing useful recording is abandoned by clearing that completed job reference.

## Reject incomplete result data before replacement

A saved known-chord event without a symbol currently passes loading because validation supplies a temporary default, while the actual result remains unchanged. Rendering later requires the missing field and raises KeyError after the result has begun replacing current state. Require the display symbol at the input boundary for events that the application accepts. Apply the smallest validation consistent with existing generated and historical valid results; do not invent a new serialization version or silently infer a chord name from other fields.

Add a failing test that deletes the symbol from a legitimate saved fixture and proves rejection before UI rendering. Cover unknown and known events, existing manually corrected results and valid legacy fixtures according to their actual schema. Preserve input byte/depth limits, finite numbers, source sanitization and the rule that reopening never trusts a local media path or starts playback. Avoid broad unrelated validation refactors. Precise existing ValueError behavior is preferable to allowing a later GUI exception. Keep original user files and existing saved results unchanged on disk.

## Verification and allowed repair boundaries

Use the project's existing virtual environment and unittest conventions. Record failing regression evidence before production edits, then run narrow tests for each correction. The permitted implementation surface includes the shared event merger and its direct evidence tests, chart and recording handlers and headless controller tests, saved-result validation and its tests, frozen music diagnostics when needed to exercise the repaired contracts, and directly affected verification tooling. The parent owns version declarations, QA receipts, documentation and release materials. Keep workers away from shared version and plan files to avoid conflicts.

Run the full guarded headless suite against the integrated final source with warnings treated as errors and Tk creation blocked. Preserve the deferred GUI list. Run the existing synthetic precision, harmonic, uncertainty and trace comparisons against immutable v0.1.07, retaining per-case checks and source hashes. Where earlier tools expect a different prior version, adapt their invocation or explicitly scoped verification glue without weakening their acceptance criteria. Known label time, incorrect label time, evidence time and detection coverage have different meanings and must be reported separately.

Use the Room 335 MP3 only for local, silent verification of existing operational paths if useful. It may test decode, both analysis methods, progress, cancellation, edits, reopening and export, but it has no independent ground-truth chord annotations. Never call its detection coverage accuracy. Never copy it into tracked files, upload it, or include it in a ZIP. Tests must not open audio output devices, create Tk windows, print, drive the desktop or invoke an ordinary application startup. Hidden frozen diagnostics are allowed only through their existing explicit no-window, no-playback diagnostic command path and must be awaited to completion.

Review changed source for correctness, predictable state transitions, malformed data handling, concurrency, bounded output and rollback. Fix direct regressions discovered in the approved surfaces and re-run the relevant checks. Prefer one bounded repair cycle and make its cause and evidence explicit. Do not expand the patch into new inference heuristics or updater recovery. The observed damaged-update-cache redownload loop is a separate follow-up finding; the present updater safely rejects corrupted cached runtimes and falls back. Document it without modifying the updater trust or installation transaction in this patch.

## Packaging, publication and completion

Advance all active application and build markers to 0.1.08 while preserving historical version records. Update Korean and English user-facing notes and developer handoff to describe concrete repaired behavior and remaining limits. Refresh the function reference only if its generated structure changes. Record test receipts and source hashes in the same way as accepted previous releases. Keep Korean Malgun Gothic and English Arial Narrow requests unchanged; static configuration review is not visual font verification. Preserve the licensed PDF font and sixteen-bar layout.

Build only after source verification passes. The existing build defaults include GUI test discovery and can delete an existing same-version ZIP, so use the already reviewed SkipTests and SkipZip path against the new version. Keep the previous release tree intact. Package using exclusive creation and a clean frozen source commit. Verify developer-source completeness, executable and embedded version consistency, manifests, native ABI parity, font/license inclusion and absence of private media, model weights, secrets, absolute private paths and development JIT caches. Preserve known optional packaging warnings honestly rather than claiming a warning-free build.

Extract the exact candidate archive into a fresh, suitably short isolated path. Verify every manifest entry and source receipt, then run its hidden diagnostics. Exercise installation of the exact ZIP through the unchanged production updater, and verify offline cached reuse after its CQT diagnostic. Keep external archive verification outside the ZIP to avoid a circular hash claim. Do not publish an archive that failed any required gate. Bind the tag and release to the verified source commit, push without force and create a new prerelease with the ZIP, SHA256SUMS and archive-verification assets. Never replace or delete an existing asset or tag if the remote version unexpectedly already exists; compare and report the conflict instead.

Read the published release back through the public API and validate each asset size and SHA-256 against the local verified artifact, including an unauthenticated public check. Prefer downloading and hashing the actual published files when practical. Record final publication evidence in the parent checkpoint and a subsequent documentation-only commit if needed, leaving the release tag and source artifact immutable. The task is complete only when the four corrections and their required checks pass, the developer ZIP is independently verified, Git and release publication succeed, and public readback matches. Report the release link and concise verification facts, with synthetic versus real-song and headless versus UI limitations clearly separated.

## Scoreboard

Current score: 48/100
Score source: provisional
Last updated: 2026-11-10 22:53:08 Asia/Seoul
Rationale: Integrated checks and independent review now pass; frozen build and public delivery remain unfinished.
What improved: The broad request is now four bounded maintenance corrections with observable acceptance checks.
What remains unsatisfactory: Public delivery remains incomplete; actual UI and actual-song ground truth remain unverified.
Next score-maintenance action: Complete immutable archive verification and public delivery without changing accepted runtime source.

Score history:
- 2026-11-08 22:37:17 Asia/Seoul — 40 provisional: approved bounded scope, baseline and publication audit complete; implementation pending.
- 2026-11-09 21:35:31 Asia/Seoul — 46 provisional: four corrections and focused verification complete; resuming after worker service interruption, no publish yet.
- 2026-11-10 22:53:08 Asia/Seoul — 48 provisional:456headless, four synthetic corpora and local workflows passed; stale recorder race independently re-reviewed and accepted; delivery pending.

## Progress log

- 2026-11-08 22:37:17 Asia/Seoul — Plan approved by the user's continuation after the four-item scope question; beginning regression-first implementation.
- JSON regressions reproduce13failures across missing/blank known/unknown symbols and preserved-current-state behavior; minimal boundary correction now requires a nonblank stored symbol. Evidence and state workers own disjoint files; release helper preparation is confined to work/.
- 2026-11-09 21:35:31 Asia/Seoul — Resumed by user. Evidence6 and existing24, controller16, JSON9 and expanded music diagnostic1 pass. State red21subtests and evidence red6 preserved. Version set0.1.08; source date2026-11-09. Updater helper worker was interrupted by service quota; partial files retained and resumed. Independent source/controller reviews are read-only. No published v0.1.08 tag exists; remote main remains4ae3115.
- First bounded review repair opened: prevent a finished recording with a pending terminal event from being replaced by a new job before that event drains; otherwise the old event clears the new worker. Scope remains existing recording lifecycle and headless controller tests. Evidence/JSON/music independent review found no blocker. Integrated final receipts wait for this correction.
- 2026-11-10 22:53:08 Asia/Seoul — User resumed. Final456tests pass77.003s, GUI92deferred, hashes current. Precision62/harmonic31 retain prior correct/incorrect durations; uncertainty32/trace11 pass v107. Room335 CQT/FFT operational checks pass without playback; no real-song accuracy. Bounded recorder repair and independent re-review accepted. Release-helper8tests pass; separate build/v108-prezip output avoids build checksum colliding with exclusive finalizer. QA source accepted; frozen/archive/publication still pending. All previous tags remain untouched.
- 2026-11-10 22:59:29 Asia/Seoul — Six user/developer documents and generated function reference updated. C++ ABI2 parity passed; PyInstaller build running with hidden diagnostic path only. Release review found that unexpected extra draft assets could publish before later readback rejected them; helper now enforces exact names/count/uploaded state/digests before publication. Ten inert helper tests and final read-only review pass. This gate correction changes no runtime source or existing artifact.
- 2026-11-11 21:33:32 Asia/Seoul — Build finished2026-11-10 23:05KST with all hidden diagnostics passed, including uncertain-note changes and invalid-symbol rejection. Reviewed17known optional/deprecation warnings. Final456source hashes still match. Staged115source inputs, PE version, native ABI and privacy checks pass. QA source/frozen status passed; archive/publication remain external gates. Preparing clean immutable source commit and exclusive archive.
