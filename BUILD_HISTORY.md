# ToneMatch TMP — Build History / 빌드 이력

이 파일은 릴리스별 소스 범위, 검증 결과와 산출물 해시를 누적 기록합니다. 최신 항목을 위에 두고, 이미 배포한 버전의 날짜·해시는 수정하지 않습니다.

This append-only record tracks source scope, verification, and artifact hashes. Keep the newest entry first and never rewrite dates or hashes for an artifact that was already shared.

## 버전 요약 / Version Map

| 버전 | 상태 | 범위 |
|---|---|---|
| `0.0.06` | 포터블 개발 프리뷰 빌드·검증 완료 | Reference Compare, 실시간 분석 진행률, 콘솔 없는 EXE 모델 오류 수정 |
| `0.0.05` | 포터블 개발 프리뷰 빌드·검증 완료 | Windows 입력/loopback 실시간 파형·FFT 스펙트럼, bounded 최신 프레임 처리 |
| `0.0.04` | 포터블 개발 프리뷰 빌드·검증 완료 | 자동/CPU/CUDA 진단·벤치마크, NumPy 네이티브 최적화, 출력 경로별 Amp/Cab 체인 정정 |
| `0.0.03` | 포터블 개발 프리뷰 빌드 완료 | 포터블 개발 ZIP, 한·영 handoff, 로그·빌드 이력, NumPy 코드/보이싱 분석(실험) |
| `0.0.02` | 기능 통합 이정표, 0.0.03으로 승계 | 한국어/English, 장치 선택, 최대 20분, Demucs guitar stem, PC 재생음/입력 녹음, 취소 |
| `0.0.01` | 검증된 최초 비공개 프리뷰 | 짧은 로컬 오디오 DSP, TMP 추천 3개, JSON/HTML, 개발자 코드 뷰 |

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
