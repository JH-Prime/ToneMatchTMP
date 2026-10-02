# ToneMatch TMP 0.0.12

ToneMatch TMP is an unofficial, pre-release Windows desktop tool that analyzes a
local audio/video file or authorized Windows playback capture, isolates the guitar
stem, and recommends three starting-point tone chains for Fender Tone Master Pro.
Version 0.0.12 expands audio chord candidates from 20 to 41 qualities and adds an
independent **Chord & scale guide** with piano-key diagrams, 12 scales/modes and
major/natural-minor diatonic triads and sevenths in all 12 roots.
A theoretical chart is not a detected performance: ambiguous harmony remains a
candidate, not a guaranteed transcription or physical guitar fingering.
The build reference date is 2026-10-02 KST. Verified outcomes belong in
`QA_REPORT_v0.0.12.json` and `BUILD_HISTORY.md`.

한국어 설치·사용 안내는 [README_KO.md](README_KO.md)를 먼저 읽어 주세요.

## v0.0.12 validation status

The October 2 build passed 282 automated tests (`-W error`), compileall and
source/frozen chord, theory-guide and native-DSP self-tests. On October 3 the
final EXE passed actual cached-CPU full-song removal and cancellation, followed
by fresh-extract integrity and EXE checks. See `QA_REPORT_v0.0.12.json` and
`BUILD_HISTORY.md` for scope; earlier release passes are not reused.

A fixed synthetic comparison covers 41 qualities × 12 roots × 2 textures:
v0.0.12 matched 984/984 expected primary labels, versus 480/984 in v0.0.11, and
both rejected all 36 nonchord controls. This is not real-song accuracy.
Room 335 has no independently verified, time-aligned chord annotation in this
project, so successful processing or detected coverage cannot establish
transcription accuracy. This remains an unsigned CPU developer prerelease.
Hidden-window/headless checks do not substitute for manual UI, listening,
first-download, network-disabled, CUDA or actual capture testing.

## Current scope

- Korean/English UI with Malgun Gothic / Arial Narrow preferences
- Tone Master Pro firmware 1.8.58 and Model Guide Rev. J catalog
- Up to 20 minutes per analysis; `end = 0` means through the end, capped at 20 minutes
- Demucs `htdemucs_6s` guitar-stem isolation for full mixes
- Three outer workspaces: `Tone analysis`, `Stem removal`, and `Chord & scale guide`; Stem removal removes any one to five selected
  `vocals`/`drums`/`bass`/`guitar`/`piano`/`other` estimates, mixes what remains,
  and writes one new 44.1 kHz stereo PCM16 WAV
- Stem-removal progress, elapsed time and cancellation, with no source or
  existing-destination overwrite and cleanup of decoded/mix/partial temporary files
- New-source reset of stem-removal results/progress and dangling-link-safe destination checks
- Truncated-WAV rejection and cleanup in guitar isolation
- A separate real-model headless stem diagnostic with temporary-audio cleanup and path-redacted JSON
- Visible stage-weighted analysis percentage and elapsed time, with actual model
  download bytes/file percentage and completed Demucs-block audio duration
- Auto/CPU/CUDA compute preference with GPU, VRAM, inference-time, and real-time-factor diagnostics
- Windows WASAPI loopback/audio-input recording when no local file is available
- Live raw-input waveform and logarithmic 20 Hz-20 kHz spectrum for the selected
  WASAPI input or playback loopback, with RMS/peak dBFS and spectral centroid
- C++ live-DSP by default when the bundled ABI-2 DLL is available and compatible;
  explicit NumPy fallback reporting when it cannot be used
- Direct aligned, native-endian, C-contiguous float32 input without the former
  Python float64 upcast; float64 input remains supported
- Live DSP push time and engine input/completed-window/pending-frame diagnostics,
  separate from capture time, AI analysis and audio round-trip latency
- A level-normalized reference spectrum from the analyzed local source or isolated
  guitar stem, compared against Current live input as Reference, Current, and delta
  (Current minus Reference) across six stable frequency bands
- Three ordered TMP recipes with output-route-specific Amp/Cab rules, plus JSON, HTML, and clipboard output
- Chord/voicing analysis timeline with source labels, original-file times,
  unknown intervals and evidence diagnostics; guitar-source results may include
  bass/inversion, register, spacing and playable-candidate cues
- Optional original-mix harmony reference when separated guitar evidence is weak,
  without claiming guitar fingering, bass or inversion from the full mix
- Work-area-aware startup sizing and a fixed-height, scrollable analysis status
  area that does not expand indefinitely after analysis
- Native NumPy vector optimization for repeated chord/voicing spectrum work
- Clickable 11-stage developer diagram with bundled source, Korean docstrings, logs, and changelog
- Quad Cortex and Line 6 Helix are visible extension placeholders only

## Chord & scale guide

Open the third outer **Chord & scale guide** tab without loading or analyzing
audio. Choose a root, then a category and type. The keyboard, chord symbol,
component notes and degree formula update immediately.

- **Chords:** 41 qualities × 12 roots, including major/minor, sus, diminished,
  augmented, 6/9, 7/9/11/13, minor-major and altered dominant chords.
- **Scales:** major/Ionian, natural minor/Aeolian, major and minor pentatonic,
  harmonic minor, ascending melodic minor, Dorian, Phrygian, Lydian, Mixolydian,
  Locrian and six-note minor blues. Pentatonic is a scale, not a chord quality.
- **Diatonic:** each degree of a major or natural-minor scale has a triad and a
  seventh chord. Select a row to inspect its tones on the keyboard. “Diatonic”
  describes a relationship to a scale, not another independent chord type.

The chart preserves theoretical spelling, such as E♯ and B♯ in C♯ major or C♭ in
E♭ natural minor. Enharmonic names can share one piano key. Extensions 9, 11 and
13 appear in their upper octave; actual playing can use other inversions,
octaves and omissions. Natural-minor diatonic rows do not silently substitute
harmonic-minor V chords. Melodic minor is explicitly the ascending form.
This guide is read-only and independent of the audio chord timeline; it does
not detect scales or keys, fill unknown audio events, or alter tone recipes.

Theory references: [Yamaha on pentatonic scales](https://hub.yamaha.com/guitars/g-how-to/a-guitarists-guide-to-major-and-minor-pentatonic-scales/),
[minor-scale forms](https://musictheory.pugetsound.edu/mt21c/MinorScales.html),
and [diatonic seventh chords](https://musictheory.pugetsound.edu/mt21c/RomanNumeralsOfDiatonicSeventhChords.html).

## Important boundaries

There is no YouTube URL input or downloader in this version. Use an authorized local
file, including your own upload obtained through a service-provided download, or
record audio only where recording and analysis are permitted. Permission from a
copyright holder does not by itself settle a platform's access/download conditions.
YouTube's [Terms of Service](https://www.youtube.com/static?template=terms) and
[API developer policies](https://developers.google.com/youtube/terms/developer-policies)
restrict downloading and audio separation outside their authorized routes; the
app does not assume a general URL extraction entitlement or bypass restrictions.
The recording feature is a general local input, not a YouTube-download workaround.
The app does not write presets to Tone Master Pro or claim to recover the original
rig, exact DSP, or physical guitar fingering. Candidate shapes are suggestions,
not detected tablature.

Open the outer `Stem removal` workspace tab for a Logic-like workflow; it does not claim Apple
Logic Pro model or quality parity. Choose a local audio/video source, a new `.wav`
destination, a range of at least three seconds and at most 20 minutes, a compute
mode, and one to five parts to remove. End `0`/blank means the remainder of the
source subject to the 20-minute cap. The app sums only the unselected Demucs stems
and publishes a single stereo PCM16 file. It never modifies the source, refuses an
existing destination, and does not save individual stems. Saving uses atomic
no-overwrite creation, including when another file appears at the destination
during processing. If the kept-stem sum would exceed full scale,
one global gain reduction prevents clipping while preserving relative levels.
`Piano` is the model's piano estimate, not a separate detector for every keyboard
or synthesizer sound; such sounds may also fall into `Other`. User audio and output
stay local; only first-use model acquisition needs the network. Leakage, missing
instruments, phase/attack/reverb changes, and other separation artifacts are
expected limitations, so keep the source and audition the result.

The AI model weights are not committed or redistributed. The first full-mix
analysis or Stem removal job downloads them to the current Windows user's
Hugging Face cache.
The app checks the cache before downloading the official YAML/safetensors model;
it does not silently fall back to legacy model downloads. Version 0.0.06 also
guards missing console output streams in the windowed EXE, preventing the
`'NoneType' object has no attribute 'write'` progress-output failure. Model setup
errors distinguish server/network access, cache permissions or disk space,
memory, and other model/runtime failures instead of treating every failure as
an internet outage.

The analysis bar shows overall stage progress, not a time-based completion
estimate. Elapsed `mm:ss` refreshes on a 250 ms UI timer, while the percentage
advances only from processing callbacks. Download details show received bytes
and a file percentage when the total is known. Guitar-isolation details update
after completed internal Demucs blocks within the outer 30-second chunks and
show processed audio seconds; they do not update on every CPU cycle. Cancellation
is checked at those block boundaries and download callbacks, so a running block
or pending network operation can still delay cancellation. No reliable ETA is
claimed.

The chord tab is independent of tone matching. When a separated guitar stem is
very weak or has little chord evidence, the same selected range of the original
local mix can be analyzed as a **harmony reference**. The source is labeled
`original_mix`; its events do not claim guitar shapes, register, spacing, bass or
inversion. This does not replace the guitar PCM used for tone features, Reference
Compare or recipes. A weak stem produces a warning; a signal too close to true
silence for tone analysis still stops the analysis.

Chord evidence is not transcription accuracy or the recipe match percentage.
Repeated support is required for stable candidates; missing evidence remains
unknown instead of being filled with an invented chord. Source-relative offsets,
active/reliable frame counts and signal level help explain empty or partial
results, but drums, single-note parts, dense mixes and separation artifacts can
still defeat the estimator. Evidence scores and alternative candidates describe
observed support, not a calibrated probability that a chord is correct.

Version 0.0.12 adds 21 audio qualities to the previous 20: 7sus2,
11/maj11/m11, 13/maj13/m13, m(maj7)/m(maj9), 6/9/m6/9,
7♭5/7♯5/7♭9/7♯9/7♯11/7♭13, maj7♯5/maj7♯11, add11/m(add11).
Extensions still need observed support, and additional labels are not a guarantee
that complex real-world harmony can be uniquely identified.

Historical v0.0.11 evidence (not current-build validation): that version expanded
9 chord qualities to 20, adding 6, m6, m7b5, dim7, aug,
add9, madd9, 9, maj9, m9 and 7sus4. Coverage-based scoring avoids favoring smaller
subsets over supported extensions. Shared pitch-class sets such as C6/Am7 show
alternative readings. Observed pitch-class candidates and template tones are
separate; a changing bass splits inversion events for guitar inputs.

A fixed 480-case synthetic comparison (20 qualities × 12 roots × 2 textures)
matched the expected primary label in 480 cases, versus 186 in v0.0.10. Both
rejected all 36 single-note/nonchord/noise controls. This is not 100% accuracy on
real songs. The v0.0.11 complete Room 335 smoke test selected original-mix harmony due
to a weak separated guitar, with support in only 68/421 windows (16.15%). Many
intervals remain unknown. That coverage is not accuracy, and no independent,
time-aligned ground truth was available to validate real-song transcription.

The portable EXE ships with the CPU runtime for broad Windows compatibility.
CUDA is available only after installing the separate source-development CUDA
environment on a compatible NVIDIA PC. It was not hardware-validated on the
CPU-only release machine. The C++ change is limited to the live PCM/FFT/smoothing
boundary. It does not migrate device capture or accelerate whole-song Demucs
analysis. Performance measurements, when available, are scoped to the tested
workload in QA; NumPy already executes compiled FFT routines.

The v0.0.06 Reference Compare view reuses the existing live monitor, whose Current
DSP backend is now C++ with a NumPy fallback.
File analysis creates the Reference from the exact analyzed signal: the Demucs
guitar stem for a full mix, or the decoded source when isolation is skipped. The
Current side is the selected raw live device. Their overall levels are normalized
before comparison, so the six-band and frequency-difference values describe tonal
shape rather than input gain. Positive delta means Current is stronger in that
band; negative means Reference is stronger.

Play the same notes or phrase as the reference: pitch, pickups, separation artifacts,
and capture routing also affect the difference. The current 22.05 kHz reference
analysis limits comparison to about 11 kHz. The graph displays ±18 dB; table
values retain the full difference. JSON/HTML store the reference profile, while
live Current/delta values remain in the session and can be copied from the tab.

This comparison is not a statistical accuracy score or a match probability. It
does not yet provide live Brightness, Body, Gain, Compression, Ambience, or Match
percent meters, automatically derive EQ/TMP settings, or write a preset.
Legacy exported reference-URL metadata remains readable for compatibility; it is
not an input or a network fetch. The monitor is WASAPI shared mode through
Python/SoundCard; it is not a C++ device-I/O callback, ASIO, WASAPI
Exclusive, or a hard-real-time audio path.

`native_dsp.py` loads only the bundled `resources/tonematch_dsp.dll`, checks ABI 2,
and selects C++ automatically when compatible. Missing or incompatible native
code falls back to the NumPy reference path and reports the actual backend;
explicit developer `backend="cpp"` requests fail instead of silently falling back.
An older ABI-1 DLL is incompatible: do not mix files from different release ZIPs.
The accumulator retains incomplete FFT windows for the next input block; stop or
reset discards that partial window. Completed non-overlapping windows use the
same channel-power and four-frame smoothing contract. Native processing buffers
are allocated at creation. Compatible float32 input reaches `tm_dsp_push_f32`
without a Python float64 conversion; other layouts may require normalization.
The float64 path remains available. The engine reports accepted `input_frames`,
`completed_windows` and `pending_frames`; reset clears these counters and the
partial window. DSP push time measures the processing call, not device capture,
AI, UI drawing or audio round-trip latency. Python output copies, locks and
shared-mode capture remain, so this is not an end-to-end zero-copy, lock-free or
hard-real-time claim.

## Develop and build

Use 64-bit Python 3.12 on Windows. The portable development ZIP includes the
required `resources/ffmpeg.exe`; the Git repository intentionally excludes that
large binary. Copy it from the ZIP to `resources/ffmpeg.exe` before a source build.

Clone the public source on another PC with:

```powershell
git clone https://github.com/JH-Prime/ToneMatchTMP.git
Set-Location .\ToneMatchTMP
```

```powershell
py -3.12 -m venv ..\.venv
& ..\.venv\Scripts\python.exe -m pip install -r requirements.txt
& ..\.venv\Scripts\python.exe tools\build_native.py --zig C:\Tools\zig-0.15.2\zig.exe
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
& ..\.venv\Scripts\python.exe app.py --self-test-output .\self-test-v0.0.12.json
& ..\.venv\Scripts\python.exe app.py
```

The optional real-model stem diagnostic does not open a GUI. It removes guitar
and piano into a private temporary WAV, verifies output/progress/source
preservation, deletes the audio output, and writes a `tonematch-stem-self-test/v1`
JSON report without source/destination filenames, source hashes or model-cache
paths. It uses only an already complete local model cache; missing or incomplete cache
fails without a download. The diagnostic is CPU-only. The default `0` duration
means the full source subject to the normal 20-minute cap. Use a new JSON path.

```powershell
& ..\.venv\Scripts\python.exe app.py --stem-self-test-source C:\Audio\sample.mp3 --stem-self-test-output .\stem-check-v0.0.12.json
& ..\.venv\Scripts\python.exe app.py --stem-self-test-source C:\Audio\sample.mp3 --stem-self-test-output .\stem-cancel-v0.0.12.json --stem-self-test-seconds 31 --stem-self-test-cancel-at 35
```

For the packaged build, replace `python.exe app.py` with
`.\ToneMatchTMP-v0.0.12.exe` and the same flags. The cancellation threshold
requests cancellation at a reported percentage, not at a guaranteed elapsed
time; in-flight inference or network work can delay it. These are optional,
potentially CPU-intensive diagnostics, not the ordinary lightweight
`--self-test-output` check.

Portable EXE users do not need a compiler. For a source/native rebuild, use the
pinned [official Zig 0.15.2 Windows x64 archive](https://ziglang.org/download/0.15.2/zig-x86_64-windows-0.15.2.zip)
and verify SHA-256
`3a0ed1e8799a2f8ce2a6e6290a9ff22e6906f8227865911fb7ddedc3cc14cb0c`
before extracting it outside the project. Pass its `zig.exe` to `--zig`, set
`TONEMATCH_ZIG`, or run `build.ps1 -ZigPath C:\Tools\zig-0.15.2\zig.exe`.
The compiler is not redistributed in the portable ZIP. The developer archive
includes `native/` source/header, `native_dsp.py`, native tests, the build script,
and the DLL; Git tracks the sources, not the generated DLL. Do not substitute
a skipped-native test run for native release validation.

For an NVIDIA CUDA source build, run `enable_cuda.ps1` after the base environment
is working. It installs the pinned CUDA runtime from `requirements-cuda126.txt`;
then rerun the tests and `build.ps1`. The driver, PyTorch CUDA build, and GPU must
all be compatible. Auto mode otherwise falls back to CPU.

Read [DEVELOPER_HANDOFF_KO_EN.md](DEVELOPER_HANDOFF_KO_EN.md) and
[BUILD_HISTORY.md](BUILD_HISTORY.md) before continuing development.

## License and trademarks

Application source: MIT. Third-party licenses and binary notices are documented
in `THIRD_PARTY_NOTICES.txt`, `THIRD_PARTY_RUNTIME_INVENTORY.txt`, and `licenses/`.
Fender and Tone Master are trademarks of their respective owner. This project is
not affiliated with or endorsed by Fender Musical Instruments Corporation.
