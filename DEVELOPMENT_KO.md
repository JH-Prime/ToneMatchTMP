# ToneMatch TMP 개발자 안내서 · 0.0.07

이 문서는 구현 구조를 빠르게 이해하기 위한 한국어 요약입니다. 모든 함수의
이름·원본 줄·docstring은 `FUNCTION_REFERENCE_KO.md`, 새 PC 재구성과 릴리스
절차는 `DEVELOPER_HANDOFF_KO_EN.md`를 함께 보세요.

현재 릴리스·빌드 기준일은 2026-09-08 KST입니다. v0.0.07은 실험 코드 추정의
반복 근거·잡음·배음·역상 처리를 보완하고, 약한 분리 기타의 원본 믹스 화성 참고와
작은 작업 영역의 UI를 추가 보완합니다. v0.0.06의 Reference Compare와 진행률,
v0.0.05의 실시간 모니터는 유지합니다. 실제 검증 완료 여부는
`QA_REPORT_v0.0.07.json`과 `BUILD_HISTORY.md`에 기록하며 이 문서로 대신하지 않습니다.

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
[05 기타 stem NumPy 네이티브 DSP 특징·Reference 스펙트럼 추출]
       ↓
[06 코드 보이싱 분석(실험) · 근거 부족 시 별도 원본 화성 참고]
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

### v0.0.07 코드 출처·화성 참고·화면 배치 계약

- `voicing.py`는 채널별 스펙트럼으로 좌우 역상 상쇄를 피하고, 독립 피치 피크와
  잡음·배음 억제 및 반복되는 시간 근거를 사용합니다. 불충분한 근거는 `unknown`으로
  유지하며 검출 구간이 늘었다는 사실을 코드 정답률 향상으로 표현하지 않습니다.
- `engine._analyze_chord_sources`는 분리 기타가 약하거나 코드 근거가 부족할 때만
  원본 파일의 동일 선택 구간을 추가 분석합니다. 선택된 결과는 `analysis_source`가
  `original_mix`인 화성 참고이며, 기타 운지·저음/역위·음역·간격 정보는 제거합니다.
- 톤 특징·레시피와 Reference는 기존 최종 분석 PCM 그대로 사용합니다. 원본 화성
  참고의 선택 여부가 해당 신호나 결과를 바꾸면 안 됩니다. 무음 수준의 톤 입력은
  계속 오류이며, 매우 약하지만 분석 가능한 분리 신호는 경고와 함께 구분합니다.
- 선택적 원본 디코딩·화성 실패는 기타 결과를 유지하지만 사용자의 취소는 전파합니다.
  출처, 선택 시작 오프셋, 미확정 이벤트와 진단값은 JSON·GUI·HTML에 일관되게 남깁니다.
- `i18n.voicing_context_lines`는 한국어·영어 출처·진단·실패 안내를 공유하고,
  `report.py`는 해당 안내와 이벤트·후보 문자열을 HTML 이스케이프합니다.
- `app.py`는 Windows 작업 영역을 고려해 초기 창을 배치합니다. 입력 폼과 분석
  하단 영역을 분리하고, 상태 문구는 고정 높이의 스크롤 가능한 Text로 제한합니다.
  폼 스크롤 범위를 내용 높이에 맞추며 결과 제목과 동작 버튼을 별도 행으로 배치합니다.
- 숨긴 Tk 창의 배치 회귀와 실제 EXE의 시각 확인은 별개입니다. 전체 테스트·실제
  MP3·소스/패키지 자체 진단·최종 ZIP 검증 상태를 QA에 각각 기록합니다.

### v0.0.06 분석 진행률·모델 준비 계약

- `app.py`는 외부 라이브러리를 import하기 전에 `sys.stdout`·`sys.stderr`가
  `None`인 경우에만 안전한 출력 스트림을 연결합니다. 콘솔 없는 PyInstaller EXE의
  진행 출력이 `'NoneType' object has no attribute 'write'`로 실패하지 않게 합니다.
- 일반 분석 화면에 단계 가중 전체 %와 경과 `mm:ss`를 표시합니다. Tk의 250 ms
  타이머는 경과 시간만 갱신하며, 실제 콜백을 기다리는 동안 %를 임의로 올리지
  않습니다. 전체 %는 단계 배분이지 남은 시간의 비율이나 ETA가 아닙니다.
- `separator.py`는 공식 `adefossez/HTDemucs-6s` YAML·safetensors를
  `local_files_only=True`로 먼저 확인한 뒤 누락 파일만 받습니다. 명시적인 모델
  로더를 사용하여 Hugging Face 오류 뒤 예전 모델 다운로드로 조용히 폴백하지 않습니다.
- 다운로드용 `tqdm`은 콘솔에 그리지 않고 실제 수신 바이트를 앱 콜백에 전달합니다.
  총량을 알 때만 파일 %를 계산하며 캐시 확인·수신·메모리 로딩을 구분합니다.
- Demucs의 30초 외부 조각은 유지하되 내부 분할 콜백의 완료 블록을 누적합니다.
  모델별 stride·overlap과 완료 블록을 반영한 음원 처리 초를 전체 분리 구간 진행률에
  대응시키며, CPU 처리 중 시간만으로 추론 완료량을 꾸미지 않습니다.
- 취소는 다운로드 콜백과 내부 블록 시작·종료 경계에서 확인합니다. 진행 중인 추론
  블록이나 네트워크 대기를 즉시 강제 종료하지 않으므로 반영이 지연될 수 있습니다.
- 모델 준비 예외 체인을 서버·네트워크, 캐시 권한·디스크, 메모리 부족, 기타
  모델·런타임으로 분류합니다. 모든 예외를 인터넷 미연결로 설명하지 않습니다.
  현행 오디오·EXE 검증 결과는 `QA_REPORT_v0.0.07.json`과 `BUILD_HISTORY.md`를
  기준으로 하며 이 구현 설명 자체는 해당 검증의 성공 증거가 아닙니다.

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

## Reference Compare 처리 시퀀스

Reference 생성은 파일 분석 경로에, Current 갱신은 기존 실시간 모니터 경로에
붙습니다. 같은 장치를 여는 별도의 두 번째 캡처 세션은 만들지 않습니다.

```text
[분석에 실제 사용한 PCM: 분리 guitar stem 또는 분리 생략 로컬 소스]
       ↓ 활성 프레임 표본 · 채널별 Hann FFT power 누적
[레벨 정규화 Reference 주파수 프로필 + 6밴드 집계]
       ↓ 분석 결과 JSON에 저장
[Reference Compare 탭]
       ↑
[기존 Live Spectrum의 최신 Current 프레임]
       ↓ Reference 주파수 그리드로 보간 · 전체 power 정규화
[Low / Low Mid / Mid / Presence / Treble / Air]
       ↓
[Reference | Current | Δ(Current−Reference) + 0 dB 중심 차이 그래프]
```

입력 게인으로 비교 결과가 좌우되지 않게 Reference와 Current의 전체 power를 각각
정규화합니다. 따라서 Δ는 레벨 정규화된 톤 형상 차이이며 정확도 확률이나 Match %가
아닙니다. Reference가 없으면 Current만으로 비교 결과를 생성하지 않습니다.

## 모듈 구성

| 파일 | 역할 |
|---|---|
| `app.py` | Tkinter 화면, 한·영 전환, 연산 장치·성능 진단, 분석·녹음·스펙트럼 작업 스레드, 수치 진행률·경과 시간, 콘솔 없는 출력 보호, Canvas 표시, 취소, 결과/보이싱 탭, 로그, 디버그 번들, 자체 진단 |
| `engine.py` | FFmpeg 구간 변환, PCM 로딩, NumPy DSP, 기타 분리 호출, 코드 전용 원본 화성 참고 선택, 출력 경로별 Amp/Cab 조립, 템플릿 매칭과 결과 스키마 |
| `separator.py` | Demucs `htdemucs_6s` 캐시 우선 명시 로더, 실제 다운로드·내부 블록 진행, 원인별 모델 오류, 자동/CPU/CUDA 선택·폴백, VRAM/추론 벤치마크, 30초 외부 조각, guitar stem WAV |
| `recorder.py` | SoundCard 기반 Windows WASAPI loopback/오디오 입력 열거, PCM16 녹음, 실시간 2,048-frame float32 블록 전달 |
| `spectrum.py` | 입력 정규화, 채널별 FFT power, 20 Hz~20 kHz 스펙트럼·dBFS·중심 주파수 계산과 4프레임 평활화 |
| `reference_compare.py` | 분석 PCM의 레벨 정규화 Reference 프로필, 6밴드 집계, 실시간 Current 보간과 `Δ(Current−Reference)` 계산 |
| `voicing.py` | 채널별 스펙트럼, 독립 피치·잡음/배음 억제, 반복 근거·미확정 이벤트·진단, 제한된 코드 템플릿과 기타 소스의 보이싱 후보(실험) |
| `catalog.py` | 앱/펌웨어/가이드 버전, 패치 기록, 18개 Tone Master Pro 톤 템플릿 |
| `devices.py` | Tone Master Pro 지원 프로필과 Quad Cortex/Helix 미구현 자리 |
| `i18n.py` | 한국어/영어 문자열, 안정적인 선택 코드와 화면 라벨 변환, GUI/HTML 공통 코드 출처·진단 안내 |
| `report.py` | 언어별 클립보드 텍스트와 독립형 HTML 결과 |
| `debug_info.py` | 11개 처리 블록, 진행률 매핑, AST 기반 실제 소스 추출 |
| `tests/` | 엔진·내보내기·보이싱·스펙트럼 DSP·녹음 스트림·Tk 표시·개발자 모드 회귀 테스트 |
| `tools/` | 함수 색인, 라이선스 목록, 포터블 manifest 생성 도구 |
| `ToneMatchTMP.spec` | PyInstaller onedir와 동적 Demucs/Hugging Face 모듈 수집 |
| `build.ps1` | 테스트, 라이선스 수집, 빌드, 자체 진단, 포터블 개발 ZIP, SHA-256 |

## 데이터와 오디오 경계

- 로컬 파일/녹음은 최대 20분이며 끝 `0` 또는 빈칸은 파일 끝까지를 뜻합니다.
- 풀믹스의 톤 특징·Reference·레시피는 44.1 kHz PCM에서 분리한 Demucs guitar stem의
  22.05 kHz 분석 버퍼만 사용합니다. 코드 전용 화성 참고는 원본의 같은 구간을 별도로
  읽을 수 있지만 톤 분석 버퍼를 교체하지 않습니다. 기타 단독 파일은 분리를 건너뜁니다.
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

### v0.0.06 Reference Compare 경계

기준 프로필은 최대 384개 활성 표본 프레임의 2,048-point Hann FFT를 192개 로그
셀에 파워 보존 방식으로 투영합니다. 기준과 Current 모두 peak 대비 80 dB 미만
성분을 제외하며, 총 파워 대비 −80 dB와 라이브 dBFS 측정 한계로부터 계산한
공통 관측 하한을 표시값에 적용합니다. RMS −75 dBFS 이하 입력은 비교에서
제외합니다. Current/Δ는 세션 상태이며 JSON/HTML에는 기준 프로필만 저장합니다.
자동 UI 테스트는 숨긴 Tk 창과 지정한 Canvas 크기를 사용하므로 실제 창 배치의
수동 시각 점검과 구분합니다.

- Reference는 `engine.analyze_file`이 최종 분석에 사용한 PCM에서 생성합니다. 풀믹스는
  Demucs guitar stem, 분리 생략은 디코딩한 로컬/녹음 소스이므로 참고 URL의 오디오를
  직접 가져오지 않습니다.
- 긴 신호는 제한된 수의 활성 프레임을 고르게 표본화해 FFT power를 누적합니다. 채널은
  파형을 모노로 상쇄시키지 않고 채널별 power 뒤에 평균합니다.
- Current는 새 오디오 스트림이 아니라 v0.0.05 Live Spectrum의 최신 프레임입니다.
  샘플레이트가 달라도 Reference 그리드로 보간한 뒤 양쪽 전체 power를 정규화합니다.
- 고정 대역은 Low, Low Mid, Mid, Presence, Treble, Air이며 Δ의 부호는 항상
  `Current−Reference`입니다. 양수는 Current가, 음수는 Reference가 더 강함을 뜻합니다.
- 이 비교는 통계적 정확도, 기존 레시피 순위의 유사도 또는 Match %가 아닙니다.
  Brightness·Body·Gain·Compression·Ambience 실시간 미터도 이 버전에 포함하지 않습니다.
- 자동 EQ/TMP 파라미터 추천·적용, 프리셋 쓰기, C++/ASIO/WASAPI Exclusive는
  구현하지 않습니다. 무음·비유한 값과 공통 나이퀴스트 범위 밖은 안전하게 처리합니다.

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
v0.0.05~v0.0.07도 Python을 UI, 파일 처리, Demucs 실행, 레시피·리포트 조립,
실시간 스펙트럼과 Reference Compare의 기준 구현으로 유지합니다.

후속 실시간 톤 매칭에서 지연 시간이 엄격한 오디오 콜백, lock-free 링 버퍼, FFT와
ASIO 입출력이 필요해질 때 그 경계를 C++ 모듈로 분리하고 Python에는 안정적인 API만
노출합니다. 이 계획은 v0.0.04~v0.0.07에 구현된 항목이 아닙니다.

## 코드 보이싱 결과의 의미

`engine.analyze_file` 결과의 `chord_voicing`은 독립 스키마
`tonematch-voicing/v1`을 담습니다. 각 이벤트는 시간, 코드 기호, 구성 피치 클래스와
근거 신뢰도를 포함합니다. 기타 소스에서는 최저음/역위·음역·간격·연주 후보도
제공할 수 있지만, `original_mix` 화성 참고에서는 이 기타 전용 정보를 제거합니다.
`source_start_seconds`를 더한 원본 시각으로 표시하고 미확정 구간을 숨기지 않습니다.

오디오만으로 같은 음높이를 만든 실제 줄·프렛 조합은 유일하게 복원되지 않습니다.
따라서 후보 운지는 항상 `detected: false`이며 검출 타브로 표현하지 않습니다.
왜곡·드롭 튜닝·카포·벤딩·분리 누출에서는 결과가 틀릴 수 있습니다.

## 디버깅과 테스트

```powershell
# 프로젝트 폴더의 형제 위치에 Python 3.12 가상환경을 만든 경우
& ..\.venv\Scripts\python.exe -m compileall -q .
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
& ..\.venv\Scripts\python.exe app.py --self-test-output .\self-test-v0.0.07.json
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
   파일명을 다음 패치인 `0.0.08`로 정확히 한 단계 올립니다. 현행 `0.0.07`의
   검증을 먼저 마치고 v0.0.06 이하의 역사 기록은 변경하지 않습니다.
4. 함수 색인과 제3자 라이선스 목록을 다시 생성합니다.
5. 단위 테스트, 소스 자체 진단, 실제 짧은 Demucs 분리, 패키지 자체 진단을
   통과시킵니다.
6. 포터블 ZIP과 SHA-256을 만들고 `BUILD_HISTORY.md`에 검증 결과를 기록합니다.
7. 개인 오디오·URL·로그·모델 캐시·EXE·ZIP을 제외한 소스와 문서를 GitHub에
   커밋합니다.
