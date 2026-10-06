# ToneMatch TMP v0.1.01 — Song chords and music workflow

Plan Type: revision-plan
Workstream: Full-song chord analysis, playback, corrections, stem mixer, and printable sixteen-bar charts
Version: 02
Status: Delivered as verified developer prerelease v0.1.01
Created: 2026-10-05 10:15:00 KST (Asia/Seoul)
Last Updated: 2026-10-07 01:30:55 KST (Asia/Seoul)
Supersedes: plan/20261005-093310--work-plan--v0-1-01-music-workflow--v01.md
Current Completion State: All approved feature slices implemented; 358 tests, PDF render review, actual cached CPU processing/cancellation, frozen self-test and cold fresh ZIP verification passed. Source and tag pushed; three GitHub release assets published and digest-verified.
Completed So Far: Full-mixture CQT, symbol/evidence/candidate UI, playback/chart linkage, correction/undo/reopen, six-stem mixer/WAV, PDF/viewer print flow, packaging and developer prerelease.
Remaining Work: None for this delivery. Musical correctness/listening and clean-machine/hardware launch gates remain explicit limitations, not claimed successes.
Current Blockers: None for delivered prerelease; independent annotations, listening, physical printer, first-download/offline, CUDA and signing evidence are still unavailable.
Next Step: User validation; scope reported defects as 0.1.02 rather than replacing 0.1.01.

## Approval and user intent

The user approved the original four-feature v0.1.01 direction with “그렇게 해요”. They subsequently reported that chord accuracy was poor and clarified that they want a song-level chord detector, not an estimate of guitar fingering or a chord inferred chiefly from a separated guitar part. The understanding report proposed full-original-mixture chord analysis while retaining guitar-specific tone analysis and the separately requested instrument mixer. The user further specified that the chord itself should be prominent, with supporting reasons and other candidate chords underneath, and that chord fingering or separated audio should not be shown in this view. Fractional or slash chords, sus4 and other extended qualities remain valuable. They then explicitly approved that clarified direction with “응 그렇게 해”.

Treat this version as the authoritative scope. Supersede the previous plan's guitar-first chord analysis, automatic guitar diagram output, and blanket suppression of slash chords in full-mixture results. Do not interpret the clarification as removing the independent tone-matching workflow or the requested instrument mixer. The user accepted the stated assumption that those separate workspaces remain. Keep separation controls and separated-audio playback out of the chord view. If a later request changes that boundary, reopen only the genuinely changed scope.

The product objective is a readable, editable chord progression for the whole recording, synchronized to the original audio. Chord identities are shared harmonic descriptions and should not be labelled as guitar, keyboard or bass-specific chord detections. Recognizing a bass note and a chord identity are related but distinct tasks. A bass note can support a slash chord when there is evidence; it does not make a symbol a statement of exact instrument fingering. Preserve ambiguity between acoustically equivalent or incomplete voicings rather than asserting a unique answer.

## Baseline and current work

Start from the preserved working directory based on released v0.0.13, commit 874aeb1. The working tree already contains the approved playback service, a compact transport bar, bar selection and following, source-range management, and correction modules and tests. Do not discard these changes or restart the work. No v0.1.01 release or tag exists from this work yet. All measurements from the old release remain historical and are not evidence for the new build.

Playback uses local FFmpeg decoding into a managed PCM file, a single output worker, frame-based position, explicit user play, bounded buffers, and cancellation generations. Sounddevice 0.5.6 has been installed and pinned for PortAudio output; existing SoundCard capture remains. Eighteen initial focused tests passed, then compact-window and optional-view regressions were repaired. The later full checkpoint passed 336 tests. That run emitted stale Tcl callback diagnostics from old developer test fixtures that create application timers and directly destroy the root. A test-only timer cleanup was added and its focused regression passes; final suite verification must confirm clean teardown.

The correction model stores a separate map instead of overwriting original events. Five model tests pass, covering supported symbols, source immutability, manual confidence handling, unknowns, continuation events and bounded JSON reopen. UI editing, undo, language persistence and reopen are partly implemented. The latest focused run passed seven tests and failed an HTML-export test because its synthetic fixture lacks report metadata. Reopened results also need valid metadata defaults before report export. Repair this narrow integration gap and verify a complete reopen-to-export workflow. Do not conceal an integration failure with an inaccurate completion claim.

## First phase: separate song harmony from tone extraction

Read the existing analysis pipeline and make the source of each result explicit. Preserve guitar-isolation and guitar tone features for the tone recipe. Feed the original selected audio range to chord analysis regardless of whether tone matching uses an isolated guitar part, a full mix, or automatic separation. Never decide whether to analyze the mix based on whether guitar-only coverage appears high enough. A strong guitar line can still omit keyboard harmony, and a quiet guitar stem should not prevent song-level chords from being analyzed.

Avoid unnecessary duplicate decoding when an already decoded original range is available within its managed lifetime. Preserve source timing and sample rate. A tone or separation setting must not silently change which notes form the chord input. Decoding or harmony failure must be represented honestly: an unavailable or uncertain chord analysis is preferable to silently substituting a guitar-only answer labelled as full-song harmony. Cancellation must propagate through preparation and analysis, and long-running operations must keep the main UI responsive.

Inspect primary research or official implementations before choosing an algorithmic improvement. Assess the current harmonic peak and template method in the context of a complete mix, including percussion, melody, bass and overlapping instrument spectra. Consider harmonic/percussive discrimination, multi-resolution chroma or pitch evidence, bass-specific evidence, and temporal consistency only where they improve a measured failure. Do not add a collection of unvalidated heuristics just to make the code larger. Keep the smallest complete design that has useful observable evidence.

Do not equate a higher number of accepted chords with greater accuracy. Define tests that cover both correct acceptance and correct rejection. Preserve short genuine changes where the evidence supports them. Do not force every event into the most likely key, or automatically simplify all rich chords into major/minor. When a seventh, extension, suspension or altered tone is missing, distinguish between an incomplete performance, a competing chord interpretation, and insufficient evidence. Present candidates instead of inventing absent notes.

## Second phase: symbol-first chord display

Rename and present the result as song chords or a chord progression, not instrument voicing. Retain a sixteen-bar chart with four bars per row where possible. The leading content in each bar should be chord symbols and their timing or beat position, including slash chords, sus2/sus4, sixths, sevenths, ninths and supported extensions. Remove automatic guitar diagrams and fret-string lists from the analysis result, detail view, HTML and future PDF. A separate theoretical chord dictionary may still explain instruments, because it is not claiming how the recording was played.

Place reasons and candidate alternatives below the primary progression or in a clearly labelled lower detail area associated with the selected event. The user should not need to navigate an instrument-analysis panel to understand a chord. Show the actual evidence the algorithm computes: observed pitch classes, chord template requirements, lower-register or bass support when available, temporal support, and competing symbols. Do not show a generic confidence percentage as a calibrated probability if it is only an internal evidence score. Distinguish a manual correction from machine evidence.

Keep the chart readable at the existing 960 by 600 minimum and at 120 and 150 percent display scaling. Playback controls and a detail area must not make the chart disappear or push controls outside the window. Use the existing compact and collapsible controls rather than increasing the minimum window size without permission. Provide keyboard selection and access to the evidence. Do not rely on color alone: selected or edited items need explicit labels, borders or markers. Keep Korean and English behavior equivalent.

Preserve source-relative and original-file time. The chart grid remains a manually adjustable constant tempo/meter/downbeat display, not a promise of automatic bar transcription. A chord crossing a bar boundary must refer to the same editable event. Unknown portions remain visible rather than disappearing. Keep all symbols and evidence when changing pages, tempo settings, language or exports.

## Third phase: finish editing and persistence

Allow the user to edit a selected event's symbol, choose a supported quality, mark it unknown, restore the original estimate, and undo recent changes. Preserve original event evidence and keep manual corrections separate. A new manually chosen symbol must not inherit the previous machine confidence or old acoustic explanation as if it supports the edit. Instead, retain access to the original estimate and label the edited symbol unambiguously. With automatic result fingering removed, corrections do not need to generate theoretical guitar diagrams.

Keep corrections across page navigation, chart settings and language changes. Save them in the existing analysis JSON and use the same effective result for chart, detail, HTML and PDF. Reopen local saved results through a bounded validated JSON boundary. Reject malformed structures, out-of-range indices, oversized collections, deeply nested input, non-finite times and unsupported symbols before replacing the current result. Never execute serialized objects or use a stored path to fetch network data.

A reopened analysis does not automatically connect an audio file or start playback. Require an explicit local source selection to relink the original recording. Preserve the selected source offset and duration, and give clear errors for moved, missing, too-short or unreadable audio. Do not store or distribute the user's absolute private file path in reports. Ensure report metadata is available after reopen and that optional information does not cause a partial UI update or failed export.

## Fourth phase: retain playback linkage and complete the mixer

Keep the implemented explicit play/pause, stop, seeking, chosen-bar loop and following behavior. Link playback to the original mix in the chord workspace. Device opening and decoding stay off Tk's main thread. Reject stale preparation completions. Stop or suspend playback before capture, hardware checks, inference, language rebuild or shutdown until combined operation is specifically validated. Account for shared-mode buffering; do not claim sample-accurate DAW synchronization. Test a final partial buffer, EOF, seek and stop races, cancellation and missing-device errors.

Implement the previously requested instrument mixer in its separate workspace. Retain six estimated parts for a bounded selected range: vocals, drums, bass, guitar, piano and other. Provide independent gain, mute and solo controls with explicit semantics. A muted part stays silent; when eligible solos exist, only those parts are mixed. Keep the source recording as a separate comparison option. Do not describe the piano part as a reliable detector of every keyboard or synthesizer.

Separate once and reuse file-backed, sample-aligned stems for fader changes and exports. Do not run the model on every control movement or keep twenty minutes of six-channel floating audio unnecessarily resident. Provide individual WAV export and a mixed WAV export. Use a coherent anti-clipping policy and avoid independent normalization that changes the parts' relative balance without the user's intent. Detect uneven lengths and non-finite samples. Protect the source and existing destinations, including races where a destination appears after export begins. Clean incomplete outputs on cancellation without deleting unrelated files.

Compare any higher-quality separation setting with the current method using supported model options and bounded work. Check alignment, edge continuity and reconstruction on controlled mixtures. Those tests do not prove real-song separation accuracy. The provided Room 335 file is an end-to-end regression and listening candidate, not ground truth. If no legally usable independent stems or human listening assessment exist, report the inference setting and its computational tradeoff without asserting a measured perceptual improvement.

## Fifth phase: printable charts

Export the same effective song chord chart to A4 PDF, including manual edits, unknown regions, source time, manual grid settings and necessary legends. Do not draw guitar chord diagrams. Use sixteen bars per musical page with four bars per row when the content fits, allowing supporting detail pages for dense events instead of dropping changes. Provide chord evidence and candidate information below or in clearly linked supplemental sections when required for legibility. Keep each event traceable to the progression.

Use a maintained PDF library after checking its distribution and font requirements. Korean and English text must render on the user's packaged executable, not just the developer machine. Prefer vector symbols and lines, and include legally distributable fonts or an explicitly verified available font path. Do not copy reference artwork, lyrics or unrelated score metadata. Avoid private absolute paths in PDF metadata. Render to a temporary file and commit safely so failed generation does not leave a misleading finished document.

Printing means opening or previewing the completed PDF for the user's print action. Never send a physical print job silently. Verify page count, ordering, text and actual rendered page images. Cover short, long and dense charts, unknowns, slash symbols, manual edits, offsets, both languages and final partial pages. Physical printing remains unverified unless it is actually performed with authority.

## Optimization, verification and delivery

Retain the existing native C++ spectrum engine. The user authorizes C++ where it improves performance, not an unconditional rewrite. Measure a real hotspot before moving it. NumPy, FFmpeg, PortAudio and the AI runtime already execute native work. If inference or device latency dominates, replacing a Python wrapper is not evidence of speedup. Any new native surface needs parity, bounds, failure handling, packaging and fallback checks.

Use red-green-refactor for new behavior and focus on observable results. Use real PCM and hidden Tk for integration, with fakes only at hardware or slow external-model boundaries. Preserve old tests unless the newly approved behavior intentionally changes their contract; replace guitar-first and automatic-fingering assertions with explicit full-mixture and symbol-only assertions, rather than silently deleting coverage. Keep a test proving rich slash and suspended symbols survive display and exports.

For real-song chord quality, define annotation source, scoring vocabulary, time tolerance, unknown handling and baseline before publishing a number. Synthetic notes and mixtures prove supported cases and wiring, not general recording accuracy. Compare against the prior implementation and retain failures. Do not use the user's dissatisfaction as permission to claim improvements without evidence. Record limitations and candidate ambiguities openly.

Run the full warnings-as-errors suite after integration, source self-tests, compilation, native parity and all new workflow tests. Perform a bounded read-only review after each coherent slice. Material findings open one narrow repair pass, followed by verification and rereview. If the same root cause remains after that pass or the work needs a materially different authority, stop and request direction. Expected RED tests do not count as failed application repairs.

Update user/developer documentation, QA and build history only with current evidence. Package the final windowed executable and verify playback dependencies, native DLLs, model-cache behavior, export fonts, third-party notices, source inputs and archive checksums. Run the final frozen executable's feature checks, not only the previous release's diagnostics. Record absent audible, first-download, offline, GPU, clean-machine, printer and signing checks honestly.

Use the user's exact feature version 0.1.01. Later published bugfix releases advance to 0.1.02 and onward rather than replacing published assets. Continue the established GitHub source/tag/developer-ZIP workflow only when the feature scope and release checks are complete. Do not publish an unfinished four-feature build as complete. Keep previous releases immutable, never force-push, and never upload private user audio, credentials or model caches. Use prerelease status if essential launch evidence remains unavailable.

## Scoreboard

Current Score: 45/100
Score Source: provisional; not a numeric user rating or accuracy metric
Last Updated: 2026-10-07 01:30:55 KST (Asia/Seoul)
Rationale: All four feature slices, actual cached CPU, frozen dependencies and cold fresh archive now pass. Real-song accuracy and listening remain unmeasured.
What Improved: Full-mixture CQT, symbol-first display, corrections/reopen, playback synchronization, six-stem mixer/export and Korean PDF are implemented.
What Remains Unsatisfactory: Real-song correctness and perceptual separation quality are unmeasured; this is not a production-quality accuracy claim.
Next Actions: Preserve published assets and collect user validation for a separately scoped 0.1.02.

Score History:
- 2026-10-07 01:30:55 KST: Provisional 45/100 after verified GitHub publication. Delivery complete, not a user score or musical-accuracy metric.
- 2026-10-07 01:27:45 KST: Provisional 43/100 after cold fresh-archive proof. Not a user score or musical accuracy measurement.
- 2026-10-06 20:10:00 KST: Provisional 38/100 after 357 warnings-as-errors tests, source self-test and nine-page PDF visual QA. Not an accuracy or user score.
- 2026-10-05 09:33:10 KST: Provisional 15/100 after original approval and baseline inspection.
- 2026-10-05 09:53:52 KST: Provisional 23/100 after focused playback verification.
- 2026-10-05 10:10:50 KST: Provisional 20/100 after the user's dissatisfaction exposed a mismatch in chord-analysis intent.
- 2026-10-05 10:15:00 KST: Provisional 22/100 after explicit approval of the clarified full-song, symbol-first direction. No numeric user score has been given.
- 2026-10-05 20:58:09 KST: Provisional 28/100 after default CQT, source isolation, and symbol-only UI work. This is a delivery-progress estimate, not an accuracy metric or user score.

## Progress log

- 2026-10-07 01:30:55 KST: Published https://github.com/JH-Prime/ToneMatchTMP/releases/tag/v0.1.01 from f327015ebef2ef806de8d0a0cb64f1dbbe22db98. GitHub draft=false/prerelease=true and all three asset sizes/SHA256 match. No force push or old-release replacement. Delivery complete; remaining listening/accuracy/hardware limitations are explicit.

- 2026-10-07 01:27:45 KST: Final ZIP 349399545 bytes verified: 5438 manifest hashes, 80 matching source/build inputs, native/font/license parity, no private paths/media/weights/development JIT caches, fresh EXE and cold CQT successful. SHA256 5F3C455044DC7132833B0CD55CEBAD01384FDB1AAD39A3E677B1F70B9ABAAD2F. Publish ZIP/checksums/independent receipt as an immutable developer prerelease; no runtime source changes remain.

- 2026-10-07 01:25:16 KST: Unpublished ZIP inspection found 54 development Numba cache files. Added packaging-only exclusion and retained first archive locally, plus PortAudio notice/platform filtering. Application EXE unchanged; rebuild metadata synchronized and ZIP regenerated. Require cold fresh CQT proof and complete archive verification before publication. No published release altered.

- 2026-10-07 01:18:25 KST: Rebuilt EXE passes CQT/music/C++ diagnostics and 80 source-input comparison. Final suite 358 / 201.559s OK. Actual cached CPU EXE processes the full 252.6099s sample in 98.417s, cancellation in 10.210s, source preserved and temporary/partial outputs cleaned. Real mixer seven aligned exports and source CQT also passed. Both narrow cancellation/SciPy repairs closed. Archive receipt and publication remain; score 38 retained until independent archive proof.

- 2026-10-06 20:10:00 KST: Version moved to 0.1.01. Final build's full suite passed 357 tests in 169.013s; C++ ABI 2 parity passed. Source music diagnostic passed actual CQT, corrections, PCM/mixer WAV, Korean PDF/font and PortAudio DLL loading without audible output. Fixed old version-test regex to allow the approved minor version. Developer pipeline now describes full-mixture CQT. PyInstaller build running; docs refreshed and historical implementation sections explicitly labelled. No push/tag/release yet.

- 2026-10-06 19:53:33 KST: Resumed; no published v0.1 tag and remote main remains 874aeb1. PDF rendering review covered nine synthetic pages with no glyph/overlap/loss defect. The last full-suite process output was unavailable after session restart, so it is being rerun. Activate final package/verification phase and add a frozen diagnostic for the new CQT/playback/mixer/PDF dependencies before building.

- 2026-10-05 21:21:04 KST: PDF initial implementation passes three content/boundary and two hidden UI tests. ReportLab 4.5.1 and Pillow 12.3.0 pinned, pypdf 6.19.0 development-only. Unmodified Nanum Gothic with OFL notice is bundled for Korean output. Export runs off Tk, snapshots corrections, preserves dense events in detail pages and only opens a viewer after explicit preview selection; no print job is sent. Render QA follows.

- 2026-10-05 21:16:23 KST: Complete suite passed 351 tests in 163.515s after mixer integration and bounded output-exclusion repair; rereview accepted this slice. Activate approved PDF phase with ReportLab vector layout and bundled OFL Korean font, without automatic printing.

- 2026-10-05 21:12:34 KST: Mixer backend/session plus playback tests passed 21 checks; hidden UI prepare/fader/solo/export/language/reopen passed two checks. Read-only review found output overlap with original transport, reproduced by a third UI test. Bounded repair adds a side-effect-free output guard while permitting the mixer's own Pause. A missing Stop localization key was corrected. Score remains 28/100 pending integrated proof and PDF.

- 2026-10-05 21:06:55 KST: Loader repair and migrated full-song display contracts verified by the complete 342-test warnings-as-errors run (153.021s, OK). Independent mixer backend initial three tests pass; reader-factory integration and asynchronous UI are next. Score remains provisional 28/100 because mixer/PDF/release and real-song quality evidence remain incomplete.

- 2026-10-05 20:58:09 KST: CQT focused tests pass, including major/minor/sus/slash, C6/Am7 alternatives, noise/silence rejection, phase-safe stereo, quiet third, progress and cancellation. Whole-source wiring and unchanged tone/reference PCM tests pass. Engine 19 tests pass. Full suite reached 340 tests with 11 failures, all old fingering/slash-suppression expectations; migrated those contracts and focused reruns pass. Full rerun still needed. Review exposed malformed saved evidence and lost tone-separation metadata; reproduction tests now fail before the bounded loader repair.
- CQT comparison: 246 controlled synthetic cases (41 qualities × 3 roots × pure/harmonic) both FFT and CQT matched all expected labels; aggregate elapsed FFT 7.825s, CQT 31.014s. These are regression cases, not real-song accuracy. Room 335 original range 30–90s completed in CQT 4.974s versus FFT 1.014s; CQT coverage 0.2323 versus FFT 0.4242. Coverage is not accuracy. No reference annotations or perceptual-quality claim. No user audio is copied into version control.

- 2026-10-05 10:15:00 KST: Approved v02 saved before revised implementation. Preserve unfinished corrections and playback; repair known integration failure, then change the chord source and presentation with targeted regressions.
- 2026-10-05 15:34:23 KST: Resumed under the existing approval. Correction reopen-to-HTML repair passed 8 focused tests. Reddit provenance and its linked primary implementations were checked; no accuracy claim inferred from comments.
- User subsequently selected CQT as the preferred implementation. Make true constant-Q pitch extraction the default full-mixture chord path (not an FFT-bin relabel). Keep the prior FFT analyzer for regression comparison and legacy diagnostics. Librosa 0.11.0 is the initial proven implementation candidate; bound chunk memory, preserve stereo phase safety and cancellation, measure startup/steady-state cost, pin dependencies and verify frozen distribution. This is within the approved algorithm phase, not a new feature approval gate. Performance skill governs measurement, not an unconditional C++ rewrite.
