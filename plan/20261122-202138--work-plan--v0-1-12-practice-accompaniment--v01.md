# Practice accompaniment work plan

Plan Type: Work plan
Workstream: ToneMatchTMP v0.1.12 practice accompaniment
Version: 01
Status: Approved implementation and developer delivery complete
Created: 2026-11-22 20:21:38 Asia/Seoul
Last Updated: 2026-11-23 19:51:27 Asia/Seoul
Related Plan: plan/20261120-202742--work-plan--v0-1-11-update-https-repair--v01.md
Current Completion State: Source, frozen practice workflow and GitHub release verified
Completed So Far: 556 guarded tests, silent packaged data generation, ZIP integrity, live HTTPS and offline cache reuse, verified publication
Remaining Work: Native visual and listening acceptance remain deferred
Current Blockers: None for approved delivery
Next Step: Use the new practice mode from the published developer build

## Approved outcome

Add a separate practice accompaniment mode in ToneMatchTMP. The user approved the workflow proposed after examining six screenshots on November 22. A player supplies the title and optionally a key, prepares a question for an external AI, pastes the returned code chart, previews and edits it by bar, transposes it in semitone steps, and plays a locally generated band arrangement. Support the seven proposed styles (Rock, Pop, Ballad, Funk, Blues Shuffle, Bossa Nova and Jazz Swing), a part mixer, repeating practice, saving and opening the chart/project, and exporting audio. Keep the application’s existing visual language, bilingual text and fonts. The images are product reference material. Use them to understand the feature, without incorporating the actual images, branding, layout, interaction copy, or media into the product or distribution.

The current approved delivery also includes incrementing the version to 0.1.12, tests that do not create a window or play sound, updated developer and user information, a Developer ZIP, ordinary GitHub source and tag pushes, a new GitHub prerelease, and verification of the public bytes. Preserve all historical tags and assets. Use the existing explicit Development mode for the unsigned ZIP. The default build remains SigningInput. Do not proceed with SignPath or Store account enrollment, paid services, unsigned MSIX publication, or undisclosed certificate changes. Keep the recent frozen HTTPS repair and testing in the build and release path.

Native UI launch, screen manipulation, hardware queries for this feature, device playback during testing, installing packages, and use of the user's private Room 335 track or attached images in artifacts remain outside the user’s approved testing. Use fake output for transport tests, and generate PCM and render WAV or MP3 in temporary storage for offline verification. Report exactly what these tests prove, including their limits for actual listening, DPI, naturalness, or accuracy of song transcription. Do not infer original keys or exact charts from song titles.

## Practice chart and prompt

Present a local title and optional key input. Blank key means that the question can request the original key if known, without asserting that ToneMatchTMP has determined it. Provide a preview and copy action for the generated question, and deliberate actions to open ChatGPT or Claude and paste it. Restrict provider actions to fixed provider addresses. A browser opens only when the eventual user selects that action in the product. Keep prompt creation and chart import offline, with no required credential, API billing, network submission or automatic extraction of a private conversation. Request a plain chart of bars, optional section labels, rests and chord symbols without lyrics, sheet music or melody. Treat the title and key as data with bounded length, not instructions to run. Let the player identify suggestions and verify them before use.

Define a compact chart format using one or more physical input lines and pipe boundaries between bars, with optional bracketed section labels. Treat spaces as separators within a bar. In 4/4, default duration is 4 beats for one chord, 2 and 2 for two, 2 then 1 and 1 for three, or one beat each for four. Permit explicit whole-beat durations within a bar for edits and export. Check total duration and reject mixed or malformed durations, empty bars, unexpected prose, invalid chords and unfinished section markers with useful line or bar context. Support a single surrounding Markdown code fence if found in an ordinary pasted answer. Keep silence distinct from an unresolved chord. Recognize only the existing chord parser’s validated chord grammar, including flats, sharps, sus, extensions, and slash bass. If users enter an unresolved symbol, show that it needs correction before rendering. Do not infer a replacement. Limit text, sections, title, number of bars and downstream generated frames to defend against oversized or malformed input.

Keep the practice project separate from audio-analysis results and their evidence, recommendations, and corrections. Use one chart representation as the source of truth after a successful parse. Do not overwrite a working project on invalid paste or file load. Show a scrollable numbered preview with section, chord and beat durations. Make ordinary keyboard edits easy in the chart text or at bar level. Update the effective chart when input validates, and ensure playback and export use the same effective chart the user sees. The semitone controls transpose both the harmonic root and bass, retain chord quality, repeat lengths and rests, and update a known key consistently. Use a sensible sharp or flat naming convention while preserving pitch-class meaning. Apply saved settings atomically on successful load. Use versioned, bounded JSON for the practice project and preserve the input chord text and playback settings through save and reload. Use ordinary save dialogs and explicit user-authorized destinations; malformed collections or nonfinite numbers cannot reach audio generation.

## Generated accompaniment and transport

Use the NumPy and PCM/WAV support already bundled. Synthesize the backing tracks locally with no sample, weight, internet or third-party dataset requirement. Keep seven musically distinct, deterministic rhythmic patterns. Provide drums, bass, harmonic comping and a click, with suitable voicing range and predictable rhythmic subdivisions. Use distinct harmonic comp rhythm, bass rhythm and percussion placement so style changes are audible in principle and observable in synthetic tests. Use a shared absolute sample clock to avoid cumulative rounding drift across charts, and align all tracks and bar positions to it. Keep the implementation simple and handle slash bass, rests, section transitions, last sample boundaries and clipped or nonfinite output defensively. Use bounded memory with bar-by-bar generation, cancellation between bounded chunks, and cleanup in failures. Report the nature of the generated sounds honestly. The mode is for practice accompaniment rather than automatic transcription or a reproduction of the recording.

Reuse the existing WavPlayer output worker and transport where practical. Keep rendering, playback and exports off the Tk event loop. A single owner manages each temporary arrangement and releases it only after the output and any readers have closed. Play is an explicit user command, including after paste or load. Include stop, current bar, loop, BPM and a simple count-in. Preserve the count-in on first start when looping and skip it on each musical wrap. Ensure stopping, seeking, replaying after EOF and restarting count-in are predictable at frame boundaries. Keep no output stream open before user play. Bound polling, use the main thread for widget updates, and invalidate stale asynchronous work when closing or changing the chart. Reuse audio availability and suspension checks so this window does not compete with capture, reference monitoring, stem playback or ordinary playback. Existing save and playback behavior is a regression concern and must be guarded.

Show the four levels alongside the seven styles, with master level, mute and solo where natural, and update playback from a consistent immutable mix snapshot. Stop or cancel the current render if controls that change generated content need a new render. Mixer changes should not require re-synthesizing sound. Use conservative output headroom and convert using a bounded common path for playback and export. Support saving and opening the project when offline. Export the current mix as WAV and MP3 through the existing trusted bundled FFmpeg path, and allow individual part WAV files using the same aligned render. Treat count-in behavior for export explicitly, since exporting a song normally omits pre-roll. Keep temporary output from replacing an existing destination on failure or cancellation. Exercise WAV and MP3 data generation without sending it to any playback device. Keep generated fixtures, project data and results out of the public archive unless they are minimal synthetic source fixtures already reviewed under repository policy.

## Integration and verification

Use a distinct ToneMatchTMP-styled practice window or panel reached from the main app. Use Malgun Gothic for Korean and Arial Narrow for English, current palette, shortcuts and layout conventions. Keep entry points visible and use error and progress messages only where the user needs to understand the state or recover. Maintain a single model for practice data, a deterministic render boundary, the existing playback worker, and a small UI integration. Do not expand into real-time AI, sample import or a general DAW. Carry app version and dependencies through the spec, source lists, function index and build documentation. Preserve existing updater, existing analysis frontends, chord findings, export behavior, private data, and signing policy.

Write specific behavioral tests for input bounds, parse diagnostics, section and beat preservation, chord-bass transposition and round trips, project save and readback, and invalid loads that leave prior state intact. Test distinct arrangement output, frame alignment at fractional tempos, resulting frequency and note evidence where practical, silence and mute/solo behavior, finite amplitude and headroom, cancellation cleanup, and audio export shape without real output devices. Exercise count-in, repeating, pause, stop and the shared audio arbitration without a real window. Build guarded Tk tests around inert collaborators where necessary to validate lifecycle without mimicking Tk. Keep existing checks for playback and store behavior. Run the existing guarded suite and capture hash-bound test receipts. Test application-generated audio as data only and record native visual or listening acceptance as deferred.

Ask for a narrow independent review of the whole change, with attention to input validation, data provenance, async ownership, playback or capture overlap, resource lifetime, bounded audio rendering and exact build wiring. Correct concrete issues within the approved scope and rerun affected tests. Verify source references and code are present in both the public developer sources and the packaged debug source paths. Add a silent frozen diagnostic for the new feature to the existing self-test. Use a small synthetic progression, transpose it and render and read the generated PCM without opening a device. Update the build acceptance and archive validation so a missing frozen module or broken render fails the distribution check.

## Release and record

Update the new QA snapshot, README in Korean and English, developer handoff, function reference and build history. Distinguish test fixtures from actual listening and song measurements. Build the explicit unsigned Development ZIP from the accepted source, run hidden offline and online HTTPS diagnostics, and verify the complete manifest, checksums, runtime resource, native parity, source inputs, temporary files and absence of private content. Verify update installation of the new exact archive from the preceding version and offline reuse in an isolated cache. Publish one new v0.1.12 tag and GitHub prerelease with its ZIP, SHA-256 list and archive verification report. Use existing credential tooling without displaying secrets. Re-download all public assets and compare actual bytes and hashes before reporting completion. Preserve prior release metadata and tag references. Keep records under the project and update this plan and the project checkpoint as verified facts change. Record the signed/Store distinction factually and maintain enrollment as a user-deferred step.

## Scoreboard

Current score: 49/100
Score source: provisional
Last updated: 2026-11-23 19:51:27 Asia/Seoul
Rationale: The approved workflow is implemented and the published package was checked against actual public bytes.
What improved: Chart validation, transport boundaries and PCM/audio exports are exercised in guarded source and frozen diagnostics.
What remains unsatisfactory: Native layout, listening and actual-song accuracy have not been measured.
Next score-maintenance action: Preserve immutable release evidence and accept later authorized feedback.

Score history:

- 2026-11-22 20:21:38 Asia/Seoul — 34 provisional: Approved plan persisted with concrete offline and public release requirements.

- 2026-11-23 19:37:21 Asia/Seoul — 44 provisional: guarded source tests passed and independent review complete.

- 2026-11-23 19:51:27 Asia/Seoul — 49 provisional: published package and download readback passed. Native and listening acceptance remain deferred.

## Progress log

- 2026-11-22 20:21:38 Asia/Seoul — User explicitly approved v0.1.12 practice accompaniment, testing without window or audio playback, a developer ZIP and GitHub release.
- 2026-11-23 19:37:21 Asia/Seoul — Implemented chart parsing, offline prompt handoff, seven arrangements, playback/mix, persisted projects and audio exports. Independent review covered input bounds and child/worker lifecycle. All 556 guarded tests passed in 96.41 seconds. The remaining work is packaged and public verification.
- 2026-11-23 19:51:27 Asia/Seoul — Published v0.1.12, verified actual GitHub bytes and preserved previous tags/releases. 357,408,597 bytes, 5,510 manifest files.
