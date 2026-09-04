# ToneMatch TMP v0.0.04 — 개발 인수인계 / Developer Handoff

이 문서는 v0.0.04 포터블 개발 ZIP을 다른 Windows PC나 새 개발 세션에서 이어서 작업하기 위한 기준 문서입니다. 대화 기록이 아니라 압축에 포함된 소스와 `BUILD_HISTORY.md`가 작업 상태의 근거입니다.

This is the source-of-truth handoff for continuing the v0.0.04 portable development snapshot on another Windows PC or in a new development session. The archived source and `BUILD_HISTORY.md`, not prior chat history, define the state being handed over.

> v0.0.04 산출물의 정확한 크기와 해시는 패키징 완료 뒤 `BUILD_HISTORY.md`와 ZIP 옆 `ToneMatchTMP-v0.0.04-SHA256SUMS.txt`를 기준으로 합니다. 문서의 자리표시자를 검증값으로 오인하지 마세요.
> After packaging, use `BUILD_HISTORY.md` and the sibling `ToneMatchTMP-v0.0.04-SHA256SUMS.txt` as the authority for exact v0.0.04 artifact sizes and hashes. Never treat pending placeholders as verified values.

---

## 한국어

### 1. 제품 범위와 변하지 않아야 할 계약

- 앱 버전: `0.0.04`
- 대상 장치: Fender Tone Master Pro
- 대상 펌웨어/모델 가이드: `1.8.58` / `Rev. J (2026-07)`
- 플랫폼: 64-bit Windows, Python 3.12 계열
- 입력: 로컬 오디오·영상 또는 Windows PC 재생음/오디오 입력 녹음
- 길이: 최소 3초, 시작 지점부터 최대 20분. 끝 `0`/빈칸은 전체 항목을 뜻하되 20분에서 제한
- 풀믹스: Demucs `htdemucs_6s`로 guitar stem을 분리한 뒤 그 stem만 DSP 분석
- 기타 단독 파일: 사용자 선택으로 AI 분리 생략
- 출력: 상위 3개 Tone Master Pro 레시피, JSON, 독립형 HTML, 클립보드 텍스트, 실험적 코드·보이싱 단서
- 기기 제어: Tone Master Pro/Pro Control 자동 쓰기 없음. 사용자가 값을 수동 적용
- 네트워크: 오디오 업로드·YouTube 추출 없음. 앱이 직접 받는 콘텐츠는 첫 AI 모델뿐이며, 참고 URL은 외부 브라우저에 위임

Neural DSP Quad Cortex, Line 6 Helix Family와 예약 장치 슬롯은 UI 확장용이며 현재 레시피 생성은 지원하지 않습니다.

버전 경계는 다음처럼 유지합니다.

- `0.0.02`: 한국어/English 전환, 확장형 장치 선택, 최대 20분 분석, Demucs guitar stem, PC 재생음/오디오 입력 녹음과 취소
- `0.0.03`: 포터블 개발 ZIP과 한·영 인수인계, 로그·빌드 이력 전달, NumPy 기반 코드/보이싱 분석(실험)
- `0.0.04`: 자동/CPU/CUDA 분리 선택, GPU·VRAM·추론 벤치마크 진단, NumPy 네이티브 최적화, 출력 경로별 Amp/Cab 체인 정정

v0.0.03에서 도입된 보이싱 결과는 톤 레시피와 별도의 참고 진단입니다. 완전한 다성음 채보, 타브 생성 또는 연주 정확도 판정으로 표현하지 않습니다.

### 2. 현재 처리 흐름

```text
[로컬 오디오/영상]
          또는
[SoundCard + WASAPI loopback/오디오 입력 → 임시 44.1 kHz PCM16 WAV]
          ↓
[FFmpeg: 선택 구간, 최대 20분]
          ↓
[auto/CPU/CUDA 결정 → 풀믹스이면 Demucs htdemucs_6s → 30초 외부 조각별 guitar stem]
          ↓
[22.05 kHz 분석 PCM → NumPy 네이티브 DSP 특징 + 코드/보이싱 단서(실험)]
          ↓
[픽업·출력 보정 → 18개 템플릿 매칭 → 경로별 Amp/Cab을 갖춘 TMP 레시피 3개]
          ↓
[GUI / JSON / HTML / 텍스트]
```

AI 분리용 혼합 WAV와 guitar stem은 `TemporaryDirectory` 안에서 만들어지고 분석 후 삭제됩니다. 작업 체크포인트나 중간 stem 불러오기는 구현돼 있지 않으므로 취소·오류·PC 이동 후에는 분석을 처음부터 다시 실행해야 합니다. 재사용되는 것은 완전히 다운로드된 AI 모델 캐시뿐입니다.

### 3. 모듈 지도

| 파일 | 책임 |
|---|---|
| `app.py` | Tkinter UI, 언어/장치/입력·연산 선택, 비동기 GPU/VRAM 진단, 녹음·분석 작업 스레드, 취소, 내보내기, 자체 진단 |
| `engine.py` | 최대 20분 FFmpeg 디코딩, DSP 특징, AI 분리 호출, 템플릿 매칭, 출력 경로별 Amp/Cab과 결과 구조 |
| `separator.py` | Demucs/PyTorch 자동/CPU/CUDA 선택·폴백, 모델 캐시와 GPU/VRAM 진단, 추론 벤치마크, 30초 조각별 guitar stem 생성 |
| `recorder.py` | SoundCard 기반 WASAPI loopback·오디오 입력 목록과 PCM16 녹음 |
| `voicing.py` | 캐시와 NumPy 벡터 연산 기반 피치 클래스·코드 후보·저음/음역 단서 추정(실험, 톤 매칭과 분리) |
| `catalog.py` | 앱/펌웨어 버전, 변경 기록, 18개 TMP 톤 템플릿 |
| `i18n.py` | 한국어/영어 UI·오류·진행 문자열과 안정적인 선택 코드 변환 |
| `devices.py` | 멀티이펙터 프로필, 지원 여부와 언어별 표시 |
| `report.py` | 언어별 텍스트/HTML 결과 |
| `debug_info.py` | 처리 블록, 진행률 매핑과 EXE 내 클릭형 소스 뷰 |
| `tests/` | DSP, 다국어, 개발자 모드와 패키지 회귀 테스트 |
| `ToneMatchTMP.spec` | PyInstaller 데이터·바이너리·숨은 import·버전 리소스 |
| `build.ps1` | 테스트 후 깨끗한 PyInstaller 빌드 |

`DEVELOPMENT_KO.md`는 v0.0.04 구현 구조 요약이고, `FUNCTION_REFERENCE_KO.md`는 배포 소스의 모든 함수와 한국어 docstring을 자동 색인합니다. 새 PC 재구성과 릴리스 판정은 이 문서를 우선합니다.

#### v0.0.03 코드/보이싱 실험 계약

- 공개 API: `analyze_voicings(samples, sample_rate, tuning_reference_hz=440.0, max_events=96)`와 `voicing_analysis_dict(analysis)`
- 입력: 엔진이 이미 준비한 22.05 kHz 기타 분석 버퍼. 풀믹스는 분리된 guitar stem, 기타 단독은 원본 버퍼
- 방법: 채널별 STFT power, 고조파 salience, 12-bin pitch class/chroma, 짧은 시간 문맥, 제한된 코드 템플릿과 시간 평활화
- 출력: 시간 이벤트별 `root_pc`, `quality`, `bass_pc`, 들리는 음역·간격 단서, 대안 후보와 0~1 신뢰도
- 안정 코드: core에는 C/도 같은 번역 문자열보다 `root_pc=0..11`과 `major/minor/power5/.../unknown`을 저장
- 보수 정책: 3도가 없으면 장·단조를 추측하지 않고 `power5`/`unknown` 처리. 임계값이나 1·2위 점수 차가 작으면 `unknown`
- 금지 표현: string/fret/open/barre shape, 확정 타브, 완전 채보. 같은 음높이 집합에서 물리적 운지는 유일하게 복원되지 않음
- 결정론: 후보 동점 정렬과 반올림 규칙을 고정하고 같은 입력의 JSON이 매번 같아야 함

바깥 `tonematch-tmp-recipe/v1` 결과의 `chord_voicing` 필드가 독립 `tonematch-voicing/v1` 객체를 담습니다. 이후 필드 의미를 깨는 변경은 보이싱 스키마 버전과 바깥 스키마 호환성을 함께 검토합니다.

#### v0.0.04 연산·Amp/Cab 계약

- `auto`는 CUDA 가용성을 런타임에 확인해 CUDA 또는 CPU를 선택하고, CUDA가 없으면 CPU로 폴백합니다. 명시적 `cuda` 요청을 임의로 CPU 결과로 바꾸지 않습니다.
- 진단은 CUDA 빌드, GPU 이름·연산 능력, 총/여유 VRAM을 표시하고 분석 결과에는 실제 장치, 전체/조각별 추론 시간, 실시간 배수와 최대 GPU 메모리를 남깁니다.
- 포터블 EXE는 CPU 런타임을 포함합니다. `requirements-cuda126.txt`와 `enable_cuda.ps1`은 호환 NVIDIA PC에서만 사용하는 별도 소스 개발 경로입니다.
- 이번 릴리스 PC에는 CUDA GPU가 없어 실제 GPU Demucs 추론과 VRAM 값은 하드웨어 검증하지 못했습니다. mock 회귀 테스트와 CPU 폴백을 실제 GPU 검증으로 표현하지 않습니다.
- FRFR/헤드폰/USB/PA는 Amp Only + Cabinet, 실제 캐비닛용 파워앰프는 Amp Only, 기타 앰프 전면 입력은 Amp/Cab 없음입니다. FRFR Cabinet의 로우/하이 컷을 별도 EQ로 중복하지 않습니다.
- Python은 UI·AI·레시피 기준 구현입니다. C++은 후속 실시간 오디오 콜백, 링 버퍼, FFT와 ASIO 경계로 한정할 계획이며 v0.0.04에는 구현되지 않았습니다.

### 4. 다른 PC에서 개발 환경 재구성

권장 폴더 구조:

```text
C:\ToneMatchTMP-dev\ToneMatchTMP-v0.0.04\
├─ .venv\                 새 PC에서 다시 생성
├─ ToneMatchTMP-v0.0.04.exe
└─ source\                자체 완결된 개발 프로젝트
   ├─ app.py
   ├─ requirements.txt
   ├─ build.ps1
   ├─ resources\ffmpeg.exe
   ├─ tests\
   └─ ...
```

`build.ps1`는 프로젝트의 형제 위치인 `..\.venv`를 찾습니다. 압축에 `.venv`가 있더라도 사용하지 마세요. Python 가상환경에는 원래 PC의 절대 경로와 네이티브 바이너리가 들어가므로 새 PC에서 다시 만드는 것이 안전합니다.

```powershell
Set-Location C:\ToneMatchTMP-dev\ToneMatchTMP-v0.0.04
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r .\source\requirements.txt

Set-Location .\source
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
& ..\.venv\Scripts\python.exe app.py
```

이 스냅샷을 만든 환경의 핵심 버전은 다음과 같습니다. `requirements.txt`와 최종 빌드 환경도 같은 범위를 고정해야 합니다.

| 구성요소 | 확인 버전 |
|---|---:|
| Python | 3.12.13, x64 |
| NumPy | 2.2.6 |
| PyInstaller | 6.15.0 |
| Demucs | 4.1.0 |
| PyTorch | 2.13.0, CPU 경로 |
| SoundCard | 0.4.5 |
| FFmpeg | 9.0.1 Essentials |

공개 소스 저장소는 `https://github.com/JH-Prime/ToneMatchTMP`입니다. Git clone에는 대용량 `resources\ffmpeg.exe`가 없으므로 포터블 ZIP의 같은 파일을 복사한 뒤 실행·빌드합니다. ZIP을 기준으로 작업한다면 원본 ZIP과 SHA-256을 보존하고 `source` 폴더를 Git 작업 폴더로 사용하세요.

위 표는 포터블 CPU 기준입니다. 호환 NVIDIA PC에서 CUDA 소스 환경을 만들 때는 기본 테스트를 먼저 통과한 뒤 `source`에서 `.\enable_cuda.ps1`을 실행합니다. 이 스크립트는 `requirements-cuda126.txt`에 고정된 PyTorch CUDA 런타임을 설치합니다. 설치 후 `torch.cuda.is_available()`과 앱 성능 진단을 확인하고 전체 테스트·빌드를 다시 수행하세요. NVIDIA 드라이버·GPU·PyTorch 빌드가 호환되지 않으면 CPU 환경으로 돌아가야 합니다.

### 5. 첫 AI 모델 다운로드와 PC 간 캐시 이동

`separator.py`는 `adefossez/HTDemucs-6s`의 `htdemucs_6s` YAML·`safetensors`를 표준 Hugging Face 캐시에 받습니다.

기본 위치:

```text
%USERPROFILE%\.cache\huggingface\hub\models--adefossez--HTDemucs-6s
```

`HF_HOME`을 지정했을 때:

```text
%HF_HOME%\hub\models--adefossez--HTDemucs-6s
```

별도 드라이브에 캐시를 둘 예:

```powershell
$env:HF_HOME = "D:\ToneMatchTMP-model-cache"
& .\ToneMatchTMP-v0.0.04.exe
```

다른 PC에서 재다운로드하지 않으려면 모델의 배포 조건을 먼저 확인하고 `models--adefossez--HTDemucs-6s` 전체(`blobs`, `refs`, `snapshots` 포함)를 새 PC의 대응 경로로 복사합니다. 부분 다운로드나 실행 중이던 분석을 다른 PC에서 이어받는 기능은 보장하지 않습니다. 캐시 복사가 불완전하면 지우고 온라인 상태에서 다시 받는 편이 안전합니다.

모델 가중치는 포터블 개발 ZIP에 기본 포함하지 않습니다. 사용자 캐시, 토큰, 프록시 자격 증명도 압축에 넣지 마세요.

### 6. PC 재생음 녹음 점검

- `recorder.py`는 `soundcard.all_microphones(include_loopback=True)`로 입력과 loopback을 함께 열거합니다.
- `PC 재생음`은 실제 브라우저가 출력하는 장치와 같은 loopback 항목을 선택해야 합니다.
- 샘플 형식은 44.1 kHz, 16-bit, stereo이며 3초 미만은 폐기하고 20분에서 제한합니다.
- 알림음과 다른 앱의 소리도 함께 캡처될 수 있습니다.
- DRM·보호 경로 우회나 스트림 다운로드를 구현하지 않습니다.
- 녹음 장치가 없으면 Windows 오디오 드라이버, 출력 장치 활성화와 SoundCard 포함 여부를 확인합니다.

### 7. 테스트·자체 진단·빌드

```powershell
# 회귀 테스트
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v

# 소스 자체 진단
& ..\.venv\Scripts\python.exe app.py --self-test-output .\self-test-v0.0.04.json

# 테스트 후 PyInstaller 빌드
.\build.ps1

# 필요할 때만 테스트를 이미 통과한 동일 소스로 재빌드
.\build.ps1 -SkipTests
```

최종 배포 전에 최소한 다음 수동 검증을 수행합니다.

1. 기타 단독 WAV에서 AI 분리 생략, 모델 다운로드 없이 추천 3개 생성
2. 짧은 풀믹스에서 첫 모델 다운로드, guitar stem 분리와 추천 3개 생성
3. 모델 캐시가 있는 상태에서 네트워크 없이 같은 경로 재실행
4. WASAPI loopback으로 3초 이상 PC 재생음 녹음 후 분석
5. 최대 20분 제한, 끝 `0`/빈칸, 비정상 시간 입력과 취소 동작
6. 한국어↔English 전환 후 UI, 오류, JSON과 HTML 언어 확인
7. 지원하지 않는 장치에서 분석 버튼/오류 처리 확인
8. JSON·HTML 특수문자 이스케이프와 Tone Master Pro 수동 적용 안내 확인
9. 단음, 메이저/마이너 트라이어드, 전위와 무음에서 코드·보이싱 실험 결과 및 낮은 신뢰도 처리 확인
10. 자동/CPU 선택과 CUDA 미지원 폴백, 장치·VRAM 진단과 마지막 분석 벤치마크 표시 확인
11. 세 출력 경로에서 Amp/Cab 포함 규칙, 적용 순서와 Cabinet 컷 비중복 확인
12. CUDA 빌드라면 실제 NVIDIA GPU에서 짧은 분리, CPU 결과 비교, VRAM 회수와 취소 확인
13. EXE `--self-test-output` 결과의 `ok: true` 확인

### 8. 포터블 개발 ZIP 구성

포함:

- 전체 `*.py` 소스와 `tests`
- `resources\ffmpeg.exe`
- `ToneMatchTMP.spec`, `version_info.txt`, `build.ps1`, `requirements.txt`, `requirements-cuda126.txt`, `enable_cuda.ps1`
- `README_KO.md`, 이 문서, `BUILD_HISTORY.md`와 필요한 개발 문서
- `LICENSE.txt`, `THIRD_PARTY_NOTICES.txt`, `licenses`
- 최종 검증된 자체 진단 JSON; SHA-256 목록은 ZIP 옆 형제 파일로 제공
- 같은 소스에서 빌드한 EXE를 함께 전달할 경우 그 EXE

제외:

- `.venv`, `build`, `dist`, `__pycache__`
- Hugging Face/Demucs 모델 캐시와 미완료 다운로드
- 사용자 오디오·영상, 녹음 WAV, 분리 stem, JSON/HTML 개인 결과
- `%TEMP%\ToneMatchTMP-error.log`
- API 키, 토큰, 프록시·계정 정보와 개인 경로가 들어간 설정

대상 파일명은 `ToneMatchTMP-v0.0.04-Windows-x64-Portable-Dev.zip`입니다. EXE·ZIP·자체 진단의 최종 SHA-256은 패키징이 모두 끝난 뒤 형제 파일 `ToneMatchTMP-v0.0.04-SHA256SUMS.txt`와 `BUILD_HISTORY.md`에 기록합니다.

### 9. 릴리스 게이트

v0.0.04에서 다음 개발자가 재확인할 항목입니다. 실제 CUDA GPU, loopback 녹음과 코드 서명은 이번 릴리스 PC에서 검증되지 않았습니다.

- `catalog.APP_VERSION`, 최신 `CHANGELOG`, `version_info.txt`, spec의 EXE 이름과 모든 문서가 `0.0.04`인지
- spec에 `i18n.py`, `devices.py`, `separator.py`, `recorder.py`와 필요한 Demucs/PyTorch/SoundCard 런타임이 포함되는지
- `voicing.py`와 해당 테스트·표시 문자열이 포함되고, 실험 결과가 톤 추천 신뢰도와 혼동되지 않는지
- `requirements.txt`가 새 의존성을 재현 가능하게 고정하는지
- `THIRD_PARTY_NOTICES.txt`와 `licenses`가 Demucs, PyTorch, SoundCard, Hugging Face 관련 런타임/모델 조건을 반영하는지
- 개발자 소스 뷰가 신규 모듈까지 찾는지
- 전체 자동 테스트와 패키지 자체 진단이 통과하는지
- 최종 ZIP에 AI 가중치와 사용자 데이터가 섞이지 않았는지
- CPU 포터블 EXE가 CUDA 런타임을 잘못 포함하지 않고, 별도 CUDA 설치 파일·문서가 소스에 포함되는지
- 자동/CPU/CUDA 상태와 벤치마크가 사실대로 표시되고 GPU 미검증 사실이 릴리스 노트에 남는지
- 세 출력 경로의 Amp/Cab 정책과 적용 단계 회귀 테스트가 통과하는지

---

## English

### 1. Product contract

- App version: `0.0.04`
- Active target: Fender Tone Master Pro
- Target firmware/model guide: `1.8.58` / `Rev. J (2026-07)`
- Platform: 64-bit Windows with the Python 3.12 line
- Input: local audio/video or recorded Windows playback/audio input
- Range: at least 3 seconds and at most 20 minutes from Start; End `0`/blank means the remainder of the item, capped at 20 minutes
- Full mix: isolate the guitar with Demucs `htdemucs_6s`, then run DSP only on that guitar stem
- Guitar-only input: user can skip AI separation
- Output: three Tone Master Pro recipes, JSON, standalone HTML, clipboard text, and experimental chord/voicing cues
- Device control: no automatic write to Tone Master Pro or Pro Control
- Network: no audio upload and no YouTube extraction; the only content fetched directly by the app is the first-use AI model, while reference URLs are delegated to the external browser

The Quad Cortex, Helix Family, and unnamed device slots are UI extension placeholders and do not currently generate recipes.

Keep the version boundary explicit:

- `0.0.02`: Korean/English switching, extensible device selection, up-to-20-minute analysis, Demucs guitar stem, PC playback/audio-input recording, and cancellation
- `0.0.03`: portable developer archive, bilingual handoff, log/build history, and experimental NumPy chord/voicing analysis
- `0.0.04`: Auto/CPU/CUDA isolation selection, GPU/VRAM/inference diagnostics, native NumPy optimization, and output-route-aware Amp/Cab chains

The voicing output introduced in v0.0.03 is a separate diagnostic aid. Do not present it as complete polyphonic transcription, tablature, or performance grading.

### 2. Processing flow

```text
local audio/video
       or
SoundCard WASAPI loopback/audio input → temporary 44.1 kHz PCM16 WAV
       ↓
FFmpeg selected range, capped at 20 minutes
       ↓
resolve Auto/CPU/CUDA → Demucs htdemucs_6s for full mixes → guitar stem in outer 30-second chunks
       ↓
22.05 kHz analysis PCM → native NumPy DSP features + experimental chord/voicing cues
       ↓
pickup/output correction → 18-template match → three TMP recipes with route-aware Amp/Cab blocks
       ↓
GUI / JSON / HTML / clipboard text
```

The mixture WAV and guitar stem live in a temporary directory and are removed after analysis. There is no analysis checkpoint or intermediate-stem import. A cancelled or interrupted job must restart from the beginning; only a fully downloaded model cache is reusable.

The voicing API introduced in v0.0.03 is `analyze_voicings(samples, sample_rate, tuning_reference_hz=440.0, max_events=96)` plus `voicing_analysis_dict(analysis)`. It accepts the existing 22.05 kHz guitar buffer and returns deterministic time events with stable pitch-class/chord codes, bass/inversion, register/spacing cues, candidate shapes, and confidence. Candidate shapes always carry `detected: false`; never claim physical string/fret detection or complete tablature from audio alone. The outer `tonematch-tmp-recipe/v1` result stores the independent `tonematch-voicing/v1` object under `chord_voicing`.

The v0.0.04 compute contract uses stable `auto`, `cpu`, and `cuda` codes. Auto mode chooses CUDA when available and otherwise falls back to CPU; an explicit unsupported CUDA request must report the reason instead of silently relabeling a CPU run. Runtime diagnostics include the CUDA build, GPU model/capability, total/free VRAM, resolved device, total/per-chunk inference time, real-time factor, and peak GPU memory. The portable EXE remains CPU-based. `requirements-cuda126.txt` and `enable_cuda.ps1` define a separate source-development path for compatible NVIDIA PCs. No CUDA GPU was available on the release machine, so mock coverage and CPU fallback must not be described as real GPU validation.

Output routes are also contractual: FRFR/headphones/USB/PA use Amp Only plus Cabinet; a power amp feeding a real guitar cabinet uses Amp Only and retains the reference cabinet as comparison metadata; a guitar amp's front input omits both Amp and Cab. Do not duplicate Cabinet low/high cuts as another EQ block. The current Python app remains the reference implementation; C++ is future work limited to the real-time audio callback, ring buffer, FFT, and ASIO boundary.

### 3. Recreate the environment on another PC

Use this layout because `build.ps1` expects a sibling `..\.venv`:

```text
C:\ToneMatchTMP-dev\ToneMatchTMP-v0.0.04\
├─ .venv\                 recreate on the new PC
├─ ToneMatchTMP-v0.0.04.exe
└─ source\                self-contained development project
```

```powershell
Set-Location C:\ToneMatchTMP-dev\ToneMatchTMP-v0.0.04
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r .\source\requirements.txt

Set-Location .\source
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
& ..\.venv\Scripts\python.exe app.py
```

Do not reuse a copied virtual environment. It contains machine-specific paths and native wheels. The verified source environment used Python 3.12.13 x64, NumPy 2.2.6, PyInstaller 6.15.0, Demucs 4.1.0, PyTorch 2.13.0 on CPU, SoundCard 0.4.5, and FFmpeg 9.0.1 Essentials.

That is the portable CPU baseline. On a compatible NVIDIA PC, first verify the baseline environment, then run `.\enable_cuda.ps1` from `source`. It installs the pinned PyTorch CUDA runtime from `requirements-cuda126.txt`. Re-run the full suite, confirm `torch.cuda.is_available()` and the in-app GPU/VRAM diagnostics, then rebuild. A compatible NVIDIA driver, GPU, and PyTorch CUDA build are all required; never copy a virtual environment between PCs.

### 4. First model download and offline transfer

The default model cache is:

```text
%USERPROFILE%\.cache\huggingface\hub\models--adefossez--HTDemucs-6s
```

With `HF_HOME` set, it becomes:

```text
%HF_HOME%\hub\models--adefossez--HTDemucs-6s
```

To avoid downloading again on another PC, first check the model distribution terms, then copy the complete repository directory, including `blobs`, `refs`, and `snapshots`, to the corresponding cache root. Incomplete downloads and in-progress analyses are not portable or resumable. Do not include model weights, credentials, or user cache data in the development ZIP.

### 5. Build and release verification

```powershell
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
& ..\.venv\Scripts\python.exe app.py --self-test-output .\self-test-v0.0.04.json
.\build.ps1
```

Before release, manually exercise guitar-only bypass, first-download full-mix isolation, cached offline isolation, WASAPI loopback recording, 20-minute/end-zero handling, cancellation, both languages, unsupported-device behavior, JSON/HTML export, experimental chord/voicing confidence behavior, Auto/CPU selection and unavailable-CUDA behavior, three-route Amp/Cab policies, and the packaged EXE self-test. A CUDA build additionally requires an actual NVIDIA-GPU separation run, CPU comparison, VRAM cleanup, and cancellation check.

The target archive name is `ToneMatchTMP-v0.0.04-Windows-x64-Portable-Dev.zip`. Its `source` folder must be self-contained and include source, tests, FFmpeg, build metadata, base/CUDA setup files, documentation, and licenses alongside the EXE built from the same code. Record final artifact hashes only after packaging in the sibling checksum file and `BUILD_HISTORY.md`. Exclude virtual environments, build caches, model weights, personal media/results, raw logs, credentials, and machine-specific settings.

### 6. Resume checklist for the next developer or agent

1. Verify the archive hash and extract it to a writable local folder.
2. Read `README_KO.md`, this file, and `BUILD_HISTORY.md` before editing.
3. Recreate the sibling virtual environment and run the full test suite.
4. Confirm every version-bearing file says `0.0.04` and that `BUILD_HISTORY.md` keeps v0.0.02, v0.0.03, and v0.0.04 changes separate.
5. Confirm the PyInstaller spec includes the new modules and lazy AI/recording dependencies.
6. Confirm third-party notices and license files cover the added AI/recording stack and model terms.
7. Keep AI weights and user data out of the archive.
8. Verify CPU/CUDA diagnostics and all three Amp/Cab routes; do not claim real GPU validation without compatible hardware.
9. Replace pending placeholders with test, self-test, artifact-size, and SHA-256 results in `BUILD_HISTORY.md`.
10. If using a new Codex/task session, explicitly provide the extracted `source` folder (or clone `https://github.com/JH-Prime/ToneMatchTMP`) and ask it to treat these handoff documents as context. Chat history and interrupted analysis state are not embedded in the ZIP.
