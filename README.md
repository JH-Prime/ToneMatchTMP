# ToneMatch TMP 0.0.04

ToneMatch TMP is an unofficial, pre-release Windows desktop tool that analyzes a
local audio/video file or Windows playback capture, isolates the guitar stem,
and recommends three starting-point tone chains for Fender Tone Master Pro.
It also provides an experimental chord/voicing timeline. Version 0.0.04 adds
compute-device diagnostics and route-aware Amp/Cab recommendations.

한국어 설치·사용 안내는 [README_KO.md](README_KO.md)를 먼저 읽어 주세요.

## Current scope

- Korean/English UI with Malgun Gothic / Arial Narrow preferences
- Tone Master Pro firmware 1.8.58 and Model Guide Rev. J catalog
- Up to 20 minutes per analysis; `end = 0` means through the end, capped at 20 minutes
- Demucs `htdemucs_6s` guitar-stem isolation for full mixes
- Auto/CPU/CUDA compute preference with GPU, VRAM, inference-time, and real-time-factor diagnostics
- Windows WASAPI loopback/audio-input recording when no local file is available
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

The portable EXE ships with the CPU runtime for broad Windows compatibility.
CUDA is available only after installing the separate source-development CUDA
environment on a compatible NVIDIA PC. It was not hardware-validated on the
CPU-only release machine. C++ is reserved for a later real-time audio/ASIO
boundary; the current app and AI orchestration remain Python-based.

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
