# Privacy and local data / 개인정보와 로컬 데이터

ToneMatchTMP performs audio analysis, chord estimation, editing, mixing, and export
on the user's PC. Its analysis workflow does not upload the input audio to an analysis
service. Recordings, analysis results, settings, and logs are local files. Logs can
contain file paths and error details; review them before sharing them with maintainers.

## Network communication

- The portable Windows executable checks the project's public GitHub releases at
  startup unless launched with `--skip-update`. A newer release may be downloaded
  after its metadata is checked. GitHub and its asset hosts receive the request and
  normal connection information, including the IP address. A hash check is not a
  publisher signature. Store-packaged builds use Store-managed application updates.
- Instrument separation can download the documented model configuration and weights
  from Hugging Face when the user requests that feature and the local cache is missing.
  Those requests can disclose client/library metadata and connection information to
  the hosting service. Model weights stay in the user's cache and are not included
  in the application release. Cached operation does not require another model download.
- Opening a help or reference link launches the user's browser and is subject to
  that destination's privacy policy. There is no ToneMatchTMP account service or
  application-maintainer analytics endpoint in this release.
- Practice accompaniment prepares the question and synthesizes backing audio locally.
  The ChatGPT and Claude buttons open the chosen provider in your browser. You choose
  whether to paste and submit the copied question there. Practice projects and exported
  audio are written to destinations you select.

Third-party policies: [GitHub privacy](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement),
[Hugging Face privacy](https://huggingface.co/privacy),
[Microsoft privacy](https://privacy.microsoft.com/privacystatement).
These services operate independently of the project. Do not describe this program
as making no network requests: the portable startup update check is enabled by default.

## Storage and removal

Portable installations prefer the adjacent `data` folder, falling back to
`%LOCALAPPDATA%\ToneMatchTMP` when the installation location is not writable.
The updater keeps versioned copies under `%LOCALAPPDATA%\ToneMatchTMP\updates`.
Store builds use their package's per-user `LocalState` for settings, logs, captures,
and the generated Numba cache. Hugging Face has its own user cache, which may be
shared with other applications. Files explicitly exported by the user remain where
the user saved them.

To remove a portable installation, close it, preserve any wanted results and settings,
and delete its extracted application directory. Separately review its data and update
cache before deleting them. Do not remove a shared model cache without checking whether
another program uses it. Remove a Store installation through Windows installed-app
settings; separately saved exports remain the user's responsibility. The application
does not automatically delete private audio or earlier portable installations.

입력 음원과 분석 결과는 로컬에서 처리·저장합니다. 포터블 시작 업데이트는 GitHub에,
악기 분리의 최초 모델 다운로드는 Hugging Face에 연결됩니다. 로그를 공유하기 전에
경로·파일명 등 개인정보를 확인하세요. 사용자 음원은 빌드·서명·배포 파일에 포함하지 않습니다.
