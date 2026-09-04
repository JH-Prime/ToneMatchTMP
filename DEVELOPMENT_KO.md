# ToneMatch TMP 개발자 안내서 · 0.0.05

이 문서는 구현 구조를 빠르게 이해하기 위한 한국어 요약입니다. 모든 함수의
이름·원본 줄·docstring은 `FUNCTION_REFERENCE_KO.md`, 새 PC 재구성과 릴리스
절차는 `DEVELOPER_HANDOFF_KO_EN.md`를 함께 보세요.

현재 릴리스·빌드 기준일은 2026-09-05 KST입니다. v0.0.05는 기존 v0.0.04의
오프라인 분석·CUDA 진단·Amp/Cab 계약을 유지하면서 별도의 원시 입력 실시간
스펙트럼 경로를 추가합니다.

## 파일 분석·레시피 처리 시퀀스

```text
[01 앱 초기화]
       ↓
[02 입력 검증/PC 재생음 녹음]
       ↓
[03 FFmpeg 디코딩 · 최대 20분]
       ↓
[04 연산 장치 결정 · Demucs 6-stem AI 기타 분리]
       ↓
[05 기타 stem NumPy 네이티브 DSP 특징 추출]
       ↓
[06 코드 보이싱 분석(실험)]
       ↓
[07 기타 소스/픽업/출력 보정]
       ↓
[08 18개 톤 템플릿 매칭]
       ↓
[09 Tone Master Pro 블록·파라미터 생성]
       ↓
[10 결과·경고·진단 조립]
       ↓
[11 JSON · HTML · 클립보드 내보내기]
```

앱에서 `개발자 옵션`을 켜면 같은 순서가 블록 다이어그램으로 표시됩니다.
각 블록을 클릭하면 그 단계의 설명, 입력·출력, 실제 배포 함수 원문과 줄 번호가
나옵니다. 함수에는 모두 한국어 docstring이 있으며 테스트가 누락을 검사합니다.

## 실시간 스펙트럼 처리 시퀀스

실시간 탭은 위 레시피 처리 시퀀스에 신호를 공급하지 않는 독립 경로입니다.

```text
[선택한 WASAPI 오디오 입력 또는 PC 재생음 loopback]
       ↓ 44.1 kHz · 2채널 · 2,048-frame 블록(초당 약 21.5개)
[채널별 Hann-window FFT power → 채널 power 평균]
       ↓
[20 Hz~20 kHz bin · RMS/Peak dBFS · 스펙트럼 중심 주파수]
       ↓
[최근 4프레임 선형 power 평활화 · 최신 파형 유지]
       ↓
[용량 1 bounded 큐: 오래된 화면 프레임 교체]
       ↓ UI가 50 ms마다 poll(약 20 Hz)
[Tk Canvas: 입력 파형 + 로그 주파수 스펙트럼 + 수치]
```

블록 캡처 주기와 UI 그리기 주기를 분리했으므로 UI가 잠시 늦어져도 측정 프레임이
무한히 쌓이지 않습니다. 각 세션은 별도 중지 이벤트와 세션 ID를 사용해 종료 뒤의
낡은 프레임을 버립니다.

## 모듈 구성

| 파일 | 역할 |
|---|---|
| `app.py` | Tkinter 화면, 한·영 전환, 연산 장치·성능 진단, 분석·녹음·스펙트럼 작업 스레드, Canvas 표시, 취소, 결과/보이싱 탭, 로그, 디버그 번들, 자체 진단 |
| `engine.py` | FFmpeg 구간 변환, PCM 로딩, NumPy DSP, 기타 분리 호출, 출력 경로별 Amp/Cab 조립, 템플릿 매칭과 결과 스키마 |
| `separator.py` | Demucs `htdemucs_6s` 모델 캐시 확인, 자동/CPU/CUDA 선택·폴백, VRAM/추론 벤치마크, 30초 외부 조각, guitar stem WAV |
| `recorder.py` | SoundCard 기반 Windows WASAPI loopback/오디오 입력 열거, PCM16 녹음, 실시간 2,048-frame float32 블록 전달 |
| `spectrum.py` | 입력 정규화, 채널별 FFT power, 20 Hz~20 kHz 스펙트럼·dBFS·중심 주파수 계산과 4프레임 평활화 |
| `voicing.py` | 캐시·NumPy 벡터 연산 기반 시간창 chroma, 제한된 코드 템플릿, 베이스/역위·음역·간격과 연주 후보(실험) |
| `catalog.py` | 앱/펌웨어/가이드 버전, 패치 기록, 18개 Tone Master Pro 톤 템플릿 |
| `devices.py` | Tone Master Pro 지원 프로필과 Quad Cortex/Helix 미구현 자리 |
| `i18n.py` | 한국어/영어 문자열, 안정적인 선택 코드와 화면 라벨 변환 |
| `report.py` | 언어별 클립보드 텍스트와 독립형 HTML 결과 |
| `debug_info.py` | 11개 처리 블록, 진행률 매핑, AST 기반 실제 소스 추출 |
| `tests/` | 엔진·내보내기·보이싱·스펙트럼 DSP·녹음 스트림·Tk 표시·개발자 모드 회귀 테스트 |
| `tools/` | 함수 색인, 라이선스 목록, 포터블 manifest 생성 도구 |
| `ToneMatchTMP.spec` | PyInstaller onedir와 동적 Demucs/Hugging Face 모듈 수집 |
| `build.ps1` | 테스트, 라이선스 수집, 빌드, 자체 진단, 포터블 개발 ZIP, SHA-256 |

## 데이터와 오디오 경계

- 로컬 파일/녹음은 최대 20분이며 끝 `0` 또는 빈칸은 파일 끝까지를 뜻합니다.
- 풀믹스는 44.1 kHz PCM으로 바꾼 뒤 Demucs guitar stem만 22.05 kHz 분석
  버퍼로 보냅니다. 기타 단독 파일은 분리를 건너뜁니다.
- 모델 가중치는 ZIP·Git에 넣지 않습니다. 첫 풀믹스 분석 때 Hugging Face
  사용자 캐시로 내려받습니다.
- 혼합 WAV와 stem은 임시 폴더에서 삭제되며 중간 체크포인트는 없습니다.
- YouTube 스트림을 다운로드하지 않습니다. 권한 있는 로컬 파일 또는 브라우저의
  정상 재생음을 WASAPI loopback으로 녹음합니다.
- Tone Master Pro 프리셋에 자동 쓰지 않고 사용자가 추천값을 수동 입력합니다.

### v0.0.05 실시간 스펙트럼 경계

- 녹음 목록과 같은 선택 WASAPI 입력/loopback을 공유 모드로 엽니다. 44.1 kHz에서
  2,048-frame 블록은 초당 약 21.5개이며, UI는 50 ms마다 최신 프레임을 poll해
  약 20 Hz로 갱신합니다. 둘은 같은 시간 기준을 뜻하지 않습니다.
- 최신 PCM 블록의 채널별 FFT power를 먼저 계산하고 채널 사이에서 power를 평균합니다.
  따라서 좌우 역상 신호가 모노 평균으로 사라지는 문제를 피합니다.
- 스펙트럼과 RMS는 최근 4프레임의 선형 power 평균, Peak는 같은 창의 최댓값,
  파형은 최신 프레임을 사용합니다. 출력은 로그 20 Hz~20 kHz 스펙트럼,
  RMS/Peak dBFS와 스펙트럼 중심 주파수입니다.
- 작업 스레드에서 UI로 보내는 `Queue(maxsize=1)`는 가득 차면 이전 값을 버리고
  최신 프레임만 남깁니다. 중지 뒤에는 마지막으로 그린 프레임을 유지합니다.
- 원시 입력 시각화만 제공하며 Demucs 분리, `ToneFeatures`, 템플릿 매칭,
  레시피 결과와 연결하지 않습니다. 녹음·분석·하드웨어 검사·언어 재구성과도
  동시에 실행하지 않아 하나의 캡처 장치를 두 작업이 경쟁하지 않게 합니다.
- 이 경로는 Python/NumPy + SoundCard/WASAPI 공유 모드입니다. C++ 오디오 콜백,
  ASIO, WASAPI Exclusive 또는 하드 실시간 엔진으로 표현하지 않습니다.

## 연산 장치와 출력 경로 경계

- 연산 선택 코드는 `auto`, `cpu`, `cuda`입니다. `auto`는 CUDA를 사용할 수 있을 때
  CUDA를 고르고, 아니면 CPU로 안전하게 폴백합니다. 명시적 `cuda` 요청은 사용할 수
  없을 때 조용히 결과를 바꾸지 않고 원인을 오류로 알립니다.
- 하드웨어 진단은 UI를 멈추지 않는 별도 작업에서 CUDA 빌드, GPU 이름·연산 능력,
  총/여유 VRAM을 확인합니다. 분석 뒤에는 실제 선택 장치, 전체/조각별 추론 시간,
  실시간 배수와 최대 GPU 메모리를 결과에 보존합니다.
- 배포용 포터블 EXE는 CPU 런타임을 포함합니다. CUDA 개발 빌드는 호환 NVIDIA PC에서
  `enable_cuda.ps1`과 `requirements-cuda126.txt`로 별도 환경을 만든 뒤 검증합니다.
  이번 릴리스 PC에는 CUDA GPU가 없어 실제 GPU 실행은 하드웨어 검증하지 못했습니다.
- FRFR/헤드폰/USB/PA는 Amp Only + Cabinet, 실제 기타 캐비닛에 연결한 파워앰프는
  Amp Only, 기타 앰프 전면 입력은 Amp/Cab 없음이 계약입니다. 각 경로는 별도 적용
  단계와 적합도 라벨을 가지며, Cabinet 로우/하이 컷을 독립 EQ로 중복하지 않습니다.

## Python과 C++의 경계

v0.0.04는 전체 앱을 C++로 재작성하지 않고 NumPy와 PyTorch가 이미 사용하는
컴파일된 네이티브 벡터·텐서 연산에 반복 계산을 모아 오프라인 분석을 최적화했습니다.
v0.0.05도 Python을 UI, 파일 처리, Demucs 실행, 레시피·리포트 조립과 실시간
스펙트럼의 기준 구현으로 유지합니다.

후속 실시간 톤 매칭에서 지연 시간이 엄격한 오디오 콜백, lock-free 링 버퍼, FFT와
ASIO 입출력이 필요해질 때 그 경계를 C++ 모듈로 분리하고 Python에는 안정적인 API만
노출합니다. 이 계획은 v0.0.04에도 v0.0.05에도 구현된 항목이 아닙니다.

## 코드 보이싱 결과의 의미

`engine.analyze_file` 결과의 `chord_voicing`은 독립 스키마
`tonematch-voicing/v1`을 담습니다. 각 이벤트는 시간, 코드 기호, 구성 피치 클래스,
최저음/역위, 음역, 간격, 신뢰도와 연주 가능한 후보 운지를 포함합니다.

오디오만으로 같은 음높이를 만든 실제 줄·프렛 조합은 유일하게 복원되지 않습니다.
따라서 후보 운지는 항상 `detected: false`이며 검출 타브로 표현하지 않습니다.
왜곡·드롭 튜닝·카포·벤딩·분리 누출에서는 결과가 틀릴 수 있습니다.

## 디버깅과 테스트

```powershell
# 프로젝트 폴더의 형제 위치에 Python 3.12 가상환경을 만든 경우
& ..\.venv\Scripts\python.exe -m compileall -q .
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
& ..\.venv\Scripts\python.exe app.py --self-test-output .\self-test-v0.0.05.json
& ..\.venv\Scripts\python.exe app.py
```

실행 로그는 우선 EXE 옆 `data\logs`에 기록되고 쓰기 권한이 없으면
`%LOCALAPPDATA%\ToneMatchTMP\logs`를 사용합니다. 앱의 `디버그 번들 ZIP`은
현재 세션 로그, 일별 로그, 실제 배포 소스, 변경 기록과 런타임 상태를 묶습니다.

## 빌드

Git 저장소는 대용량 `resources\ffmpeg.exe`를 추적하지 않습니다. 포터블 개발
ZIP에서 해당 파일을 복사한 뒤 실행하세요.

```powershell
& ..\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\build.ps1 -OutputDir C:\원하는\출력폴더
```

호환 NVIDIA PC에서 CUDA 소스 빌드를 만들 때만 기본 환경 검증 후 실행합니다.

```powershell
.\enable_cuda.ps1
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\build.ps1 -OutputDir C:\원하는\출력폴더
```

빌드는 PyInstaller onedir 런타임, 소스, 테스트, 문서, 라이선스, 빌드 재료,
로그 자리, 자체 진단, 파일별 manifest와 ZIP SHA-256을 생성합니다. 모델 가중치가
들어오면 manifest 단계가 실패하도록 막았습니다.

## 패치 버전 절차

1. 재현 테스트를 추가하고 코드를 수정합니다.
2. 모든 함수의 한국어 docstring과 사용자용 한·영 문자열을 유지합니다.
3. `catalog.APP_VERSION`, 최신 `CHANGELOG`, `version_info.txt`, spec, 문서와
   파일명을 다음 패치인 `0.0.06`으로 정확히 한 단계 올립니다.
4. 함수 색인과 제3자 라이선스 목록을 다시 생성합니다.
5. 단위 테스트, 소스 자체 진단, 실제 짧은 Demucs 분리, 패키지 자체 진단을
   통과시킵니다.
6. 포터블 ZIP과 SHA-256을 만들고 `BUILD_HISTORY.md`에 검증 결과를 기록합니다.
7. 개인 오디오·URL·로그·모델 캐시·EXE·ZIP을 제외한 소스와 문서를 GitHub에
   커밋합니다.
