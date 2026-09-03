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
