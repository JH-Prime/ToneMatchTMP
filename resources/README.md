# FFmpeg runtime note

The Git repository does not track `ffmpeg.exe` because it is a large third-party
binary. The portable development ZIP contains the tested file at this location.

- File: `ffmpeg.exe`
- Build: `ffmpeg 9.0.1-essentials_build-www.gyan.dev`
- Size: `102,856,192` bytes
- SHA-256: `72A489ECCD008C2EC2C0A5856C5C75BC3D8BBFA90166C4566865C246445E6AA3`
- Upstream: <https://ffmpeg.org/>
- Windows build provider: <https://www.gyan.dev/ffmpeg/builds/>

Before a source run or PyInstaller build on a fresh Git clone, copy the tested
binary from the portable ZIP into `resources/ffmpeg.exe`, or supply a compatible
FFmpeg build and re-run the tests. See `licenses/FFmpeg-GPL-3.0.txt` and
`THIRD_PARTY_NOTICES.txt`.

# Native live DSP runtime

`tonematch_dsp.dll` is generated from `native/tonematch_dsp.cpp` and its C ABI 2
header. Git tracks the source, not the binary. The portable developer ZIP ships
the tested Windows x64 DLL both here and in the application's internal resources.
Run `tools/build_native.py --zig <path-to-Zig-0.15.2-zig.exe>` to rebuild it.
The release diagnostics record source/DLL SHA-256 hashes, compiler options,
native-versus-NumPy parity and a local DSP benchmark. Runtime notices are in
`licenses/native/`; ordinary portable EXE users do not need the compiler.

v0.0.09 adds `tm_dsp_push_f32` alongside the float64 input path and reports engine
accepted input frames, completed FFT windows and pending frames. The bridge
requires ABI 2: older ABI-1 DLLs fail strict C++ selection and trigger NumPy fallback
in automatic mode. Do not mix a new bridge with a DLL from an older release.
The direct float32 path removes the compatible input's Python float64 upcast;
it does not remove Python output copies, locks or SoundCard capture.

# Shared stem-removal resources

The Stem removal workspace introduced in v0.0.09 uses this same bundled FFmpeg for local
segment decoding. `stem_removal.py` mixes retained `htdemucs_6s` estimates into
one new 44.1 kHz stereo PCM16 WAV; it does not export individual stems.
The model's YAML and safetensors are acquired on first AI use and kept in the
Windows user's Hugging Face cache, shared with guitar isolation. Model weights,
input media, mixed output, and temporary audio are not release resources and must
not be added here or to the public archive. The build reference date is
2026-10-02 KST; current release checks are recorded in `QA_REPORT_v0.0.12.json`
and `BUILD_HISTORY.md` rather than inferred from the presence of these binaries.

v0.0.10 adds a CPU-only headless stem diagnostic in `stem_diagnostics.py`. It
uses only a complete local model cache and refuses missing/incomplete cache
without downloading. Diagnostic WAV output is temporary and deleted; its JSON
omits source/output filenames, source hashes and model paths. Neither test media
nor private model caches belong in this directory or release artifacts.

The v0.0.11 chord/evidence and input-UI update does not introduce a YouTube
extractor, new separation weights or a new native ABI. Verify this build's actual
artifacts separately; an unchanged binary is not evidence of completed release tests.

The v0.0.12 chord/scale reference is computed locally from note intervals. It adds
no model weights or network downloads, and does not change the C++ DSP ABI.
