# ToneMatch TMP 0.1.07

Source reference: 2026-11-03 KST. Unsigned Windows CPU developer prerelease.
Source, local-file and frozen verification have passed; archive/publication are separate gates.
See [한국어 안내](README_KO.md), [QA](QA_REPORT_v0.1.07.json) and [build history](BUILD_HISTORY.md).

## Changed in 0.1.07

- Normal EXE startup checks this repository's published numeric Windows portable releases,
  including the existing developer prerelease channel. Newer versions download, verify and open
  automatically. Offline, failed or cancelled updates fall back to the installed app.
- Archive SHA-256, safe paths, full manifest inventory and per-file hashes are required.
  Side-by-side installation keeps the old executable and original settings/results.
- CQT withholds power chords explained only by a tightly coherent harmonic series and prevents
  an isolated rejected harmonic from returning as a display alternative. Actual independent
  fifths, weak roots/fifths and detuned controls are preserved. FFT and native ABI remain unchanged.
- Modulo audit found no random-integer modulo sampling in production scoring. All 242,064
  transposed-template comparisons agree within 1.11e-16. Evidence scores are not probabilities;
  exact ambiguous tie ordering remains a separate limitation.

433 headless tests pass; 92 GUI-containing tests are deferred. The original 62-case synthetic
comparison preserves 76.117 correct seconds while incorrect seconds fall from 23.116243 to
1.516243. Dedicated harmonic/power31, uncertainty32 and transition11 comparisons pass.
These are development fixtures, not real-song accuracy. Exact harmonic coincidence, noise and
vibrato can remain ambiguous or incorrect.

## Automatic updates and recovery

Install v0.1.07 manually once: v0.1.06 cannot acquire this feature retroactively. Extract the
whole ZIP and launch `ToneMatchTMP-v0.1.07.exe`; retain this executable as the entry point.
New versions live in installation-specific folders under
`%LOCALAPPDATA%/ToneMatchTMP/updates`. The updated app reuses the original portable data
location and its existing writable-directory fallback. No user audio is uploaded.

Use **Use installed version** to skip a startup update, or launch the original executable with
`--skip-update` for recovery. Older installed versions are not automatically deleted.
Source runs and diagnostics bypass updates. Hashes establish integrity relative to GitHub
release metadata, not independent publisher signing. Native interaction, listening and physical
printing are untested in this no-screen verification run.

## Archived v0.1.06 release record

An unofficial Windows tool for whole-mixture chord charts and starting-point Fender Tone Master Pro
or Quad Cortex recipes from authorized local audio/video and Windows capture.
Source reference: 2026-11-01 KST. Unsigned CPU developer prerelease.
Published after fresh-archive verification: [download v0.1.06](https://github.com/JH-Prime/ToneMatchTMP/releases/tag/v0.1.06).
Unauthenticated public readback matched all three asset sizes/digests on 2026-11-01.
See [한국어 사용 안내](README_KO.md), [v0.1.06 QA](QA_REPORT_v0.1.06.json) and [build history](BUILD_HISTORY.md).
Source, local real-file and frozen executable checks passed. The external archive-verification receipt
and release page record fresh-ZIP verification and publication; those are separate release gates.

## Changed in 0.1.06

- CQT requires resolved note peaks before combining octaves, reducing false notes from filter
  shoulders and weak responses. It keeps the sustained interpretation first and considers
  sequential-note evidence only when that interpretation contains no observed pitches.
- Selected seventh/ninth chords may omit the perfect fifth when the root, third and named
  extensions are supported. The absent fifth is never reported as an observed note.
- Quiet CQT regions preserve their unresolved state without an optional-field error or a chord
  inferred from neighboring sound. Unknown intervals, explanations and candidates remain available.
- FFT peak extraction keeps the exact v0.1.05 behavior. The attempted low-bass recovery change
  was deferred after harmonic false positives; some valid overlapping low-bass chords remain unresolved.

Verification: 387 guarded headless tests passed; 92 native GUI tests are deferred. The 62-case
CQT/FFT precision comparison passed all per-case gates: correctly recognized duration increased
from 55.743 to 76.117 seconds and incorrectly recognized duration decreased from 29.090243 to
23.116243 seconds. Previously unresolved intervals contributed 14.4 newly correct seconds and
zero newly incorrect seconds. The 32-case uncertainty comparison passed; eleven trace sequences
retained 99.36% duration-weighted symbol agreement. These are development fixtures, not measured
real-song accuracy or a guarantee that every chord is correct. No UI, dependency or C++ ABI change
is included. Native interaction, listening and physical printing were not tested.

The local 252.61-second Room 335 file and its 30–90 second excerpt passed CQT/FFT progress,
cancellation, unchanged-input, edit/reopen and HTML/PDF checks. Full-file recognized coverage was
43.22% for CQT (previously 49.51%) and 43.23% for FFT (previously 35.87%). CQT abstains more often
on this input; neither change demonstrates accuracy or establishes which method is better.

Keep the v0.1.05 portable folder and original results for rollback. Reanalyze a file to use the new
logic; saved automatic results and manual corrections are not silently rewritten.

## Historical v0.1.05 release record

The following v0.1.05 and older dates, measurements and publication statements describe those releases only.

An unofficial Windows tool for authorized local audio/video and Windows capture:
whole-mixture chord charts plus three starting-point Fender Tone Master Pro or Quad Cortex recipes.
Source reference: 2026-10-17 KST. Unsigned CPU developer prerelease.
Published on 2026-10-18 after source, frozen and fresh-ZIP verification: [v0.1.05 download](https://github.com/JH-Prime/ToneMatchTMP/releases/tag/v0.1.05).
All three public asset sizes/digests match the locally verified artifacts; keep the previous portable folder for rollback.
See [한국어 사용 안내](README_KO.md), [v0.1.05 QA](QA_REPORT_v0.1.05.json) and [build history](BUILD_HISTORY.md).

## Added in 0.1.05

- Unresolved intervals retain observed notes, up to three supported candidates and a reason.
  Their primary chart label remains `?`; candidates appear below, not as confirmed chord names.
- Distinguish quiet signal, insufficient tonal evidence, weak/competing matches, insufficient
  temporal support, unobserved gaps and output-limit omissions. Unknown does not mean N.C.
- CQT may review a candidate-bearing unresolved observation at bounded 0.3/1.0-second lengths,
  reusing the current transform and harmonic boundaries. Both lengths must agree with an original
  candidate, required original observed notes and temporal support. No recursive guess-filling.
- FFT also preserves candidates/reasons but does not receive this new alternate-length retry.
  CQT output has a 4096-event budget with explicit output-limit gaps, preserving timeline coverage.
- UI, HTML, PDF and reopened JSON retain uncertainty details. Manual corrections remain separate
  from automatic evidence; restoring the original result brings its candidates back. No fingerings.

Candidate availability and coverage are not accuracy. Recovery of every missed chord, higher
real-song accuracy and faster analysis are not guaranteed. Keep v0.1.04 and original results for rollback.

Verified source evidence: 348 guarded headless tests passed; 92 native GUI cases remain deferred.
The 32-case CQT/FFT comparison passed with zero newly correct or incorrect recognized seconds.
The eleven-sequence timing corpus retained 99.36% duration-weighted symbol agreement, unchanged
from the previous version. These are development fixtures, not a real-song accuracy benchmark.
On the local 252.61-second Room 335 CQT check, recognized coverage remained 49.51%; 2.25 seconds
of unresolved candidate evidence were retained, with zero recovered observations. The full-file FFT
check passed with unchanged 35.87% coverage and 113.10 seconds of unresolved candidate evidence;
candidate availability is not a comparison of accuracy. Frozen CQT/FFT, uncertainty reopen/export,
PDF font, mixer export and C++ ABI 2 parity checks passed. An independently extracted archive and
matching public asset digests are required before publication; see the external archive-verification receipt.

The figures and verification in the v0.1.04 and older sections below are historical, not current-patch proof.

## Added in 0.1.04

- Modeler selection recovers after analysis success, failure or cancellation, including the
  terminal-event/thread-return race. Idle **Chords only** also permits choosing the next tone device.
  Chord extraction remains device-independent; ongoing tasks still lock controls.
- CQT observes every 50 ms, with spectral-change timing used to bound pitch evidence windows.
  Short opening/closing chords and duration-weighted candidate paths are preserved.
  This does not upsample audio or guarantee 50 ms transcription accuracy.
- Eleven annotated synthetic sequences improved duration-weighted symbol agreement from
  90.66% to 99.36%. These development signals are not a real-song accuracy benchmark.
  Finer observations add work; exact path/scoring optimizations mitigate that cost, not an overall speed guarantee.
- No-screen regression checks are separate from native clicking/layout verification, which is deferred.
  CQT and FFT remain selectable; existing saved corrections are not automatically reanalyzed.

## Added in 0.1.03

- Clear, padded **Tone + chords / Chords only** choices and an actual **CQT / FFT** selector.
  Both consume the original mixture. CQT remains the default; legacy FFT retains its fixed 440 Hz,
  pitch-range weighting and harmonic suppression. No automatic guitar fingering is shown.
- Removed the user-facing equipment inventory entrypoint; internal recipe data remains.
- Dark playback/loop/follow controls, compact small-window layout and language-specific fonts.
  GUI requests Malgun Gothic for Korean and Arial Narrow for English; PDFs keep licensed Nanum Gothic.
- Method identity survives JSON/localization/HTML/PDF. FFT results support immediate manual edits.
- No measured real-song accuracy gain is claimed. Compare the evidence and alternatives yourself.

Keep the preserved v0.1.02 folder for rollback. Old release assets and source audio are unchanged.

## Added in 0.1.02

- Select **Chords only** to bypass guitar separation, AI downloads and modeler selection.
- Choose Quad Cortex and your CorOS version for three of six curated native starting points.
  Start at device defaults: numerical QC knob ranges are unverified, not copied from TMP.
  Older firmware may use the previous names shown in the catalog.
- Internal recommendations use the [official device list](https://neuraldsp.com/device-list) snapshot
  (2026-10-07). The inventory browsing entrypoint was removed in 0.1.03; licensed and unreleased entries are excluded.
- CQT estimates a global tuning offset from at most 12 seconds of pitch-peak evidence,
  falling back to zero when peaks disagree. Twelve detuned synthetic C/Am/Dsus4 cases pass.
  Room 335 detection coverage is unchanged: 11.88% full-song, 23.23% excerpt, **not accuracy**.
- JSON reopening, localization and HTML preserve QC/chords-only identity.

Keep the old portable folder for rollback. Older versions may not open the new QC/chords-only
result types; retain original analysis files and use a new filename for new results.

## New workflow

- Original-mixture **CQT → chroma → 41 chord templates**, independent of guitar-tone isolation.
  Chord symbols, slash/sus/extensions, evidence and alternative candidates; no automatic fingering.
- Explicit audio playback, pause, seek, loop and chart/page synchronization. Nothing autoplays.
- Direct chord edits, up to 50 undo steps, restore original, JSON save/reopen.
  Corrections remain separate from original estimates and do not inherit machine confidence.
  Reopened results require explicit audio relinking.
- Six-stem mixer: 0–200% gain, mute, solo, original comparison, individual and mix WAV export.
- A4 sixteen-bar PDF, with all events/evidence retained in continued detail pages.
  Explicit preview opens a PDF viewer; it never sends a print job.

CQT is the selected frontend, **not evidence of higher real-song accuracy**.
Scores are heuristic evidence, not probabilities. The 246-case controlled comparison matched all
labels on both frontends; CQT was slower. Room 335 has no independent time-aligned ground truth.
Ambiguous names (e.g. C6/Am7), melody, percussion, harmonics and omitted notes remain difficult.

## Start

Extract the **entire** developer ZIP to a new directory, verify SHA-256, then run
`ToneMatchTMP-v0.1.07.exe` once its package has been verified and published. Do not move only the EXE.
Choose authorized local media or PC capture, then a range of 3 seconds to 20 minutes;
end `0` means through the end subject to that cap.
Full-mix tone analysis isolates guitar; already-guitar audio can skip isolation.
Chord input is always the selected original source. A separation failure can still stop the
overall tone workflow; choose **Chords only** to run without guitar separation.

First AI separation needs internet access and storage for the Demucs `htdemucs_6s` model.
Weights are not bundled. Complete per-user caches are reused. The portable runtime is CPU-only.
Stage progress and cancellation are shown; in-flight inference may delay cancellation.

The chart uses four bars per row, sixteen per page. Manually adjust BPM, beats per bar and
first-bar position, expressed in seconds **relative to the analysis range**. This is a
constant-tempo display grid, not detected downbeats or tempo/meter changes.
Playback uses the default output device; its processed-buffer clock is not a hardware
sample-accurate audible cursor. No ASIO or exclusive-mode output is claimed.

Open the mixer from Stem removal. Prepare once, then mix vocals/drums/bass/guitar/piano/other
without another AI pass. Multiple solos combine; mute wins. Original comparison is monitoring
only and does not replace the exported mix. Individual exports ignore fader/mute/solo and
preserve relative stem levels under shared clipping-prevention headroom. Mixes can sound quieter
than the source. Output is new 44.1 kHz stereo PCM16 WAV; existing files are never overwritten.
Twenty minutes of six float32 stereo stems uses about 2.54 GB of temporary storage, plus decoded
original audio. Temporary banks close on application exit.
No new separation model or quality improvement is claimed. Piano is not every keyboard sound;
leakage, missing notes and artifacts remain possible. Existing selective stem removal is retained.

Save PDF from Tools. Dense bars show three symbols plus a continuation notice; the detail
pages preserve every change. Embedded OFL Nanum Gothic supports Korean without host font setup.
For printing choose save-and-preview, then check paper/scale/printer in the viewer yourself.

## Retained scope and limitations

Korean/English UI; authorized WASAPI recording; raw-input live spectrum; level-normalized
Reference Compare; independent chord/scale guide (41 qualities, 12 scales and major/natural-minor
diatonic chords); developer source view. Pentatonic and diatonic are scale/harmony concepts,
not interchangeable chord qualities. Live PCM/FFT/smoothing uses C++ ABI 2 with explicit NumPy
fallback. CQT, AI, UI and device control are not a wholesale C++ rewrite.

Tone recipes use the firmware 1.8.58 / Model Guide Rev. J catalog, require manual entry,
and do not identify original equipment, clone Fender DSP or upload presets. JSON is not a
Tone Master Pro `.preset`. YouTube URL input/downloading is not provided.
Only use and share media for which you have the necessary rights.
Real-song accuracy, listening, physical capture/printing, clean-machine installation,
first-download, offline and CUDA evidence remain separately identified in QA.

## Develop and build

Use Windows x64 Python 3.12. The ZIP's `source` folder is self-contained.
Git excludes large generated binaries: copy `resources/ffmpeg.exe` from the developer ZIP
and rebuild the native DLL with pinned Zig 0.15.2.

```powershell
py -3.12 -m venv ..\.venv
& ..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& ..\.venv\Scripts\python.exe tools\build_native.py --zig C:\Tools\zig-0.15.2\zig.exe
& ..\.venv\Scripts\python.exe -W error tools\verify_headless.py --output .\headless-v0.1.06.json
& ..\.venv\Scripts\python.exe app.py --self-test-output .\self-test-v0.1.06.json
& .\build.ps1 -SkipTests -ZigPath C:\Tools\zig-0.15.2\zig.exe
```

This no-screen sequence skips a repeated build-time test run only after the guarded headless
receipt passes. The runner forbids Tk construction and records deferred GUI cases. Full unittest
discovery and builds without `-SkipTests` include window-creating tests; use them only in a separately
authorized interactive verification session. Deferred native UI tests are not considered passed.

Official Zig 0.15.2 Windows x64 ZIP SHA-256:
`3a0ed1e8799a2f8ce2a6e6290a9ff22e6906f8227865911fb7ddedc3cc14cb0c`.
EXE users need no compiler. Optional CUDA source setup uses `enable_cuda.ps1` and requires
compatible hardware plus revalidation. Self-test covers CQT, corrections, mixer PCM/WAV,
PDF/font, PortAudio loading and native parity without audible output or actual model inference.
The separate `--stem-self-test-source` / `--stem-self-test-output` CLI checks an already
cached CPU model, writes redacted JSON and cleans temporary audio.

The current source version is 0.1.07. After publication, fixes advance to 0.1.08; published releases are immutable.
Read [handoff](DEVELOPER_HANDOFF_KO_EN.md) and [research](TRANSCRIPTION_RESEARCH_KO.md).
Application source: MIT. See `THIRD_PARTY_NOTICES.txt`, inventory and `licenses/`.
Fender, Tone Master, Neural DSP and Quad Cortex are their owners' trademarks;
this project is not affiliated with or endorsed by Fender or Neural DSP.
