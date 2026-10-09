# ToneMatch TMP 0.1.02

An unofficial Windows tool for authorized local audio/video and Windows capture:
whole-mixture chord charts plus three starting-point Fender Tone Master Pro or Quad Cortex recipes.
Build reference: 2026-10-09 KST. Unsigned CPU developer prerelease.
See [한국어 사용 안내](README_KO.md), [QA](QA_REPORT_v0.1.02.json) and [build history](BUILD_HISTORY.md).

## Added in 0.1.02

- Select **Chords only** to bypass guitar separation, AI downloads and modeler selection.
- Choose Quad Cortex and your CorOS version for three of six curated native starting points.
  Start at device defaults: numerical QC knob ranges are unverified, not copied from TMP.
  Older firmware may use the previous names shown in the catalog.
- Search the offline [official device list](https://neuraldsp.com/device-list) snapshot (2026-10-07):
  318 native, 164 factory Captures, 150 plugin and 57 announced entries. The 689-entry
  inventory is not 689 individually measured recipes; licensed and unreleased entries are excluded.
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
`ToneMatchTMP-v0.1.02.exe`. Do not move only the EXE.
Choose authorized local media or PC capture, then a range of 3 seconds to 20 minutes;
end `0` means through the end subject to that cap.
Full-mix tone analysis isolates guitar; already-guitar audio can skip isolation.
Chord input is always the selected original source. A separation failure can still stop the
overall tone workflow; there is no independent chord-only analysis button yet.

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
& ..\.venv\Scripts\python.exe -W error -m unittest discover -s tests -v
& ..\.venv\Scripts\python.exe app.py --self-test-output .\self-test-v0.1.02.json
& .\build.ps1 -ZigPath C:\Tools\zig-0.15.2\zig.exe
```

Official Zig 0.15.2 Windows x64 ZIP SHA-256:
`3a0ed1e8799a2f8ce2a6e6290a9ff22e6906f8227865911fb7ddedc3cc14cb0c`.
EXE users need no compiler. Optional CUDA source setup uses `enable_cuda.ps1` and requires
compatible hardware plus revalidation. Self-test covers CQT, corrections, mixer PCM/WAV,
PDF/font, PortAudio loading and native parity without audible output or actual model inference.
The separate `--stem-self-test-source` / `--stem-self-test-output` CLI checks an already
cached CPU model, writes redacted JSON and cleans temporary audio.

Post-publication fixes advance to 0.1.03; published releases are immutable.
Read [handoff](DEVELOPER_HANDOFF_KO_EN.md) and [research](TRANSCRIPTION_RESEARCH_KO.md).
Application source: MIT. See `THIRD_PARTY_NOTICES.txt`, inventory and `licenses/`.
Fender, Tone Master, Neural DSP and Quad Cortex are their owners' trademarks;
this project is not affiliated with or endorsed by Fender or Neural DSP.
