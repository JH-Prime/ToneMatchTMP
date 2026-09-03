# ToneMatch TMP — Build History / 빌드 이력

이 파일은 릴리스별 소스 범위, 검증 결과와 산출물 해시를 누적 기록합니다. 최신 항목을 위에 두고, 이미 배포한 버전의 날짜·해시는 수정하지 않습니다.

This append-only record tracks source scope, verification, and artifact hashes. Keep the newest entry first and never rewrite dates or hashes for an artifact that was already shared.

## 버전 요약 / Version Map

| 버전 | 상태 | 범위 |
|---|---|---|
| `0.0.03` | 포터블 개발 프리뷰 빌드 완료 | 포터블 개발 ZIP, 한·영 handoff, 로그·빌드 이력, NumPy 코드/보이싱 분석(실험) |
| `0.0.02` | 기능 통합 이정표, 0.0.03으로 승계 | 한국어/English, 장치 선택, 최대 20분, Demucs guitar stem, PC 재생음/입력 녹음, 취소 |
| `0.0.01` | 검증된 최초 비공개 프리뷰 | 짧은 로컬 오디오 DSP, TMP 추천 3개, JSON/HTML, 개발자 코드 뷰 |

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
