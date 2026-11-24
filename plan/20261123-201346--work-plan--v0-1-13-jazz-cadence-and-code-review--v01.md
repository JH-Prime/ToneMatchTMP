# Practice cadences and source review

Plan Type: Work plan
Workstream: ToneMatchTMP practice accompaniment and application stability
Version: v01 for v0.1.13
Status: Approved implementation and developer delivery complete
Created: 2026-11-23 20:13:46 Asia/Seoul
Last Updated: 2026-11-24 20:00:05 Asia/Seoul
Related Plan: The completed v0.1.12 accompaniment delivery
Current Completion State: Source, frozen cadence workflow and GitHub release verified.
Completed So Far: 574 guarded tests, package integrity, live HTTPS, cache repair and verified publication.
Remaining Work: Native visual and listening acceptance remain deferred.
Current Blockers: None for the approved delivery.
Next Step: The developer release is ready for download.

## Objective and assumptions

Give a musician a direct way to rehearse a jazz two–five–one cadence using the existing practice accompaniment mode. The current project already accepts editable chord charts, arranges them in seven styles, mixes parts and exports them locally. A learner should be able to choose a tonic and tonal mode without transcribing every chord, leave the exercise in one key for repeated practice or follow a circle through all twelve tonal centers. The generated chart should remain intelligible and editable before the user starts playing. Treat the request as a project-wide stability review as well. Start from the presently shipped first-party sources and tests, including the native layer and release tooling. Historical QA snapshots and third-party libraries supply context. An inventory of the current code and a record of actual proof are more useful to a maintainer than a count of old commit snapshots.

Use a four-bar phrase in common time, with one bar each of the second and fifth degree and two bars on the tonic. Allow the user to change that rhythm in the same editor used for other charts. Use a minor seventh, dominant seventh and major seventh in major keys. In minor keys use a half-diminished seventh, dominant seventh and minor tonic chord, with the tonic seventh choice documented. For example the C major exercise should display Dm7, G7 and Cmaj7. The C minor exercise should show Dm7b5, G7 and Cm7. The user approved a single-key option and a twelve-key option moving by ascending perfect fourths. A twelve-key run should start at the selected tonic, contain twelve different tonal centers, and loop back to the first key using the existing loop control if enabled. A single phrase should behave like a normal chart with loop disabled or enabled according to the current controls. Use ordinary spellings a jazz musician is likely to read, including flats, and test the result against actual pitch classes rather than trusting text alone.

## Preserve existing musical and editing behavior

Keep a single source of truth for playback, export, transposition and visual preview. Reuse normal project bars and a section label when it helps the learner see a new key. Preserve the current style, tempo, count-in and mix when generating a progression unless a fact about the existing editor requires an explicit change. The tonic and tonal mode should be explicit near the cadence action. Applying the exercise must be deliberate and protect an existing edited chart from accidental loss. Keep the default prompt and chart import workflows usable. Projects saved by the preceding release should load with their original content. A new cadence that can be represented as ordinary bars should require no special storage, synthesis model or additional module dependency merely to reopen it.

Exercise root and bass recognition, seventh qualities and half-diminished spelling through the same parser and renderer as hand-written charts. Include both a common key and difficult accidentals in verification. In a full cycle ensure the first key and the last-to-first transition are both musically correct. Keep generated chart length within the existing bar limit, use bounded memory when rendering and preserve cancellation behavior. Reuse the established rendering path for each instrument so solo, mute, count-in, start-of-loop alignment and file output remain consistent. Keyboard and mouse entry points should use the project's normal widget conventions, Korean and English language choices and established font families. Treat exact native visual fit and audio timbre as deferred user acceptance.

## Review the existing application from input to delivery

Use the Git tracked inventory to identify which parts are application code, build and QA support, first-party native code, UI presentation, tests and fixtures. Review how analysis starts from a file, separates instruments when requested, estimates harmony from the full mix, preserves evidence and presents uncertain results. Follow manual corrections into copied content, exports and reopened projects. Examine chart navigation, playback ownership and device availability after a task completes, fails or is cancelled. Inspect the reference and catalog displays, diagnostics, persistence and shutdown, especially where stored JSON or results from workers cross a boundary. For passive data catalogs, check that data satisfies the expectations of its readers. Classify test files by the behavior they support and make any unexamined scenarios explicit in the audit.

Follow ownership across background threads, temporary files, audio callbacks and queued UI events. Pay particular attention to cases where one component finishes work after another has changed or released its state. Inspect validation for finite numeric input, supported ranges, old documents and failed storage operations. Consider whether a malformed but ordinary input prevents the main app from starting or leaves the last valid project unusable. Review first-party native entry points alongside their Python callers and existing parity tests. Use representative synthetic data or fakes for experiments. Where feasible preserve the observed failure as an automated regression. Weight user consequences and confidence more highly than style preferences or the size of a source file.

Inspect the packaging, updater, licensing inventory, portable runtime and Store preparation alongside their existing tests. A shortcoming in a test or release check deserves a clear distinction from a fault in the shipped app. Keep current distribution safeguards and existing releases intact. Review security-related code defensively. Do not develop exploit demonstrations. Use no paid signing, service account setup or external identity steps. Do not import user music or screenshots into test fixtures. If a finding cannot be measured without hardware, UI interaction or an actual annotated song, explain precisely what remains to be checked. A successful synthetic test must not be presented as measured accuracy on a recording.

## Sequence and evidence

First establish the provenance of the baseline. Use the live repository and actual release list to determine which published version can be updated, whether the candidate tag is available and what prior releases must be preserved. Record the version and relevant revision together with coverage boundaries. Collect candidate problems by following source code and normal caller paths. Check credible candidates independently using small deterministic inputs, fake dependencies or explicit invariants. In the review record, identify the source location, trigger, impact, test or other evidence, resolution and remaining limitations. Prioritize data loss, start-up failure, wrong musical behavior and broken user controls. Avoid unrelated sweeping refactors. Where a fix is justified, choose the narrowest reliable change that covers the whole affected path.

Implement the musical feature and the confirmed repairs as independently verifiable changes. Confirm that the cadence controls create a complete chart and that the normal project and playback interfaces consume that chart. Test cancellation of a chart replacement, invalid input and saving/reopening a generated progression. Check whether the original implementation normalizes spelling and choose a compatible way to retain musical meaning. If the existing UI assumes one global key, present the selected first key and use section labels for subsequent tonal centers so the visible chart and saved timeline remain coherent. Ensure public documentation explains those conventions in concrete terms a player can use. Keep the test evidence for musical correctness separate from experiential claims about playing or listening.

Use the project’s guarded test entry point to run the complete eligible headless suite. Build test fakes where that permits coverage of application logic without opening a native window. Add focused regressions for the specific confirmed issues, real method calls and persistent project round trips. Generate short synthetic PCM and inspect frame counts or musical activity without acquiring a device. Test the exported or frozen paths with diagnostics when the feature relies on packaged components. Document the actual number of cases executed, skipped or deferred and the exact package under test. An automated build log cannot establish that the native layout looks right. Avoid running GUI suites or programs whose normal entry point opens a window.

## Release and rollback

Increase application and Windows version metadata consistently and record the change in the relevant user and developer documents. Generate the function inventory with the established tool. Produce a distinct unsigned development package for this patch and maintain the agreed no-cost signing and Store policy for later enrollment. Do not publish an archive if the source tests or frozen diagnostics fail. Validate files included in the final ZIP, archive structure, checksums, embedded sources and key TLS policy resources. Check installation from the preceding version in an isolated cache using the exact archive. Check offline cache reuse separately. Keep private and generated audio strictly out of the package. Compare the public ZIP and supporting files against the actual verified local byte streams after publication. Preserve a receipt that allows the next maintainer to repeat the comparison.

Use a fresh version tag and a new public prerelease. Keep already published tags and bytes unchanged. Record separate commits for release source and any later publication receipts as appropriate. If a failure appears before publication, repair and rebuild the affected candidate using the existing project procedures. If another publisher takes the tag, stop before replacing it and report the conflict. If a fault emerges after a release is public, preserve it and identify the need for a subsequent patch. A complete delivery includes the verified feature, concrete audit findings, passing authorized tests, verified downloadable assets and an accurate statement of any remaining acceptance work.

## Scoreboard

Current score: 49/100 provisional.
Last updated: 2026-11-24 20:00:05 Asia/Seoul
Rationale: Source and package checks passed and public delivery is verified.
What improved: The packaged practice workflow and update cache are covered by regression checks.
What remains unsatisfactory: Native layout, listening and actual-song accuracy remain unmeasured.
Next action: Preserve the immutable developer release and evidence.
Score history:
- 2026-11-23 20:13:46 Asia/Seoul — 32 provisional, approved scope recorded and reviews begun.
- 2026-11-24 19:42:39 Asia/Seoul — 44 provisional, reviewed changes passed 574 guarded tests.

- 2026-11-24 20:00:05 Asia/Seoul — 49 provisional, verified the actual public assets.

## Progress log

- 2026-11-24 19:42:39 Asia/Seoul — Source implementation and audit complete. Passed 574 guarded checks.

- 2026-11-24 20:00:05 Asia/Seoul — Published v0.1.13 and verified all public downloads. 357,432,185 bytes, 5,510 manifest files.
