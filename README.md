# ToneMatch TMP 0.0.06

ToneMatch TMP is an unofficial, pre-release Windows desktop tool that analyzes a
local audio/video file or Windows playback capture, isolates the guitar stem,
and recommends three starting-point tone chains for Fender Tone Master Pro.
It also provides an experimental chord/voicing timeline. Version 0.0.06 stores a
level-normalized spectrum from the analyzed guitar source and compares it with the
existing live Windows input or playback-loopback monitor. The release/build date
is 2026-09-07 KST. Version 0.0.05 introduced the live visual spectrum.

한국어 설치·사용 안내는 [README_KO.md](README_KO.md)를 먼저 읽어 주세요.

## Current scope

- Korean/English UI with Malgun Gothic / Arial Narrow preferences
- Tone Master Pro firmware 1.8.58 and Model Guide Rev. J catalog
- Up to 20 minutes per analysis; `end = 0` means through the end, capped at 20 minutes
- Demucs `htdemucs_6s` guitar-stem isolation for full mixes
- Visible stage-weighted analysis percentage and elapsed time, with actual model
  download bytes/file percentage and completed Demucs-block audio duration
- Auto/CPU/CUDA compute preference with GPU, VRAM, inference-time, and real-time-factor diagnostics
- Windows WASAPI loopback/audio-input recording when no local file is available
- Live raw-input waveform and logarithmic 20 Hz-20 kHz spectrum for the selected
  WASAPI input or playback loopback, with RMS/peak dBFS and spectral centroid
- A level-normalized reference spectrum from the analyzed local source or isolated
  guitar stem, compared against Current live input as Reference, Current, and delta
  (Current minus Reference) across six stable frequency bands
- Three ordered TMP recipes with output-route-specific Amp/Cab rules, plus JSON, HTML, and clipboard output
- Experimental chord, pitch-class, bass/inversion, register, spacing, and playable-candidate cues
- Native NumPy vector optimization for repeated chord/voicing spectrum work
- Clickable 11-stage developer diagram with bundled source, Korean docstrings, logs, and changelog
- Quad Cortex and Line 6 Helix are visible extension placeholders only

## Important boundaries

This app does not download or extract YouTube streams. Use a local file you may
analyze, or capture audio that is normally playing on your PC. It does not write
presets to Tone Master Pro and does not claim to recover the original rig, exact
DSP, or physical guitar fingering. Candidate shapes are suggestions, not detected
tablature.

The AI model weights are not committed or redistributed. The first full-mix
analysis downloads them to the current Windows user's Hugging Face cache.
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

The portable EXE ships with the CPU runtime for broad Windows compatibility.
CUDA is available only after installing the separate source-development CUDA
environment on a compatible NVIDIA PC. It was not hardware-validated on the
CPU-only release machine. C++ is reserved for a later real-time audio/ASIO
boundary; the current app and AI orchestration remain Python-based.

The v0.0.06 Reference Compare view reuses the v0.0.05 Python/NumPy live monitor.
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
percent meters, automatically derive EQ/TMP settings, or write a preset. Reference
URLs remain browser shortcuts and source records only. The monitor is WASAPI shared
mode, not C++, ASIO, WASAPI Exclusive, or a hard-real-time audio path.

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
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
& ..\.venv\Scripts\python.exe app.py --self-test-output .\self-test-v0.0.06.json
& ..\.venv\Scripts\python.exe app.py
```

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
