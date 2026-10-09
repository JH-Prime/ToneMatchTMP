# ToneMatch TMP — Build History / 빌드 이력

이 파일은 릴리스별 소스 범위, 검증 결과와 산출물 해시를 누적 기록합니다. 최신 항목을 위에 두고, 이미 배포한 버전의 날짜·해시는 수정하지 않습니다.

This append-only record tracks source scope, verification, and artifact hashes. Keep the newest entry first and never rewrite dates or hashes for an artifact that was already shared.

## 버전 요약 / Version Map

| 버전 | 상태 | 범위 |
|---|---|---|
| `0.1.02` | 소스·EXE 검증 완료, 압축 배포 별도 gate | Quad Cortex 목록·내장 추천, AI 독립 코드 모드, CQT 튜닝 보정 |
| `0.1.01` | 개발자 프리릴리스 검증 중 | 전체 음원 CQT 코드, 재생 연동·직접 수정, 6-stem 믹서·WAV, 16마디 PDF |
| `0.0.13` | 서명되지 않은 CPU 포터블 개발자 프리릴리스 | 16마디 코드표, 수동 격자 보정, 이론 기타 운지 확대, 긴 타임라인 보존 |
| `0.0.12` | 서명되지 않은 CPU 포터블 개발자 프리릴리스 | 41종 코드, 12종 음계·장조/자연단조 다이어토닉 사전, 12근음 건반 참고 |
| `0.0.11` | 서명되지 않은 CPU 포터블 개발자 프리릴리스 | 20종 코드 템플릿·모호성·구성음 근거·역위 보존, 참고용 YouTube UI 제거 |
| `0.0.10` | 서명되지 않은 CPU 포터블 개발자 프리릴리스 | 악기 제거 상태·경로 보호, 잘린 WAV 거부, CPU·로컬 캐시 전용 실제 모델 CLI 진단 |
| `0.0.09` | 서명되지 않은 CPU 포터블 개발자 프리릴리스 | 선택 악기 제거 도구와 C ABI 2 float32 직접 입력·실시간 DSP 진단 |
| `0.0.08` | 포터블 개발 프리뷰 빌드·검증 완료 | C++17 실시간 PCM·FFT·평활화 엔진, ABI 브리지와 NumPy 폴백 |
| `0.0.07` | 포터블 개발 프리뷰 빌드·검증 완료 | 코드 근거·원본 화성 참고·반응형 분석 UI |
| `0.0.06` | 포터블 개발 프리뷰 빌드·검증 완료 | Reference Compare, 실시간 분석 진행률, 콘솔 없는 EXE 모델 오류 수정 |
| `0.0.05` | 포터블 개발 프리뷰 빌드·검증 완료 | Windows 입력/loopback 실시간 파형·FFT 스펙트럼, bounded 최신 프레임 처리 |
| `0.0.04` | 포터블 개발 프리뷰 빌드·검증 완료 | 자동/CPU/CUDA 진단·벤치마크, NumPy 네이티브 최적화, 출력 경로별 Amp/Cab 체인 정정 |
| `0.0.03` | 포터블 개발 프리뷰 빌드 완료 | 포터블 개발 ZIP, 한·영 handoff, 로그·빌드 이력, NumPy 코드/보이싱 분석(실험) |
| `0.0.02` | 기능 통합 이정표, 0.0.03으로 승계 | 한국어/English, 장치 선택, 최대 20분, Demucs guitar stem, PC 재생음/입력 녹음, 취소 |
| `0.0.01` | 검증된 최초 비공개 프리뷰 | 짧은 로컬 오디오 DSP, TMP 추천 3개, JSON/HTML, 개발자 코드 뷰 |

## v0.1.02 — 2026-10-09 KST

Official inventory snapshot 2026-10-07: 689 entries, with native/capture/plugin/announced separation.
Six curated native QC templates, selected CorOS filtering, no fabricated numeric control values.
Independent original-mixture chord analysis bypasses AI; purpose-aware UI, loader, localization and HTML.
Bounded tuning consensus corrects 12 controlled detuned C/Am/Dsus4 cases; no classifier threshold weakening.
Room 335: 252.6099 seconds, 64 events, 0.1188 coverage, 11.715 seconds wall time.
30–90 second excerpt: 28 events, 0.2323 coverage, 2.097 seconds. Coverage unchanged from v0.1.01.
Progress/cancel, source preservation, JSON edit/reopen and HTML/PDF export passed.
Real-song accuracy is unmeasured. Archive verification is a separate required release gate.
Final warnings-as-errors suite: 376 tests passed in 174.624s. Eight catalog tests include
all listed firmware/output routes; unavailable optional Digital Delay is omitted with an explanation.
Synthetic comparison: all 246 primary labels retained by FFT and CQT, not a real-song accuracy test.
Native visual check covered the silent synthetic chord-only chart and offline inventory.
HTML content/export passed; browser visual check was blocked by the browser file-URL policy.
Frozen windowed EXE self-test passed: real CQT, detuned CQT, QC catalog/recipes, chord-only
decode/JSON reopen, edits, PCM reader, mixer export, PDF font and PortAudio loading.
C++ ABI 2 / float32 parity passed. Optional-library build warnings are retained in the sanitized log.
EXE SHA256: `D93F511D5C1C1651BE56AA36DE3237CE0127D8D293DA636AE9D346D62AA8F284`.
The release must include `ToneMatchTMP-v0.1.02-ARCHIVE-VERIFICATION.json` with a successful
fresh-extract run and matching ZIP digest; ZIP hashes are external to avoid self-referential manifests.

## 0.1.01 — Full-mixture CQT and music workflow

- Build reference: 2026-10-06 KST. Final verification continued 2026-10-07 KST.
- Status: unsigned CPU developer prerelease candidate; publication follows independent archive verification.
- Whole original mixture CQT; symbols/evidence/alternatives instead of automatic fingering.
- Playback/seek/loop with chart following, separate manual corrections and safe JSON reopen.
- Six-stem disk-backed mixer, original monitoring and safe individual/mix PCM16 WAV export.
- A4 sixteen-bar PDF, embedded Korean font, dense-event detail pages, explicit viewer-only preview.
- Nine KO/EN synthetic PDF pages visually reviewed. Source music self-test passed.
- Final warnings-as-errors suite: 358 tests, 201.559s, OK. Frozen music/C++ self-test passed.
- 80 source/build inputs in the staged package match the project.
- Actual source CQT/mixer: 252.6099-second sample, six individual and one mix WAV with
  11,140,096 aligned stereo PCM16 frames each. Original unchanged; temp cleanup and real
  inference cancellation passed. CQT 10.870s, mixer prepare 100.867s on this cached CPU run.
- CQT returned 64 events and 0.1188 reliable-window coverage, NOT an accuracy measurement.
- Repaired cancellation exception normalization and SciPy's dynamic FFT-module packaging.
- Final windowed EXE actual cached CPU run: whole 252.6099-second sample in 98.417s,
  nine chunks, 238 monotonic progress callbacks; requested cancellation in 10.210s.
  Original preserved, temporary audio and partial outputs cleaned, no model download.
- EXE SHA-256: `085324080936D8C18D6F590F1A72300241BA56A4F0ACAEE951A56A85E959CB6D`.
- Final ZIP digest belongs to the sibling SHA256SUMS and independent ARCHIVE-VERIFICATION
  release asset; it is intentionally not embedded in its own bytes.
- 246 controlled synthetic labels matched by both FFT and CQT; no real-song accuracy claim.
- Final suite, frozen execution, actual cached model and archive proof: see QA_REPORT_v0.1.01.json.
- No audible output, perceptual separation improvement, physical printing, first download,
  clean-machine, offline, CUDA or signing claim. Later published fixes use 0.1.02.

## 0.0.13 — 16-bar chord chart and theoretical guitar shapes

- 빌드 기준일 / Build reference date: `2026-10-04 KST`
- 최종 검증일 / Final verification: `2026-10-05 KST`
- 상태 / Status: `UNSIGNED CPU PORTABLE DEVELOPER PRERELEASE`
- Four bars per row, sixteen per page, source labels, explicit unknown spans,
  every within-bar change, continuations and pickup/pre-roll preserved.
- Editable constant-tempo BPM, beats per bar and first-downbeat offset. This is
  a manual guide, not automatic beat/downbeat transcription.
- Existing 41 audio templates retained. Standard EADGBE theoretical suggestions
  expanded from six legacy families to 38 qualities × 12 roots. Seven-tone
  13/maj13/min13 cannot fit six strings and deliberately have no complete shape.
- Original-mix results continue to suppress guitar shapes and slash-bass claims.
- Default event cap 96→4096 preserves already detected long-song events; local
  acoustic classification thresholds and temporal evidence are unchanged.
- Algorithm research and proposed ground-truth evaluation:
  `TRANSCRIPTION_RESEARCH_KO.md`. No NNLS or neural transcription engine bundled.
- Chart-only header compaction, dynamic label spacing, wrapped beat labels and
  collapsible grid controls preserve the viewport in small high-DPI windows.
- Applied grid settings are saved in JSON; HTML/clipboard retain the full text
  timeline rather than paged sheet export.

### 검증 / Verification

- 316 automated tests passed with `-W error` in 128.775 seconds; compileall passed.
- Source/final EXE self-tests passed for 41 templates, theory, chart pagination,
  unknown/source guards, theoretical shapes, Reference Compare and C++ ABI 2.
- Eight new hidden Tk chart tests passed: KO/EN, 960×600/1080×720, 120/150%
  scaling, expanded/collapsed settings, page/language state and header restoration.
- Shape checks cover all 492 root/quality pairs: 456 complete theoretical shapes
  supported and 36 seven-tone combinations deliberately omitted. Search agrees
  with independent exhaustive enumeration for the tested control.
- Synthetic baseline v0.0.12/current: both 984/984 expected primary labels and
  all 36 negative controls rejected, 109.068 seconds. No accuracy gain claimed.
- Actual 252.61-second Room 335 source smoke: 138.630 seconds including baseline
  comparison, 75 monotonic updates to 100%, cache only and source unchanged.
  Weak guitar selected original-mix harmony, whose 165 events (107 known/58 unknown)
  are all retained versus the former 96-event cap. Window coverage remains .3587.
- Actual-result hidden UI: 165 event indexes and durations preserved in both
  languages, 188 manual-grid bars/12 pages/352 displayed segments, no mix guitar
  shapes. The default 178 BPM is a rough hint, not ground-truth tempo/downbeats.
- October 5 final EXE full-song removal: 252.6099 seconds, nine chunks,
  11,140,096 frames stereo 44.1 kHz PCM16, 154.076 seconds elapsed, 238 monotonic
  updates to 100%, no download. Gain .9171751788 avoids clipping. Source unchanged
  and temporary/partial audio cleaned. Timings are not speedup claims.
- Final EXE cancellation: 31-second selection, requested at 60%, observed at
  61.12684%, 22.074 seconds elapsed; no output/partial files, source unchanged.
- Fresh extraction: 4,503 manifest files, 56 matching source/build inputs,
  AMD64 PE32+ DLL and native licenses, new EXE self-test, model/user-audio absence
  and private-path checks passed. Final QA/docs are repackaged and checked again
  before publication; no unchanged source retesting is used as substitute evidence.
- Manual visible GUI inspection/listening, first download, OS network-disabled
  execution, CUDA, physical capture and signing are not verified.

### 산출물 / Artifacts

- EXE: `ToneMatchTMP-v0.0.13.exe`, 39,616,911 bytes.
- EXE SHA-256: `3AB4D75E4FF2C329D45ED3BE3E9CAD17E113400B07D69A1515CA1798D39161C0`.
- ABI-2 DLL: 350,720 bytes; SHA-256
  `F4D129C73AB015799780B2281909CBB0B793F640655D531E52D851A769854EE5`.
- ZIP: `ToneMatchTMP-v0.0.13-Windows-x64-Portable-Dev.zip`.
  Its final hash is in the sibling `ToneMatchTMP-v0.0.13-SHA256SUMS.txt`;
  `MANIFEST.json` covers internal files without circular ZIP hashes.
- Prior v0.0.12 results below remain historical and were not reused.

## 0.0.12 — Expanded chord vocabulary and keyboard theory guide

- 동결 빌드일 / Frozen build date: `2026-10-02 KST`
- 최종 릴리스 검증일 / Final release verification: `2026-10-03 KST`
- 상태 / Status: `UNSIGNED CPU PORTABLE DEVELOPER PRERELEASE`
- Scope: 20→41 audio chord templates; 12-root chord/scale guide with 41 chord
  qualities, 12 scales/modes, and major/natural-minor diatonic triads and sevenths.
- The third outer workspace tab works without audio. Its keyboard preserves
  compound 9th/11th/13th intervals and degree-aware enharmonic spelling.
- Pentatonic scales and diatonic harmony are reference theory, not additional
  chord qualities or automatic audio key/scale detection.
- Full listed-tone evidence is required; omitted-tone/rootless extended chord
  names are not inferred. Ambiguity, unknown spans and original-mix safeguards
  remain. A terminal slash bass is removed without truncating 6/9.
- Temporal tracking separates absolute local-evidence candidates from near-score
  displayed alternatives. Unsupported candidates are pruned before path selection,
  followed by a final adjacent-label check. No neighbor-tone copying or minimum-evidence
  threshold relaxation; broader retention still does not establish correct transcription.

### 검증 / Verification

- 282 automated tests passed with `-W error` in 134.432 seconds; compileall passed.
- Source and final EXE self-tests passed: 41 chord templates, new suspended/extended
  chords, ambiguity, single-note rejection, actual theory calculations (41/12/2 ×
  12 roots), enharmonic spelling, Reference Compare, developer source and C++ ABI 2 parity.
- Fixed independent synthetic comparison: 984 cases (41 qualities × 12 roots ×
  two textures), v0.0.11 primary matches 480/984 → v0.0.12 984/984.
  All 36 negative controls rejected in both versions; elapsed 109.182 seconds.
  This is not measured real-song accuracy or proof of detected fingering.
- Actual Room 335, 252.61 seconds: comparison-inclusive source run 122.245 seconds,
  75 monotonic progress updates to 100%, source unchanged, local model cache only.
  Weak guitar (-63.246 dBFS) selected original-mix harmony.
  Support is 151/421 windows (35.87%) before display limiting, versus 68/421 in
  v0.0.11. This is coverage, not accuracy. The timeline is limited from 165 to
  96 events (50 known / 46 unknown); omitted candidates become unknown without time gaps.
  Many intervals remain unknown, and retained candidates may still be wrong.
- Final EXE real-model removal: 252.6099 seconds / 11,140,096 frames, nine chunks,
  118.817 seconds elapsed, 238 monotonic progress updates to 100%, no model download.
  Output checked as stereo 44.1 kHz PCM16; normalization gain 0.91717518; source
  preserved and temporary/partial audio cleaned. Timings are not a speedup or quality claim.
- Final EXE cancellation: 31-second selection, requested at 60%, observed at
  61.12684%, 10.092 seconds elapsed; cancelled output absent, source unchanged
  and temporary/partial files cleaned.
- Staged source-input verification: all 51 inputs and bundled developer code match;
  native DLL/source/imports/licenses and actual ABI 2 agree.
- Fresh extraction verified all 4493 manifest entries, 51 matching source
  inputs, native DLL/imports/licenses, absence of audio/weights/private build-log
  paths, and a new EXE self-test. Final docs are repackaged and independently
  verified again before publication.

### 산출물 / Artifacts

- EXE: `ToneMatchTMP-v0.0.12.exe`, 39,565,178 bytes
- EXE SHA-256: `46E38E5259C0722D3CC2CCA8A852F45EE293E70E6FD1EFB89299823E4544A0DD`
- Native DLL: 350,720 bytes, ABI 2; SHA-256 `F4D129C73AB015799780B2281909CBB0B793F640655D531E52D851A769854EE5`
- ZIP: `ToneMatchTMP-v0.0.12-Windows-x64-Portable-Dev.zip`; final ZIP hash belongs
  in external `ToneMatchTMP-v0.0.12-SHA256SUMS.txt`, not inside the archive itself.
- Includes privacy-safe synthetic/actual-input chord checks and final EXE
  stem-completion/cancellation JSON. No user audio or model weights.
- Comparative benchmark requires a Git checkout with tag `v0.0.11`:
  `python tools/benchmark_voicing.py --output NEW.json`.

Manual visible GUI/listening, physical capture, first download, OS-network-blocked
operation, CUDA and code signing remain unverified. Evidence is not a calibrated
probability; theoretical keyboard layouts and candidate shapes are not detected fingering.

## 0.0.11 — Extended chord evidence and input cleanup

- 동결 빌드일 / Frozen build date: `2026-09-30 KST`
- 최종 릴리스 검증일 / Final release verification: `2026-10-01 KST`
- 상태 / Status: `UNSIGNED CPU PORTABLE DEVELOPER PRERELEASE`
- 범위 / Scope: 9→20 chord qualities, coverage/complexity scoring, ambiguous alternatives,
  observed vs template tones, preserved bass-change intervals, and removal of the reference-only YouTube controls.

### 검증 / Verification

- 251 automated tests passed with `-W error` in 66.031 seconds; compileall passed.
- Source and packaged EXE self-tests passed: C9 and observed evidence, C6/Am7 ambiguity,
  single-note rejection, Reference Compare, developer source and actual C++ ABI 2 parity.
- Fixed synthetic comparison: 480 cases (20 qualities × 12 roots × 2 textures),
  expected primary label matches v0.0.10 **186/480** → v0.0.11 **480/480**;
  all 36 single-note/nonchord/noise controls rejected in both versions. This is **not real-song accuracy**.
- Actual Room 335, 252.61 seconds: comparison-inclusive source run 139.417 seconds,
  75 monotonic progress updates to 100%, source unchanged, local model cache only.
  Weak guitar (-63.246 dBFS) selected original-mix harmony. Support is **68/421 windows (16.15%)**,
  with 43 known and 33 unknown events. Many intervals remain unknown. No ground-truth accuracy claim.
- Final EXE real-model stem removal: 252.6099 seconds / 11,140,096 frames, nine chunks,
  123.557 seconds elapsed, 238 monotonic progress updates to 100%, no model download.
  Output checked as stereo 44.1 kHz PCM16; normalization gain 0.91717518; source preserved,
  temporary/partial audio cleaned. These timings do not establish a speedup or listening quality.
- Final EXE cancellation: 31-second selection, requested at 60%, observed at 61.12684%,
  11.370 seconds elapsed; cancelled output absent, source unchanged and temporary/partial files cleaned.
- Fresh-extract checks verify every manifest entry, matching source/devsource, native DLL/imports/licenses,
  a new EXE self-test, and absence of user audio/model weights/private paths in public build logs.
  Final documentation is repackaged and checked again before publication.

### 산출물 / Artifacts

- EXE: `ToneMatchTMP-v0.0.11.exe`, 39,526,707 bytes
- EXE SHA-256: `44EF7D901B29F2253A0D65E095E8D5159F874FFDEB51470029EA23AC7503392F`
- Native DLL: 350,720 bytes, ABI 2; SHA-256 `F4D129C73AB015799780B2281909CBB0B793F640655D531E52D851A769854EE5`
- ZIP: `ToneMatchTMP-v0.0.11-Windows-x64-Portable-Dev.zip`; final archive hash is in the
  external `ToneMatchTMP-v0.0.11-SHA256SUMS.txt` release asset, avoiding a self-containing hash.
- Package includes privacy-safe synthetic/real-input chord checks and packaged stem completion/cancellation JSON.
- Reproduce the comparative synthetic check from a Git checkout containing tag `v0.0.10` with
  `python tools/benchmark_voicing.py --output NEW.json`; the portable source copy alone has no Git history.

Manual GUI/listening, physical capture, first model download, OS-network-blocked operation,
CUDA and signing remain unverified. Chord evidence scores are not calibrated probabilities;
candidate shapes do not identify performed strings/frets. No automatic YouTube extraction was added.

## 0.0.10 — Stem-removal reliability and headless model diagnostics

- 작업일 / Work dates: `2026-09-20–30 KST`; frozen build reference date: `2026-09-20 KST`
- 최종 릴리스 검증일 / Final release verification date: `2026-09-30 KST`
- 상태 / Status: `UNSIGNED CPU PORTABLE DEVELOPER PRERELEASE — validation limits below`
- 기반 / Based on: v0.0.09 selective stem removal and native DSP ABI 2

### 이 버전에 속하는 변경 / Changes owned by this version

- 새 악기 제거 입력을 선택하면 이전 결과·진행률·경과 상태를 초기화
- 기본 출력 이름 선택·UI 실행 전 검증에서 끊어진 심볼릭 링크도 이미 존재하는
  항목으로 보호해 저장 계층의 비덮어쓰기 계약과 일치
- 기타 분리에서 WAV 헤더보다 짧은 PCM payload를 거부하고 실패 시 중간 파일 정리
- `stem_diagnostics.py`와 별도 `--stem-self-test-source PATH`,
  `--stem-self-test-output JSON` CLI로 GUI 없이 실제 CPU 모델의 기타+피아노
  제거·진행률·원본 보존·출력 형식·정리를 검사
- `--stem-self-test-seconds 0`은 전체 음원(최대 20분), 선택적
  `--stem-self-test-cancel-at PERCENT`는 실제 보고 진행률에서 취소 요청
- 완전한 로컬 모델 캐시만 허용하며 없거나 불완전하면 다운로드 없이 실패
- 진단용 WAV는 검사 뒤 삭제; `tonematch-stem-self-test/v1` JSON은
  파일명·소스 해시·모델 경로를 제외하고 기존 JSON은 덮어쓰지 않음
- 기존 악기 제거·C ABI 2 float32·실시간 DSP 표시·톤/Reference/코드 분석 계약 유지

### 검증 경계 / Verification boundary

GUI 없는 실제 모델 진단과 수동 UI·청감 검증은 구분합니다. 새 모델 또는 분리 품질
개선이 아니며 AI 누출·빠진 소리·잔향·왜곡은 여전히 발생할 수 있습니다.
기존 v0.0.09 테스트·음원·성능 결과는 아래 역사 섹션에만 보존하며 새 통과로
간주하지 않습니다. 음원·출력·모델 가중치·원시 로그는 로컬에 남고 배포하지 않습니다.

The headless diagnostic uses the real CPU model from a complete local cache.
It does not establish manual GUI quality, listening quality, first-download,
network-disabled application use, CUDA hardware or live-capture behavior.
Cancellation can be delayed by an active inference block. No new separation
model, C++ device-I/O migration or hard-real-time guarantee is introduced.

### 릴리스 게이트 결과 / Release gate result

- [x] 전체 자동 테스트·compileall — `PASS`: 소스 검사와 최종 빌드 검사 모두
  234개 통과; 최종 빌드 테스트 `68.497 s`, `-W error`
- [x] 실제 ABI 2 float32/float64 비교·진단·벤치마크 — `PASS`: 30개 창,
  양 경로 parity·stream stats·reset 통과; 최대 spectrum 차이
  `2.1316282072803006e-14 dB`
- [x] 실제 CPU 모델 소스 제거·취소 진단 — `PASS`: 아래 측정 범위 참조
- [x] 소스·최종 EXE 일반 자체 진단 — `PASS`
- [x] 최종 EXE 실제 모델 전체 곡 제거·취소 진단 — `PASS`: 아래 측정 범위 참조
- [x] 새 ZIP manifest·소스·DLL·고지·해시·개인 데이터 제외 검사 — `PASS`:
  `2026-09-30` 새 압축 해제에서 4,485개 manifest 항목과 46개 소스 입력의 일치,
  실제 ABI 2 DLL과 고지, 사용자 음원·모델 가중치·개인 경로 제외,
  새 압축 해제 EXE 자체 진단을 확인했습니다. 이 완료 기록을 반영한 ZIP도
  동일 검사에 다시 통과한 뒤 게시합니다.
- [ ] 전체 곡 수동 GUI·청감 품질·첫 모델 다운로드·네트워크 차단 실행·CUDA·
  실제 마이크/loopback 캡처·코드 서명 — `NOT RUN`

### 이번 버전의 실제 측정 / Measurements from this version

- 소스 실제 모델 검사: 31초, 2조각, 진행률 39회; 총 `30.8685812 s`,
  추론 `24.9144687 s`. 다른 테스트가 동시에 실행된 부하 조건입니다.
- 소스 취소: 31초 범위에서 진행률 60% 기준으로 요청, 관측
  `61.1268387%`, 총 `16.3702098 s`; 원본 보존·중간 파일 정리·출력 부재 통과.
- 최종 패키지 EXE 전체 곡: `252.6098866 s`, 9조각, 단조 증가 진행률 238회와
  최종 100%; `11,140,096 frames`, 44,100 Hz stereo PCM16, 출력 peak `32,734`.
  총 `140.8733689 s`, 추론 `134.4898491 s`; 합산 peak `1.0892139507`에
  전 구간 동일 gain `0.9171751788`을 적용했습니다. 기타+피아노 제거를
  실제 CPU 모델로 수행했고 원본 보존과 임시 파일 정리를 확인했습니다.
- 최종 패키지 취소: 31초 범위에서 60% 기준으로 요청, 관측 `61.1268387%`,
  총 `11.9191346 s`; 출력·임시 파일 부재와 원본 보존 통과.
- 위 모델 검사는 완전한 기존 로컬 캐시만 사용했습니다. 다운로드가 없었다는
  사실은 OS 네트워크를 차단해 검증했다는 뜻이 아닙니다. 청감 품질을 평가하지
  않았으며 입력·출력 오디오는 배포에 포함하지 않습니다.
- 이 빌드의 DSP push 벤치마크: C++ float32 `0.1557 ms`, NumPy `0.6892 ms`
  (비율 `4.42646`), 같은 DLL의 float64 변환 대조군 `0.1622 ms`.
  캡처·UI·AI·오프라인 분석 시간은 제외합니다. 네이티브 소스와 DLL은 v0.0.09와
  같으므로 새 C++ 구현이나 버전 간 속도 개선의 근거가 아닙니다.

### 최종 산출물 기록 / Final artifact record

완료된 검사 결과는 `QA_REPORT_v0.0.10.json`에 기록합니다.
ZIP 최종 해시는 `ToneMatchTMP-v0.0.10-SHA256SUMS.txt`, 내부 파일별 크기·해시는
`MANIFEST.json`이 기준이며 새 압축 해제 검사를 통과한 바이트만 게시합니다.

## 0.0.09 — Selective stem removal and native DSP ABI 2

- 작업일 / Work dates: `2026-09-13–19 KST`; build reference date: `2026-09-19 KST`
- 상태 / Status: `UNSIGNED CPU PORTABLE DEVELOPER PRERELEASE — validation limits below`
- 기반 / Based on: v0.0.08 C++ live DSP engine migration

### 이 버전에 속하는 변경 / Changes owned by this version

- C ABI 2의 `tm_dsp_push_f32` 입력 추가, 기존 float64 `tm_dsp_push` 경로 유지
- 정렬된 native-endian C-contiguous float32 입력에서 Python float64 upcast 복사 제거
- 엔진이 수락한 `input_frames`, `completed_windows`, `pending_frames` 진단과 reset 초기화
- 실시간 화면에 DSP push ms·완성 FFT 창·잔여 frame 표시, 실제 C++/NumPy 백엔드 구분 유지
- 예전 ABI 1 DLL은 strict C++ 선택에서 오류, 자동 선택에서는 사유와 함께 NumPy 폴백
- 바깥쪽 `톤 분석 / Tone analysis`와 `악기 제거 / Stem removal` 작업 탭을 분리
- 별도 악기 제거 도구에서 로컬 오디오·영상의 `vocals`, `drums`,
  `bass`, `guitar`, `piano`, `other` 가운데 1~5개를 선택해 제거
- `stem_removal.py`가 Demucs `htdemucs_6s`의 나머지 stem을 조각별로 합산하고 새
  44.1 kHz stereo PCM16 WAV로 확정 저장; 원본과 이미 존재하는 출력은 비덮어쓰기
- Windows에서 같은 폴더의 완성 partial을 비덮어쓰기 `os.rename`으로 확정해
  처리 도중 생성된 출력 파일도 보호; 합산 peak가 1을 넘을 때만 전 구간 동일 감쇠 적용
- 최소 3초·최대 20분 구간, 자동/CPU/CUDA 선택, 실제 모델 다운로드/캐시 상태와
  내부 처리 기반 진행률·경과 시간·취소, 작업 중 다른 오디오 작업과의 상호 배타 처리
- 개별 stem은 저장하지 않고 임시 디코딩·float mix·부분 출력은 완료/오류/취소 뒤 정리
- 기존 톤 분석, Python/Tk UI와 SoundCard/WASAPI 공유 캡처 계약 유지

### 검증 경계 / Verification boundary

입력 변환 한 경로를 줄인 것이며 Python 출력 복사·잠금·필요한 입력 정규화는 남습니다.
전체 zero-copy, C++ 장치 콜백, ASIO/독점 모드 또는 하드 실시간 구현을 뜻하지 않습니다.
DSP push 시간은 처리 호출만 측정하며 캡처·AI·UI 그리기·오디오 왕복 지연이 아닙니다.
이전 v0.0.08의 테스트·MP3·성능 결과는 역사 기록으로만 보존하고 이번 검증으로 재사용하지 않습니다.

악기 제거는 Logic Pro의 Stem Splitter와 비슷한 사용자 흐름을 지향한 로컬 보조
기능이지 Apple Logic Pro와 동일한 모델·품질·분류를 구현했다는 뜻이 아닙니다.
Demucs가 추정한 stem에는 다른 악기 누출, 위상·어택·잔향 변화와 인공음이 생길 수
있습니다. 사용자 음원과 출력은 로컬에 머물고 모델 준비 때만 네트워크를 사용합니다.

The float32 fast path removes the compatible input's Python float64 upcast, not
all copying or synchronization. DSP push time excludes capture, AI, UI drawing
and audio round-trip latency. Any performance result must identify this version,
the tested machine, input layout and workload. User audio and private logs stay local.

### 릴리스 게이트 결과 / Release gate result

- [x] `2026-09-14` 사전 확인: 제공 Room 335 음원의 0~3초 CPU 악기 제거 smoke — guitar+piano 제거,
  1 chunk, inference `3.476 s`, 44.1 kHz stereo PCM16 `529,244` bytes,
  peak `0.696726`, normalization `false`, 남은 partial 파일 없음
  (아래 31초 검증에 앞선 초기 기능 확인)
- [x] `2026-09-16` 실제 CPU 소스 검증: Room 335의 0~31초 guitar+piano 제거,
  2 chunks, 진행률 `39`회 단조 증가, inference `13.650 s`, 전체 `17.217 s`,
  44.1 kHz stereo PCM16 `1,367,100` frames. 합산 peak `1.045119`에서
  전 구간 gain `0.955872`를 적용해 출력 peak `32,734`로 정규화
- [x] 같은 소스 검증에서 원본 보존, 실제 추론 취소, 취소 후 출력·부분 파일 없음 확인;
  사용자 음원 업로드와 청감 품질 평가는 수행하지 않음
- [x] `2026-09-19` 전체 자동 테스트 `214 tests`, `48.577 s`, warnings-as-errors,
  compileall 통과
- [x] 실제 ABI 2 DLL의 float32/float64 경로 각 `15`개, 총 `30`개 창 비교 통과;
  최대 스펙트럼 오차 `2.1316e-14 dB`, stream stats·reset 통과.
  분할 입력·오류·폴백 회귀는 위 자동 테스트에 포함
- [x] 소스 자체 진단 통과: C++ ABI 2 float32/float64 parity, stream stats/reset,
  추천 `3`개, Reference `6`밴드, 개발자 소스 `11`개와 악기 제거 소스 포함
- [x] 이번 버전으로 제공 MP3 `252.61초`의 완성 FFT 창 `5,439개` 비교 통과;
  float32 직접 입력·카운터 확인, 최대 스펙트럼 오차 `1.2513e-10 dB`
- [x] `2026-09-19` 44.1 kHz·2채널·2,048-frame float32 DSP push 측정:
  C++ 중앙값 `0.1482 ms`, NumPy `0.65745 ms`, 약 `4.44배`; 경로별 `2,560`회,
  순서 교대와 warmup 포함. 동일 ABI 2의 float64 변환 대조군은 `0.1536 ms`이며
  v0.0.08 바이너리와의 비교가 아님. 호환 입력에서 push당 `32,768 bytes` 변환 할당 제거
- [x] 패키지 EXE 자체 진단 통과; 실제 C++ ABI 2 경로 확인
- [x] 숨김 Tk 자동 회귀에서 한·영 DSP 표시·작은 창 및 악기 제거 UI 검증 통과;
  1~5개 선택·20분 경계·취소·비덮어쓰기·임시 파일 정리는 자동 테스트에 포함
- [x] 패키지 GUI 실행과 악기 제거 탭 열기 확인; 해당 GUI에서 제거 작업은 실행하지 않음
- [ ] 전체 곡 패키지 UI end-to-end — `NOT RUN`: 사용자 Escape 요청으로 검증을
  중단했으며 자동 UI 회귀·소스 31초 추론·EXE 자체 진단으로 이를 대체하지 않음
- [ ] 첫 모델 다운로드, 네트워크 차단 실행, 실제 마이크/loopback 캡처·왕복 지연,
  CUDA 장치, 청감 품질, 코드 서명 — `NOT TESTED`

초기 ZIP의 manifest·소스·native 확인 뒤 최신 README와 staging 사본의 불일치를
발견해 문서와 QA를 다시 반영했습니다. 최종 게시 조건은 새 ZIP의 manifest·동일 소스·
DLL·고지·SHA-256·사용자 데이터 제외와 새 압축 해제 EXE 자체 진단 재검증입니다.
그 결과는 `QA_REPORT_v0.0.09.json`에 기록하며, 위 미실행 항목을 통과로 표시하지 않습니다.

### 최종 산출물 기록 / Final artifact record

배포 ZIP의 최종 해시는 ZIP 옆
`ToneMatchTMP-v0.0.09-SHA256SUMS.txt`, 내부 각 파일은 `MANIFEST.json`이 기준입니다.
`diagnostics/native-build.json`의 ABI·소스/DLL 해시와 `native-verification.json`의
수치 비교·측정값이 동일 빌드에 속하는지 확인한 뒤 업로드합니다.

## 0.0.08 — C++ live DSP engine migration

- 작업일 / Work dates: `2026-09-08–11 KST`; build date: `2026-09-10 KST`; final validation: `2026-09-11 KST`
- 상태 / Status: `BUILT AND VERIFIED — unsigned CPU portable developer preview`
- 기반 / Based on: v0.0.07 chord evidence and responsive analysis layout

### 이 버전에 속하는 변경 / Changes owned by this version

- 실시간 PCM 고정 누적 버퍼, 채널별 Hann FFT, 최근 4프레임 선형 파워 평활화를 C++17로 분리
- C ABI 1 및 ctypes로 DLL 호환성·타입·컨텍스트 수명·동시 종료를 관리
- 임의 길이 입력의 완성 FFT 창을 모두 처리하고 미완성 입력은 다음 블록까지 보존; 중지·reset에서는 폐기
- 역상 스테레오, NaN/Inf, 표시 하한, Nyquist와 출력 소유권에 대한 NumPy 기준 경로 비교
- 실제 C++/NumPy 선택과 폴백 사유를 기존 파형 제목 행에 한·영으로 표시
- 단일 SoundCard 캡처와 최신 프레임 1개 큐 유지; Python UI·AI·오프라인 분석·레시피·코드 분석은 그대로 유지
- 명시적으로 지정한 Zig 0.15.2 C++ 도구의 재빌드 경로, DLL/원본 C++/헤더/브리지/테스트/런타임 고지 배포
- 릴리스 빌드와 EXE 자체 진단은 실제 C++ 수치 검증을 요구하며 NumPy 폴백 통과로 대체하지 않음

### 검증 경계 / Verification boundary

이번 전환은 실시간 DSP 연산 구간입니다. C++ 장치 입출력, ASIO, WASAPI Exclusive,
하드 실시간 보장, 새로운 실시간 톤 특징/Match % 미터나 기기 프리셋 쓰기는 포함하지 않습니다.
Python 복사·잠금과 공유 모드 캡처가 남아 있으므로 DSP 처리 시간은 오디오 왕복 지연이 아닙니다.
파일·AI 분리는 그대로이며 DSP 벤치마크를 Demucs 또는 전체 곡 분석의 가속으로 표현하지 않습니다.

The native benchmark compares identical float32 PCM pushes, including the Python bridge,
FFT and smoothing, but excludes capture, GUI, AI and offline analysis. It is a local
measurement, not a latency guarantee. Native parity uses the existing NumPy reference.
User audio, stems and private analysis logs stay local and are excluded from public artifacts.

### 릴리스 게이트 결과 / Release gate result

- [x] Python 3.12 전체 자동 테스트 `162 tests`, warnings-as-errors, compileall 통과; native 건너뜀 0개
- [x] 실제 DLL C ABI·수치·수명·출력 버퍼 검증 24개, 앱 통합·한영 표시·최소 창 회귀 17개
- [x] 독립 읽기 검토에서 릴리스 차단 문제 없음; 추가 9개 설정·18개 출력의 NumPy 수치 비교 통과
- [x] 소스·패키지·새 압축 해제 EXE 자체 진단: 실제 C++ ABI 1·parity, 추천 3개, Reference 6밴드, 개발자 블록 11개
- [x] 사용자 제공 252.61초 MP3의 완성 FFT 창 `5,439개` 비교 통과; 최대 스펙트럼 오차 `1.2513e-10 dB`
- [x] 동일 44.1 kHz·2채널·2,048-frame float32 DSP push 벤치마크: C++ 중앙값 `0.1494 ms`, NumPy `0.6513 ms`, 약 `4.36배`; 각 2,560회, 교차 순서·warmup 포함
- [x] 실제 EXE의 Room 335 전체 AI 분석 완료 `01:45` / 재실행 `01:47`, 모델 캐시 재사용, 수치 진행·JSON 저장 성공
- [x] 실제 EXE 960×600 클라이언트 / 962×632 캡처 창에서 완료 footer·입력 스크롤·긴 저장 경로 상태 유지
- [x] 저장한 코드 JSON이 v0.0.07 EXE 결과와 정확히 일치; 원본 믹스 화성 참고 73개 타임라인, 정확도 주장은 없음
- [x] 새 ZIP의 manifest `4,476개`, 소스 입력 `41개`, DLL·C++/헤더·런타임 고지·SHA-256 일치; 음원·모델 가중치·공개 로그 개인 경로 없음
- [ ] 실제 마이크/loopback 캡처·왕복 지연, CUDA 장치, 네트워크 차단 실행, 코드 서명 — `NOT TESTED`

최종 문서 반영 뒤에도 새 압축 해제와 자체 진단을 반복합니다. 위 DSP 벤치마크는
AI/전체 곡 분석 또는 오디오 지연의 가속 결과가 아닙니다. 상세 결과는 `QA_REPORT_v0.0.08.json`에 기록합니다.

### 최종 산출물 기록 / Final artifact record

최종 해시는 ZIP 옆 `ToneMatchTMP-v0.0.08-SHA256SUMS.txt`가 기준이며 개별 파일은
`MANIFEST.json`으로 확인합니다. `diagnostics/native-build.json`에는 컴파일러 버전·옵션·
C++ 소스 해시·DLL 해시를, `native-verification.json`에는 수치 비교와 벤치마크를 기록합니다.

## 0.0.07 — Chord evidence and responsive analysis layout

- 작업일 / Work date: `2026-09-08 KST`
- 상태 / Status: `BUILT AND VERIFIED — unsigned CPU portable developer preview`
- 기반 / Based on: v0.0.06 analysis progress and Reference Compare

### 이 버전에 속하는 변경 / Changes owned by this version

- 스테레오 역상 상쇄를 피하는 채널별 피치 근거, 배음·잡음 억제, 반복 창의 코드 근거 확인
- 단음·잡음·짧은 불안정 후보를 미확정으로 보존하며 코드 근거 점수를 정답 확률과 구분
- 기타 stem이 매우 약하거나 코드 근거가 부족할 때 원본 믹스 화성을 별도로 보조 분석
- 원본 화성 참고는 기타 운지·역위·최저음 검출로 표현하지 않으며 톤 추천과 Reference PCM은 유지
- GUI·JSON·HTML에 분석 출처·진단·선택 구간의 원본 파일 시각·미확정 구간 표시
- 작업 표시줄을 제외한 Windows 작업 영역에 맞춘 창 크기, 고정 높이의 스크롤 상태 영역, 입력 스크롤 보정
- 긴 결과 제목과 내보내기 버튼의 줄 배치로 작은 창의 하단 잘림 개선

### 검증 경계 / Verification boundary

코드 검출 구간 비율은 정확도가 아닙니다. 정답 코드 악보가 없는 사용자 샘플은 실행·출처·안정성 검증에만 사용합니다.
원본 믹스에는 베이스·건반 등 여러 악기가 포함되며 기타 보이싱을 확인해 주지 않습니다.
음원·중간 stem·개인 분석 로그는 로컬에만 보관하고 공개 저장소와 ZIP에서 제외합니다.

Chord coverage is not accuracy. The supplied backing track has no verified ground-truth chord chart.
Mix harmony remains an explicitly labeled reference; tone recipes and Reference Compare still use the guitar stem.
CUDA hardware, microphone/loopback capture, offline network disabling and code signing are not validated in this patch.
No live feature meters, automatic EQ/preset writing, C++ engine, ASIO or WASAPI Exclusive were added.

### 릴리스 게이트 결과 / Release gate result

- [x] Python 3.12 전체 자동 테스트 `121 tests`, warnings-as-errors, compileall 통과
- [x] 소스·패키지·새 압축 해제 EXE 자체 진단 `ok: true`, 추천 3개, Reference 6밴드, 개발자 블록 11개
- [x] 사용자 제공 252.61초 MP3 전체 CPU 분석: 소스 `104.844초`, EXE 표시 `01:47`; 모델 캐시 재사용
- [x] 실제 EXE의 단계 진행률·완료 상태·원본 화성 참고·미확정 구간·JSON 저장 확인
- [x] 원본 화성 후보 38구간, 전체 타임라인 73구간; 421창 중 79창에 반복 코드 근거, 그 외 미확정 — 정답률 아님
- [x] 소스와 실제 EXE JSON의 코드 결과 정확히 일치; 기타 운지·slash-bass 주장 없음
- [x] 실제 EXE 960×600 클라이언트 창에서 완료 footer·폼 스크롤·긴 저장 경로 상태 유지
- [x] 숨긴 Tk 960×600 / 1024×688 / 1280×640, scaling 2.0, 한/영, 긴 완료·오류 문자열 회귀
- [x] 새 ZIP 압축 해제 후 manifest 4,447개 크기·SHA-256, 필수 소스 일치, 모델 가중치·공개 로그 개인 경로 없음
- [x] 읽기 전용 코드·문서 감사에서 릴리스 차단 문제 없음; 이전 버전 이력 불변
- [ ] 정답 악보 대비 코드 채보 정확도, 실제 CUDA·마이크/loopback 캡처·네트워크 차단·코드 서명 — `NOT TESTED`

샘플의 분리 기타 RMS는 약 −63.25 dBFS였습니다. 검출 구간 수는 원본 믹스의 참고 후보이며
기타 보이싱이나 톤 추천의 정확성을 보증하지 않습니다. 확정 결과와 한계는 `QA_REPORT_v0.0.07.json`에 기록합니다.

### 최종 산출물 기록 / Final artifact record

최종 EXE·ZIP·자체 진단·manifest·공개 빌드 로그 해시는 ZIP 옆
`ToneMatchTMP-v0.0.07-SHA256SUMS.txt`가 기준입니다. ZIP 내부 개별 파일의 크기·해시는
`MANIFEST.json`으로 확인합니다. 문서 변경 후에도 새 압축 해제 검증을 반복합니다.

## 0.0.06 — Reference spectrum versus live Current

- 작업일 / Work dates: `2026-09-06–07 KST`; final build date: `2026-09-07 KST`
- 상태 / Status: `BUILT AND VERIFIED — unsigned CPU portable developer preview`
- 기반 / Based on: v0.0.05 live input spectrum analyzer and bounded latest-frame monitor

### 이 버전에 속하는 변경 / Changes owned by this version

- 파일 분석에 실제 사용한 PCM에서 레벨 정규화 Reference 주파수 프로필 생성·결과 저장
- 풀믹스는 Demucs guitar stem, 분리 생략은 디코딩한 로컬/녹음 소스를 Reference로 사용
- 기존 v0.0.05 WASAPI 실시간 모니터의 최신 프레임을 Current로 재사용
- Low, Low Mid, Mid, Presence, Treble, Air 6밴드의 `Reference | Current | Δ` 표시
- Reference와 Current의 샘플레이트가 달라도 공통 주파수 그리드로 보간하고 전체 power를 각각 정규화
- 0 dB 중심 주파수별 `Δ(Current−Reference)` 그래프와 무음·비유한 입력·나이퀴스트 경계 처리
- 기준 프로필·밴드 집계·실시간 비교·Tk 표시의 실제 장치 없는 결정론적 회귀 범위
- 전체 단계 수치 %·경과 시간, 모델 실제 다운로드 수신량과 Demucs 내부 완료 블록의 음원 처리 초 표시
- 입력 옵션을 스크롤해도 분석 버튼·진행률·현재 단계가 항상 보이는 고정 영역
- 콘솔 없는 EXE의 `stdout/stderr=None` 보호 및 HF 오류를 legacy 출력 오류로 덮던 모델 로딩 경로 수정
- 캐시 우선 safetensors 로드, 모델 오류 원인 분류, 내부 블록 취소와 미완성 출력 정리

### 검증 경계 / Verification boundary

Reference Compare는 파일 분석이 만든 Reference와 기존 실시간 모니터의 Current를
레벨 정규화해 비교합니다. Δ 부호는 항상 `Current−Reference`입니다. 전체 입력
게인을 맞추거나 원곡 장비·DSP를 복원하는 기능이 아니며, 통계적 정확도 또는
Match %로 표현하지 않습니다. 참고 URL은 외부 브라우저 열기와 출처 기록 전용이고
URL의 오디오를 다운로드·분석하지 않습니다.

Live Brightness, Body, Gain, Compression, Ambience, Match % 미터, 자동 EQ/TMP
파라미터 추천·적용, 프리셋 쓰기, C++ 오디오 엔진, ASIO와 WASAPI Exclusive는
v0.0.06에 포함되지 않습니다.

전체 %는 처리 단계에 배정한 진행률이며 남은 시간의 비율이나 ETA가 아닙니다.
첫 모델 다운로드의 실제 수신량과 캐시 재사용 분석을 별도로 검증했습니다.

### 릴리스 게이트 결과 / Release gate result

- [x] 앱·spec·Windows 파일 정보·빌드 스크립트의 `0.0.06` 동기화 확인
- [x] Python 3.12 경고-as-error 전체 자동 테스트 통과 — `80 tests`
- [x] 소스 자체 진단 `ok: true`, Reference Compare, 3 recipes, 11 developer blocks
- [x] Windows WASAPI 장치 열거 — 4개(입력 1, loopback 3), 실제 오디오 캡처 없음
- [x] 패키지 EXE 자체 진단 및 새 압축 해제 EXE 독립 자체 진단 통과
- [x] 새 임시 폴더 ZIP 압축 해제와 `MANIFEST.json` 4,446개 파일별 크기·SHA-256 재검증
- [x] 필수 v0.0.06 소스·테스트·FFmpeg 포함, 모델 가중치 없음, 공개 로그 개인 경로 없음
- [x] 제공 MP3 252.61초 전체 CPU 분석: 소스 첫 모델 다운로드 포함 109.204초, EXE 캐시 재사용 화면 `01:42`, 추천 3개와 기준 6대역 표시
- [x] EXE 창에서 소수점 진행률·경과 시간·처리한 음원 초·완료 상태·Reference Compare 시각 확인
- [x] 숨긴 Tk 1080×720 한·영 화면의 고정 진행 영역과 긴 상태 문자열 회귀 테스트
- [ ] 실제 마이크/loopback Reference Compare, 네트워크 차단 상태의 실행과 코드 서명 — `NOT TESTED`
- [ ] 실제 CUDA GPU 추론 — `NOT TESTED: CPU-only release environment unless later verified`

### 최종 산출물 기록 / Final artifact record

ZIP은 자기 자신의 해시를 내부 문서에 넣을 수 없으므로 최종 값은 ZIP과 함께 배포할
`ToneMatchTMP-v0.0.06-SHA256SUMS.txt`를 기준으로 합니다. 내부 개별 파일 크기와
해시는 `MANIFEST.json`에 있습니다. 내부 문서를 최종 반영한 뒤에도 압축 해제
검증을 다시 실행하고, 통과한 바이트만 업로드합니다.

| 산출물 | 바이트 | SHA-256 | 검증 |
|---|---:|---|---|
| `ToneMatchTMP-v0.0.06.exe` | `MANIFEST.json` | 형제 체크섬 파일 | package / fresh-extract self-test |
| `ToneMatchTMP-v0.0.06-Windows-x64-Portable-Dev.zip` | GitHub release asset | 형제 체크섬 파일 | fresh-extract manifest verification |
| `ToneMatchTMP-v0.0.06-SELF-TEST.json` | `MANIFEST.json` | 형제 체크섬 파일 | `ok: true` |
| `ToneMatchTMP-v0.0.06-build.log` | `MANIFEST.json` | 형제 체크섬 파일 | private-path audit |

샘플은 반주 음원으로 분리 guitar stem이 약했습니다(RMS 약 −63.25 dBFS).
위 결과는 실행·진행률 검증이며 원곡 톤 복원의 정확성을 보증하지 않습니다.
사용자 음원과 로컬 분석 로그는 공개 ZIP 또는 저장소에 포함하지 않았습니다.

ZIP 내용이나 문서를 바꾸면 형제 체크섬과 manifest를 반드시 다시 계산합니다.

### 권장 로그 생성 / Suggested build log

```powershell
$buildLog = Join-Path (Get-Location) "ToneMatchTMP-v0.0.06-BUILD.log"
Start-Transcript -LiteralPath $buildLog -Force
try {
    .\build.ps1
} finally {
    Stop-Transcript
}
```

## 0.0.05 — Live input spectrum analyzer

- 작업일 / Work date: `2026-09-05 KST`
- 상태 / Status: `BUILT AND VERIFIED — unsigned CPU portable developer preview`
- 기반 / Based on: v0.0.04 GPU diagnostics, native NumPy optimization, and route-aware recipe pipeline

### 이 버전에 속하는 변경 / Changes owned by this version

- 선택한 Windows 오디오 입력 또는 PC 재생음 loopback의 실시간 모니터링
- 2,048 샘플 블록의 입력 파형과 20 Hz~20 kHz 로그 주파수 스펙트럼 표시
- RMS·Peak dBFS와 스펙트럼 중심 주파수 수치 표시
- 좌우 역상 신호가 사라지지 않는 채널별 NumPy FFT 파워 평균과 Hann 창 dBFS 보정
- 무음·NaN·무한대 입력의 안전한 표시 하한 처리와 나이퀴스트 주파수 제한
- 최근 4프레임의 선형 파워 평활화, 최신 프레임 하나만 보관하는 bounded UI 큐
- worker 스레드와 Tk UI 분리, 세션 ID 기반 낡은 이벤트 차단과 중지 후 자원 정리
- 녹음·AI 분석·하드웨어 검사·언어 전환과 실시간 장치 사용의 상호 배타 제어
- 스펙트럼 DSP·스트림·Tk Canvas를 실제 오디오 캡처 없이 검증하는 결정론적 테스트

### 검증 경계 / Verification boundary

v0.0.05는 Python 조정 계층과 NumPy의 컴파일된 FFT 연산을 사용합니다. ASIO,
WASAPI Exclusive, 하드 실시간 콜백과 C++ 엔진은 이 버전에 포함되지 않습니다.
실시간 스펙트럼은 선택한 원시 입력의 시각화이며, Demucs 분리나 톤 레시피 추천에
직접 연결되지 않습니다.

The analyzer uses Python orchestration and NumPy's compiled FFT operations. ASIO,
WASAPI Exclusive, hard-real-time callbacks, and a C++ engine are not part of this
release. It visualizes the selected raw input and does not feed Demucs or recipes yet.

Windows WASAPI 장치 열거는 통과했지만 사적 시스템 소리나 마이크를 의도치 않게
수집하지 않도록 실제 블록 캡처는 자동 QA에서 수행하지 않았습니다. 패키지 GUI의
수동 시각 점검도 미실행이며, mapped Tk 창에서 수치와 두 Canvas 렌더링을 자동 검증했습니다.

### 릴리스 게이트 결과 / Release gate result

- [x] 앱·spec·Windows 파일 정보·빌드 스크립트의 `0.0.05` 동기화
- [x] Python 3.12에서 경고를 오류로 처리한 최종 자동 테스트 `46/46` 통과
- [x] 소스 자체 진단 `ok: true`, 레시피 3개·개발자 블록 11개·FFmpeg 분석 확인
- [x] Windows WASAPI 장치 열거: 입력 1개, loopback 3개
- [x] 합성 스테레오 2,048 샘플 FFT·평활화 2,000회 처리 관찰값 평균 `0.7081 ms/frame`
- [x] 패키지 EXE 자체 진단 `ok: true`, 앱 버전·레시피 3개·개발자 블록 11개 확인
- [x] 새 임시 폴더 ZIP 압축 해제와 `MANIFEST.json` 파일 `4,443/4,443` 크기·SHA-256 재검증
- [x] 필수 v0.0.05 소스·테스트·FFmpeg 포함, 모델 가중치 없음, 공개 로그 개인 경로 없음
- [ ] 실제 마이크/loopback 블록 캡처, 패키지 GUI 수동 시각 점검과 코드 서명
- [ ] 실제 CUDA GPU 추론 — `NOT TESTED: CPU-only release environment`

### 최종 산출물 기록 / Final artifact record

ZIP은 자기 자신의 해시를 내부 문서에 넣을 수 없으므로, 모든 최종 바이트·SHA-256은
ZIP과 함께 배포하는 `ToneMatchTMP-v0.0.05-SHA256SUMS.txt`를 기준으로 합니다.
`MANIFEST.json`은 ZIP 내부 각 파일을 별도로 검증합니다.

| 산출물 | 바이트 | SHA-256 | 검증 |
|---|---:|---|---|
| `ToneMatchTMP-v0.0.05.exe` | 형제 체크섬 파일에서 확인 | 형제 체크섬 파일에서 확인 | 패키지 자체 진단 통과 |
| `ToneMatchTMP-v0.0.05-Windows-x64-Portable-Dev.zip` | 형제 체크섬 파일에서 확인 | 형제 체크섬 파일에서 확인 | 새 임시 폴더 압축 해제·manifest 재검증 |
| `ToneMatchTMP-v0.0.05-SELF-TEST.json` | 형제 체크섬 파일에서 확인 | 형제 체크섬 파일에서 확인 | `ok: true` |
| `ToneMatchTMP-v0.0.05-build.log` | manifest/형제 체크섬 파일에서 확인 | manifest/형제 체크섬 파일에서 확인 | 사용자 홈·프로젝트 경로 일반화 |

ZIP 내용을 바꾸거나 문서를 갱신하면 형제 체크섬과 manifest를 반드시 다시 계산합니다.

### 권장 로그 생성 / Suggested build log

```powershell
$buildLog = Join-Path (Get-Location) "ToneMatchTMP-v0.0.05-BUILD.log"
Start-Transcript -LiteralPath $buildLog -Force
try {
    .\build.ps1
} finally {
    Stop-Transcript
}
```

## 0.0.04 — Compute diagnostics and route-aware Amp/Cab

- 작업일 / Work date: `2026-09-04 KST`
- 상태 / Status: `BUILT AND VERIFIED — unsigned CPU portable developer preview`
- 기반 / Based on: v0.0.03 portable developer handoff and experimental chord/voicing pipeline

### 이 버전에 속하는 변경 / Changes owned by this version

- Demucs 기타 분리의 `auto`/`cpu`/`cuda` 선택, CUDA 미지원 자동 CPU 폴백과 설정 유지
- CUDA 빌드·GPU 모델/연산 능력·총/여유 VRAM을 UI가 멈추지 않도록 조회하는 성능 진단
- 실제 선택 장치, 전체/조각별 추론 시간, 실시간 배수와 최대 GPU 메모리 결과 기록
- 코드·보이싱 반복 계산 캐시와 NumPy 벡터 연산을 통한 컴파일된 네이티브 DSP 경로 최적화
- FRFR/헤드폰/USB/PA, 실제 캐비닛용 파워앰프, 기타 앰프 전면 입력별 Amp/Cab 포함 규칙·적용 순서 분리
- FRFR Cabinet 컷과 중복되던 독립 EQ 제거, 실제 캐비닛 경로에서 기준 Cabinet 비교 정보 보존
- CPU 포터블과 분리된 `requirements-cuda126.txt`/`enable_cuda.ps1` 기반 NVIDIA CUDA 소스 환경 절차
- 전체 C++ 재작성 대신 후속 실시간 콜백·링 버퍼·FFT·ASIO만 C++ 경계로 두는 설계 방향

### 검증 경계 / Verification boundary

포터블 EXE는 CPU 런타임을 포함합니다. 이 개발 PC에는 CUDA 지원 GPU가 없어 실제
GPU Demucs 추론, VRAM 사용량과 CPU/GPU 음원 비교는 하드웨어 검증하지 못했습니다.
CUDA 분기 mock 테스트와 실제 CPU 폴백 결과를 GPU 검증으로 표현하지 않습니다.
호환 NVIDIA PC에서 별도 CUDA 환경을 설치한 뒤 실제 짧은 분리, 메모리 회수와 취소를
추가 검증해야 합니다.

The portable EXE contains the CPU runtime. No CUDA-capable GPU was available on
the release machine, so real GPU inference, VRAM use, and CPU/GPU output comparison
remain unverified. Mock branch coverage and real CPU fallback are not GPU validation.

C++ 실시간/ASIO 엔진은 로드맵이며 v0.0.04 산출물에는 포함되지 않습니다. 현재
오프라인 앱은 Python이 조정하고 NumPy/PyTorch의 컴파일된 네이티브 연산을 사용합니다.

### 릴리스 게이트 결과 / Release gate result

- [x] 모든 버전 파일·배포 문서의 `0.0.04` 동기화 확인
- [x] 출력 경로별 Amp/Cab 계약과 Cabinet 컷 비중복 회귀 테스트 통과
- [x] 자동/CPU/CUDA 장치 결정과 진단 데이터 구조 회귀 테스트 통과
- [x] Python 3.12에서 최종 자동 테스트 `26/26` 통과
- [x] 소스·패키지 EXE 자체 진단 모두 `ok: true`
- [x] 새 임시 폴더 ZIP 압축 해제와 `MANIFEST.json` 파일별 크기·SHA-256 재검증
- [x] EXE·ZIP·자체 진단·manifest·공개 빌드 로그 SHA-256을 형제 체크섬 파일에 기록
- [ ] 실제 CUDA GPU 추론 — `NOT TESTED: no compatible GPU on this release PC`
- [ ] 실제 개인 PC 재생음 loopback 수동 테스트와 코드 서명

### 최종 산출물 기록 / Final artifact record

ZIP은 자기 자신의 해시를 내부 문서에 넣을 수 없으므로, 모든 최종 바이트·SHA-256은
ZIP과 함께 배포하는 `ToneMatchTMP-v0.0.04-SHA256SUMS.txt`를 기준으로 합니다.
`MANIFEST.json`은 ZIP 내부 각 파일을 별도로 검증합니다.

| 산출물 | 바이트 | SHA-256 | 검증 |
|---|---:|---|---|
| `ToneMatchTMP-v0.0.04.exe` | 형제 체크섬 파일에서 확인 | 형제 체크섬 파일에서 확인 | 패키지 자체 진단 통과 |
| `ToneMatchTMP-v0.0.04-Windows-x64-Portable-Dev.zip` | 형제 체크섬 파일에서 확인 | 형제 체크섬 파일에서 확인 | 새 임시 폴더 압축 해제·manifest 재검증 |
| `ToneMatchTMP-v0.0.04-SELF-TEST.json` | 형제 체크섬 파일에서 확인 | 형제 체크섬 파일에서 확인 | `ok: true` |
| `ToneMatchTMP-v0.0.04-build.log` | manifest/형제 체크섬 파일에서 확인 | manifest/형제 체크섬 파일에서 확인 | 사용자 홈·프로젝트 경로 일반화 |

ZIP 내용을 바꾸거나 문서를 갱신하면 형제 체크섬과 manifest를 반드시 다시 계산합니다.

### 권장 로그 생성 / Suggested build log

```powershell
$buildLog = Join-Path (Get-Location) "ToneMatchTMP-v0.0.04-BUILD.log"
Start-Transcript -LiteralPath $buildLog -Force
try {
    .\build.ps1
} finally {
    Stop-Transcript
}
```

## 0.0.03 — Portable developer handoff

- 작업일 / Work date: `2026-09-03 KST`
- 상태 / Status: `BUILT AND VERIFIED — unsigned portable developer preview`
- 기반 / Based on: v0.0.02 audio-analysis and recording pipeline

### 이 버전에 속하는 변경 / Changes owned by this version

- 재현 가능한 다른-PC 재개 절차와 포터블 개발 ZIP 구성
- 한국어/English 개발 인수인계 문서
- 빌드·자체 진단·실행 로그를 남기고 전달하는 기준
- 버전별 산출물 크기·SHA-256을 누적하는 이 파일
- NumPy 기반 코드/보이싱 분석(실험)
- 보이싱 결과를 톤 레시피와 분리하고 오검출/낮은 신뢰도를 명시하는 테스트·문구

### 코드/보이싱 실험의 경계 / Experimental voicing boundary

목표는 기타 stem의 안정적인 프레임에서 피치 클래스, 코드 후보, 베이스 음, 음역/보이싱 단서를 보수적으로 요약하는 것입니다. 완전한 다성음 채보, 타브 생성, 연주 채점 또는 확정 코드 판정이 아닙니다. 왜곡, 벤딩, 드롭 튜닝, 카포, 잔여 베이스·건반과 분리 인공음은 결과를 흔들 수 있으므로 낮은 신뢰도를 그대로 표시해야 합니다.

The goal is a conservative summary of pitch classes, chord candidates, bass note, and register/voicing cues from stable guitar-stem frames. It is not full polyphonic transcription, tablature, performance grading, or an authoritative chord chart.

### 릴리스 게이트 결과 / Release gate result

- [x] `catalog.APP_VERSION`, 최신 `CHANGELOG`, `version_info.txt`, spec와 배포 문서가 `0.0.03`
- [x] 고정된 `requirements.txt`와 spec가 NumPy, PyInstaller, Demucs, PyTorch, SoundCard 및 앱 모듈을 포함
- [x] 제3자 고지·런타임 라이선스 인벤토리 포함; AI 모델 가중치는 의도적으로 제외
- [x] 언어·장치·녹음·취소·보이싱 UI와 엔진 연결 완료
- [x] Python 3.12.13에서 자동 테스트 `16/16` 통과
- [x] 소스 자체 진단과 패키지 EXE 자체 진단 모두 `"ok": true`; 개발자 블록 `11/11`
- [x] 실제 Demucs 첫 다운로드와 캐시 재사용, 기타 유사 오디오 end-to-end 분석, 장치 열거, 합성 보이싱 점검
- [x] 포터블 stage에서 사용자 오디오·영상, AI 모델 가중치, Python 캐시가 없음을 검사
- [x] EXE·자체 진단·공개용 빌드 로그 SHA-256 기록; 최종 ZIP 해시는 동봉된 형제 체크섬 파일에 기록
- [ ] 실제 개인 PC 재생음을 녹음하는 loopback 수동 테스트와 코드 서명

실제 재생음 녹음은 사용자의 사적 오디오를 의도치 않게 수집하지 않도록 자동 QA에서 수행하지 않았습니다. 장치 열거는 Windows WASAPI에서 통과했습니다. GPU 추론은 이번 CPU 배포 범위에 포함하지 않습니다.

### 최종 산출물 기록 / Final artifact record

ZIP은 자기 자신의 해시를 내부 문서에 넣을 수 없으므로, ZIP과 함께 배포하는 `ToneMatchTMP-v0.0.03-SHA256SUMS.txt`를 최종 기준으로 사용합니다.

| 산출물 | 바이트 | SHA-256 | 검증 |
|---|---:|---|---|
| `ToneMatchTMP-v0.0.03.exe` | 39,267,061 | `879E9855FEF8DF56D9D0B83CDADF5A87A938A3085231944F550E3370CCF4A2DD` | 패키지 자체 진단 통과 |
| `ToneMatchTMP-v0.0.03-Windows-x64-Portable-Dev.zip` | 체크섬 파일에서 확인 | 체크섬 파일에서 확인 | 새 임시 폴더 압축 해제·manifest 재검증 |
| `ToneMatchTMP-v0.0.03-SELF-TEST.json` | 578 | `455DB5C4867456E81011B80B0F5FB7247DAC8184EC3FF3377C6FE1D206664F85` | `ok: true` |
| `ToneMatchTMP-v0.0.03-build.log` | 24,166 | `D30414A979D46FA78C87FFA15A03E7F4AA2DDCD170002CC9F34AA8501C7F1404` | 일반·repr 형식 사용자 홈·프로젝트 경로 일반화 |

최초 패키징 스크립트는 GUI 하위 시스템 EXE 호출이 종료 전에 반환하는 Windows 동작 때문에 자체 진단 파일을 너무 일찍 읽었습니다. `Start-Process -Wait -WindowStyle Hidden`으로 수정했고 같은 EXE의 자체 진단을 다시 통과시킨 뒤 패키징을 재개했습니다.

### 권장 로그 생성 / Suggested build log

```powershell
$buildLog = Join-Path (Get-Location) "ToneMatchTMP-v0.0.03-BUILD.log"
Start-Transcript -LiteralPath $buildLog -Force
try {
    .\build.ps1
} finally {
    Stop-Transcript
}
```

로그에는 테스트 요약, Python/핵심 패키지 버전, PyInstaller 결과와 자체 진단 결과를 남깁니다. 공유 전 사용자 이름이 포함된 절대 경로, 오디오 파일명, 토큰, 프록시와 계정 정보를 지웁니다.

## 0.0.02 — AI isolation and recording integration

- 소스 이정표 날짜 / Source milestone: `2026-09-02 KST`
- 상태 / Status: 기능 범위를 0.0.03 포터블 개발 패키지로 승계; 독립 최종 ZIP/해시 기록 없음

### 이 버전에 속하는 변경 / Changes owned by this version

- 한국어/English 실시간 전환과 언어별 표시
- 확장 가능한 멀티이펙터 프로필과 Tone Master Pro 전용 활성 지원
- 45초 제한을 최대 20분으로 확장; 끝 `0`/빈칸 전체 처리
- Demucs `htdemucs_6s` 6-stem 모델의 guitar stem만 DSP 분석
- 30초 외부 조각 처리, 진행률과 조각 경계 취소
- Windows WASAPI loopback PC 재생음과 오디오 입력 녹음
- 첫 모델 다운로드, Hugging Face 사용자 캐시 상태와 오류 안내
- 긴 CPU 분석, stem 누출/인공음과 자동 프리셋 쓰기 부재 고지

These language/device, 20-minute, Demucs guitar-stem, Windows recording, and cancellation changes belong to v0.0.02 even when delivered inside the later v0.0.03 portable package.

## 0.0.01 — Initial private preview

- 빌드일 / Build date: `2026-09-02 KST`
- 상태 / Status: 검증된 최초 비공개 프리뷰
- 대상 / Target: Tone Master Pro firmware 1.8.58, Model Guide Rev. J
- 자체 진단 / Self-test: `ok: true`, FFmpeg analysis true, developer source blocks 9/9, recipes 3

| 산출물 | 바이트 | SHA-256 |
|---|---:|---|
| `ToneMatchTMP-v0.0.01.exe` | 61,766,971 | `4334B61D0C79BF7EC1B93670598932C3C38A4D9D388505EE7356CBBA99CEB212` |
| `ToneMatchTMP-v0.0.01-SOURCE.zip` | 38,846,230 | `FE168381F902851AC04B671F9D64382CC7D1B991ED723D7605C917BE08FCC797` |
| `ToneMatchTMP-v0.0.01-SELF-TEST.json` | 247 | `51A0FAB92AD0C8EF68925C0E46FAFC2BA113A08024D10DCCBD5E29E8B816AD89` |

### 주요 범위 / Main scope

- 로컬 오디오 3~45초 NumPy DSP 특징 분석
- Tone Master Pro 템플릿 상위 3개
- 픽업·풀믹스·출력 보정
- JSON, 독립형 HTML과 클립보드 레시피
- 처리 다이어그램, 로그, 클릭형 한글 소스와 변경 기록
- YouTube 주소는 참고/브라우저 열기 전용

## 모든 다음 빌드의 기록 규칙 / Rules for every later build

1. 버전별 기능 경계를 섞지 않고 새 항목을 맨 위에 추가합니다.
2. 앱 버전, changelog, Windows 버전 리소스, EXE·ZIP 이름과 문서를 동기화합니다.
3. 테스트와 자체 진단을 통과한 정확한 소스에서만 EXE와 ZIP을 만듭니다.
4. ZIP을 새 임시 폴더에 풀어 누락 파일·절대 경로 의존성을 다시 확인합니다.
5. 모든 산출물이 닫힌 뒤 SHA-256을 계산합니다. ZIP 내용을 바꾸면 해시를 다시 계산합니다.
6. AI 가중치, `.venv`, `build`, `dist`, 캐시, 사용자 오디오·결과·로그 원본과 자격 증명을 제외합니다.
7. 로그가 실패를 포함하면 성공 빌드로 덮어쓰지 말고 실패 원인과 후속 빌드를 별도 기록합니다.
8. 코드 서명 여부와 Windows 경고 가능성을 명시합니다.
