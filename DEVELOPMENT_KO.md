# ToneMatch TMP 개발자 안내서 · 0.0.12

이 문서는 구현 구조를 빠르게 이해하기 위한 한국어 요약입니다. 모든 함수의
이름·원본 줄·docstring은 `FUNCTION_REFERENCE_KO.md`, 새 PC 재구성과 릴리스
절차는 `DEVELOPER_HANDOFF_KO_EN.md`를 함께 보세요.

빌드 기준일은 2026-10-02 KST입니다. v0.0.12는 오디오 코드 후보를 20→41종으로
확장하고 바깥쪽 세 번째 `코드·스케일 사전` 작업 탭을 추가합니다. 음원과 독립적인
12근음의 코드·건반 참고, 12종 스케일과 장음계·자연단음계 다이어토닉을 제공합니다.
기존 선택 악기 제거, GUI 없는 실제 모델 진단과 C ABI 2 실시간 DSP는 유지합니다.

10월 2일 자동 테스트 282개와 소스·EXE 진단, 10월 3일 실제 CPU 모델의
전체 곡 제거·취소 및 새 ZIP 압축 해제 검증을 통과했습니다.
`QA_REPORT_v0.0.12.json`과 `BUILD_HISTORY.md`를 릴리스 게이트의 근거로 사용합니다.
서명되지 않은 CPU 개발자 프리릴리스입니다. 합성 회귀는 실제 곡의 정확도나 기타
운지 복원을 입증하지 않습니다. 숨긴 창·GUI 없는 검사는 수동 UI·청감·첫 다운로드·
네트워크 차단·CUDA·실제 캡처 검증을 대신하지 않습니다.

## v0.0.12 코드·스케일 사전과 확장 화음 계약

- `voicing.CHORD_INTERVALS`/`CHORD_SUFFIX`는 41종 오디오 후보를 정의합니다.
  이전 20종에 7sus2, 11·maj11·min11, 13·maj13·min13, minmaj7·minmaj9,
  6add9·min6add9, 7b5·7sharp5·7b9·7sharp9·7sharp11·7b13,
  maj7sharp5·maj7sharp11, add11·minadd11을 추가합니다.
- 시간 연결 후보와 표시용 근접 대안을 분리합니다. 구성음 존재·설명력·최소 근거
  점수를 모두 통과한 후보 중 인접 창에서도 같은 이름이 지지되는 후보를 경로 선택
  전에 남깁니다. 선택 후에도 단발 이름을 거부하며 무음·없는 음을 이웃에서 복사하지
  않습니다. 코드 종류가 늘어도 순간 확장음이 반복되는 기본 화음의 근거를 지우지
  않도록 한 보완이며, 실제 곡의 정답률이나 모든 구성음의 악기 출처를 확정하지 않습니다.
- `harmony_reference.py`는 공유 코드 구성음을 이론 도수·음이름과 대조합니다.
  41유형 × 12근음의 492개 코드 정의와 12스케일 × 12근음의 144개 음계 정의를
  오디오·네트워크 없이 만드는 읽기 전용 API입니다. 스케일 자동 판정기가 아닙니다.
- `chord_options`/`scale_options`/`diatonic_options`와
  `get_chord_reference`/`get_scale_reference`/`get_diatonic_reference`는
  JSON 직렬화 가능한 새로운 사전을 반환합니다. 반환값 변경은 공유 정의를 바꾸지 않습니다.
- C♯ 메이저의 E♯·B♯, E♭ 자연단음계의 C♭, 감7화음의 ♭♭7처럼 도수 철자를
  유지합니다. 피치 클래스와 별도로 `intervals`에 9=14·11=17·13=21 반음을
  보존해 상위 옥타브를 그립니다. 실제 연주의 역위·생략음·운지를 검출한 것은 아닙니다.
- 스케일 12종은 major/Ionian, natural minor/Aeolian, major/minor pentatonic,
  harmonic minor, ascending melodic minor, Dorian, Phrygian, Lydian,
  Mixolydian, Locrian, six-note minor blues입니다. 펜타토닉을 코드 유형에 추가하지 않습니다.
- 다이어토닉은 장음계·자연단음계 각각의 7도수에서 3화음·7화음을 보여 줍니다.
  12근음 × 2음계 × 7도수 × 2화음 = 336개 구성음 관계입니다.
  자연단음계의 v를 화성단음계의 V로 바꾸지 않고 문맥에 맞는 근음 철자도 유지합니다.
- 사전 UI는 세 번째 바깥 탭에서 근음·분류·유형을 선택하며 음원 없이 열립니다.
  음원 분석의 미확정 구간을 채우거나 톤 특징·레시피를 바꾸지 않습니다.
- 현행 고정 합성 벤치마크 984개(41유형 × 12근음 × 2음색)는 기대한 대표 이름
  일치가 v0.0.11의 480개에서 v0.0.12의 984개로 증가했고 비화음 대조 36개는
  두 버전 모두 거부했습니다. 이 결과는 합성 조건만의 비교이며 실제 곡 정확도가 아닙니다.
- 음악 이론 기준은 [펜타토닉 설명](https://hub.yamaha.com/guitars/g-how-to/a-guitarists-guide-to-major-and-minor-pentatonic-scales/),
  [단음계 형태](https://musictheory.pugetsound.edu/mt21c/MinorScales.html),
  [다이어토닉 7화음](https://musictheory.pugetsound.edu/mt21c/RomanNumeralsOfDiatonicSeventhChords.html)을 참고합니다.

## v0.0.11 코드·보이싱 및 입력 계약 · 역사 기록

아래 20유형·480개 비교와 Room 335 수치는 v0.0.11 당시 기록이며 현행 검증이 아닙니다.

- 20종 템플릿과 구성음 설명력·복잡도 비용으로 확장음을 포함한 화음을 비교합니다.
  모든 후보는 해당 분석 창의 구성음 근거와 최소 점수 0.34를 통과해야 합니다.
  베이스는 근접 해석의 선호를 제공할 뿐 음악적 근음을 확정하지 않습니다.
- `VoicingEvent.alternatives`와 `evidence`는 v1 스키마의 추가 필드입니다.
  관측/필요 피치 클래스, 휴리스틱 점수 차이, 모호성, 해당 이벤트의 분석 창 수를
  보존합니다. 창 개수는 곡 전체 정확도가 아니며 미확정 이벤트는 근거를 비웁니다.
- 고정 480개 합성 비교는 186→480개 대표 이름 일치, 36개 비화음 대조는 전부 거부입니다.
  실제 Room 335의 원본 믹스 근거 창은 68/421(16.15%)이며 미확정이 많습니다.
  정답 주석이 없는 실제 실행을 정확도 평가로 간주하지 않습니다.
- 코드 분석과 톤 추천은 별개입니다. 관측 피치 근거와 화음 후보를 구분하고,
  모호한 해석은 대안 후보로 표시합니다. 근거 점수를 보정된 정확도 확률처럼
  설명하거나 `실험` 표기 제거만으로 채보 품질이 보증된다고 주장하지 않습니다.
- 원본 믹스 화성 참고에는 건반·베이스 등이 포함될 수 있으므로 기타 줄·프렛,
  최저음/역위·음역·간격 추정을 표시하지 않는 기존 경계를 유지합니다.
- 정확한 줄·프렛은 같은 음높이에 여러 운지가 가능해 음원만으로 확정하지
  않습니다. 알려진 운지 문자열도 검출 결과가 아니라 연주 가능한 후보입니다.
- 참고용 YouTube URL 칸과 브라우저 버튼을 제거합니다. 로컬 파일과 일반 녹음
  입력만 유지하며 URL 추출기나 접근 제한 우회는 추가하지 않습니다.
- 이전 엔진 호출·저장 리포트의 선택적 `reference_url` 메타데이터 호환성은
  유지하지만 네트워크 입력으로 바꾸지 않습니다. 저작권 허가와 플랫폼 조건은
  별개이며 녹음을 YouTube 다운로드 우회로 안내하지 않습니다.
- 실제 곡의 정확도를 정량 주장하려면 독립적으로 확인한 시간 정렬 정답과
  평가 기준이 필요합니다. 검출 구간이 늘어난 사실만으로 정답률을 주장하지 않습니다.

## 악기 제거 처리 흐름과 저장 계약

바깥쪽 `톤 분석`/`악기 제거`/`코드·스케일 사전` 작업 탭으로 기능을 구분합니다. 악기 제거는 로컬
오디오·영상에서 `vocals`, `drums`, `bass`, `guitar`, `piano`, `other` 가운데
제거할 1~5개를 선택하고 나머지를 새 WAV 하나로 합치는 독립 작업입니다.

```text
로컬 파일 + 시작/끝 + 제거할 1~5개 + 새 .wav 경로
    → FFmpeg: 3초 이상·최대 20분, 44.1 kHz stereo PCM16 임시 입력
    → separate_stem_chunks: 기존 htdemucs_6s 로더·캐시·연산 장치·진행 콜백
    → 남길 stem의 float32 배열을 조각별 float64 합산 → 임시 float32 mix
    → 전체 peak 검사 → 필요할 때만 전 구간 동일 gain으로 클리핑 방지
    → 출력 폴더의 완성 .partial.wav(PCM16) → Windows 비덮어쓰기 rename으로 확정
```

- `stem_removal.remove_stems_from_file(...)`가 경로·선택·유한한 시간 값과 최소
  길이를 검사합니다. 끝 `0`/빈칸은 나머지 구간을 뜻하며 20분에서 제한합니다.
- UI에서 새 입력을 고르면 이전 결과·진행률·시간 표시를 초기화합니다.
  끊어진 심볼릭 링크도 경로 충돌로 처리하므로 기본 이름 선택과 실행 전 검증이
  실제 저장 계층의 비덮어쓰기 계약과 일치합니다.
- 원본과 같은 경로 또는 이미 있는 출력은 거부합니다. Windows의 최종 `os.rename`은
  처리 중 목적지 파일이 생겨도 덮어쓰지 않습니다. 다른 OS에서는 `os.link`를
  사용하며, `os.replace`처럼 기존 파일을 덮어쓰는 동작으로 폴백하지 않습니다.
- 합산 peak가 1을 넘으면 `0.999 / peak` 감쇠를 전체 구간에 적용하고, 그렇지
  않으면 gain 1을 유지합니다. 출력은 44.1 kHz·2채널 PCM16LE WAV입니다.
- 개별 stem 파일은 만들지 않습니다. 디코딩·합산 임시 파일과 부분 출력은 정상
  완료·오류·취소 때 정리합니다. 중단한 작업의 재개/체크포인트는 제공하지 않습니다.
- 모델 첫 다운로드는 네트워크를 사용하고 완료된 사용자 캐시는 톤 분석과 공유합니다.
  사용자 음원·출력은 로컬에 머물며 모델 가중치는 Git·개발 ZIP에 넣지 않습니다.
- 진행률은 처리 단계와 실제 모델/분리 콜백에서 갱신하고 경과 시간은 UI가 갱신합니다.
  취소는 FFmpeg 폴링, 다운로드 콜백, Demucs 내부 블록 경계와 WAV 쓰기에서
  확인하므로 실행 중인 추론 블록이나 네트워크 대기 때문에 반영이 지연될 수 있습니다.
- 작업 중에는 톤 분석·녹음·실시간 모니터·하드웨어 검사·언어 재구성을 함께
  실행하지 않습니다. UI worker는 결과를 큐로 전달하고 Tk 접근은 메인 스레드가 맡습니다.
- 결과는 `tonematch-tmp-stem-removal/v1` 사전으로 제거/유지 파트, 실제 장치,
  구간·형식·추론 시간·정규화 여부를 보존합니다. 톤 레시피 JSON 스키마와 별개입니다.
- 피아노 추정은 모든 건반/신스 분류와 같지 않으며 `other`에도 건반이 남을 수
  있습니다. 누출·소리 손실·위상/어택/잔향 변화·인공음이 가능하고 Logic Pro와
  동일한 모델이나 품질을 보장하지 않습니다.

## GUI 없는 실제 모델 진단

`app.py --stem-self-test-source PATH --stem-self-test-output JSON`은 창을
열지 않는 별도 진단 경로입니다. 기타+피아노 제거를 실제 모델로 실행해 진행률,
WAV 형식·길이·원본 보존과 정리를 확인합니다. `--stem-self-test-seconds`의
기본값 `0`은 전체 음원(최대 20분)이며 3초 이상 구간을 지정할 수도 있습니다.
`--stem-self-test-cancel-at PERCENT`는 보고된 진행률에서 취소를 요청합니다.
활성 추론 블록·네트워크 작업이 끝날 때까지 지연될 수 있습니다.

`stem_diagnostics.py`의 `tonematch-stem-self-test/v1` 진단은 완전한 로컬 모델
캐시와 기존 `remove_stems_from_file` 경로를 CPU로 재사용합니다. 캐시가 없거나
불완전하면 다운로드 없이 실패하며 기존 JSON은 덮어쓰지 않습니다.
중간 음원과 최종 진단 WAV는 임시 폴더에서 처리 후 지우고, JSON에는 소스·출력
파일명·소스 해시나 모델 캐시 경로를 넣지 않습니다. 일반 `--self-test-output`은 여전히
별도의 가벼운 진단이며, 실제 모델 진단과 서로 대체하지 않습니다.
기타 분리 경로도 WAV 헤더가 선언한 frame 수보다 PCM payload가 짧으면
실패로 처리하고 임시 분리 파일을 정리합니다.

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
[06 코드·보이싱 분석 · 근거 부족 시 별도 원본 화성 참고]
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
  현행 오디오·EXE 검증 결과는 `QA_REPORT_v0.0.12.json`과 `BUILD_HISTORY.md`를
  기준으로 하며 이 구현 설명 자체는 해당 검증의 성공 증거가 아닙니다.

## 실시간 스펙트럼 처리 시퀀스

실시간 탭은 위 레시피 처리 시퀀스에 신호를 공급하지 않는 독립 경로입니다.

```text
[선택한 WASAPI 오디오 입력 또는 PC 재생음 loopback]
       ↓ 44.1 kHz · 2채널 · 2,048-frame 블록(초당 약 21.5개)
[Python/SoundCard 캡처 → native_dsp.py: C ABI 2 호환 확인 · float32 직접 입력]
       ↓ C++ 우선, 누락·비호환이면 NumPy 폴백 및 실제 백엔드 표시
[고정 PCM 누적 → 완성된 FFT 단위 → 채널별 Hann FFT power 평균]
       ↓
[20 Hz~20 kHz bin · RMS/Peak dBFS · 스펙트럼 중심 주파수]
       ↓
[최근 4프레임 선형 power 평활화 · 최신 파형 유지]
       ↓
[용량 1 bounded 큐: 오래된 화면 프레임 교체]
       ↓ UI가 50 ms마다 poll(약 20 Hz)
[Tk Canvas: 파형 + 로그 스펙트럼 + 수치 / DSP push ms·완성 창·잔여 frame]
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
| `app.py` | Tkinter 톤 분석/악기 제거 작업 탭, 한·영 전환, 연산 장치·성능 진단, 분석·제거·녹음·스펙트럼 작업 스레드, 수치 진행률·경과 시간, 콘솔 없는 출력 보호, Canvas 표시, 취소, 결과/보이싱 탭, 로그, 디버그 번들, 자체 진단 |
| `engine.py` | FFmpeg 구간 변환, PCM 로딩, NumPy DSP, 기타 분리 호출, 코드 전용 원본 화성 참고 선택, 출력 경로별 Amp/Cab 조립, 템플릿 매칭과 결과 스키마 |
| `separator.py` | Demucs `htdemucs_6s` 캐시 우선 명시 로더, 실제 다운로드·내부 블록 진행, 원인별 모델 오류, 자동/CPU/CUDA 선택·폴백, VRAM/추론 벤치마크, 30초 외부 조각, guitar stem WAV와 선택 stem 배열 소비 콜백 |
| `stem_diagnostics.py` | CPU·로컬 캐시 전용 실제 모델 제거·취소 진단, 경로·음원 해시를 제외한 JSON, 임시 WAV 검사·정리 |
| `stem_removal.py` | 제거/유지 파트·경로·시간 검증, 취소 가능한 FFmpeg 디코딩, 남길 stem 합산·전역 peak 정규화, 원자적 비덮어쓰기 PCM16 WAV 저장과 임시 파일 정리 |
| `recorder.py` | SoundCard 기반 Windows WASAPI loopback/오디오 입력 열거, PCM16 녹음, 실시간 2,048-frame float32 블록 전달 |
| `spectrum.py` | 입력 정규화, 채널별 FFT power, 20 Hz~20 kHz 스펙트럼·dBFS·중심 주파수 계산과 4프레임 평활화 |
| `native_dsp.py` | 신뢰된 번들 DLL·ABI 확인, float32/float64 입력 선택, ctypes 타입·수명/잠금 관리, C++/NumPy 선택과 엔진 처리 진단 |
| `native/tonematch_dsp.cpp`, `.h` | C++17 C ABI 2 엔진, float32/float64 입력, 사전 할당 PCM·Hann/FFT·평활화 이력, 입력/완성 창/잔여 frame 카운터 |
| `tools/build_native.py` | 명시적인 Zig 0.15.2 경로로 Windows x64 DSP DLL 빌드 |
| `reference_compare.py` | 분석 PCM의 레벨 정규화 Reference 프로필, 6밴드 집계, 실시간 Current 보간과 `Δ(Current−Reference)` 계산 |
| `harmony_reference.py` | 41종 코드와 12종 스케일의 도수·이명동음 철자, 12근음 다이어토닉 3·7화음, 분석과 독립적인 건반 사전 자료 |
| `voicing.py` | 채널별 스펙트럼, 독립 피치·잡음/배음 억제, 반복 근거·미확정 이벤트·진단, 화음 후보·대안·관측 구성음과 기타 소스의 보이싱 후보 |
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
- 모델 가중치는 ZIP·Git에 넣지 않습니다. 첫 풀믹스 분석 또는 악기 제거 때 Hugging Face
  사용자 캐시로 내려받습니다.
- 혼합 WAV와 stem은 임시 폴더에서 삭제되며 중간 체크포인트는 없습니다.
- YouTube URL 입력·다운로드는 없습니다. 권한 있는 로컬 파일 또는 녹음·분석이
  허용된 로컬 재생/입력 신호를 사용하며 플랫폼 접근 제한을 우회하지 않습니다.
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
- v0.0.05의 기준 DSP는 Python/NumPy이며 v0.0.08은 이 PCM/FFT/평활화 부분을
  C++ 우선 경로로 교체합니다. 장치 캡처는 SoundCard/WASAPI 공유 모드를 유지하므로
  C++ 장치 콜백, ASIO, WASAPI Exclusive 또는 하드 실시간 엔진으로 표현하지 않습니다.

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
- 자동 EQ/TMP 파라미터 추천·적용, 프리셋 쓰기, ASIO/WASAPI Exclusive는
  구현하지 않습니다. v0.0.08에서도 비교 계산과 Reference 생성은 Python을 유지하고
  Current의 실시간 DSP만 C++로 분리합니다. 무음·비유한 값과 공통 나이퀴스트
  범위 밖은 안전하게 처리합니다.

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

v0.0.08에서 실시간 PCM 누적·FFT·평활화를 C++17로 옮겼습니다. v0.0.09는
float32 입력과 엔진 진단을 추가한 C ABI 2를 사용합니다. Python 버전별 확장 ABI에
의존하지 않는 `ctypes` 경계이며 `native_dsp.py`는
모듈 옆 번들 `resources/tonematch_dsp.dll`만 절대 경로로 로드하고 ABI를 확인합니다.
`create_spectrum_engine(..., backend="auto")`는 C++ 우선이며 누락·비호환·지원하지
않는 구성에는 NumPy로 폴백하고 이유를 제공합니다. 명시적 `backend="cpp"` 요청은
실패를 숨기지 않습니다. 예전 ABI 1 DLL은 호환되지 않아 strict C++ 선택은 오류,
자동 선택은 NumPy 폴백이 됩니다. 실제 백엔드 표시는 UI 스레드 이벤트로 전달합니다.

정렬된 native-endian C-contiguous float32 배열은 `tm_dsp_push_f32`로 직접
전달해 종전 Python float64 upcast 복사를 생략합니다. float64 `tm_dsp_push`는
유지하며 다른 dtype·배치에는 정규화가 필요할 수 있습니다. 엔진이 수락한
`input_frames`, 완성 FFT 단위의 `completed_windows`, 다음 창을 기다리는
`pending_frames`를 조회합니다. reset은 이 카운터와 미완성 입력을 함께 지웁니다.
UI의 DSP push ms는 처리 호출만 재며 캡처·AI·화면 그리기·왕복 오디오 지연이 아닙니다.

네이티브 기본값은 FFT 2,048, 이력 4이며 생성 범위는 FFT 128~32,768의 2의 거듭제곱,
샘플레이트 8~192 kHz, 채널 1~32, 이력 1~64입니다. 유한한 주파수 범위는
나이퀴스트와 유효 bin을 고려합니다. PCM·Hann·FFT 작업 버퍼·이력은 생성 시 할당하고
`push` 중 완성된 비중첩 FFT 단위만 처리합니다. 미완성 샘플은 다음 입력까지 유지하며
중지·초기화 때 버립니다. Python 폴백도 같은 스트리밍 단위를 사용합니다.

채널별 DC 제거·Hann FFT·채널 파워 평균과 최근 4프레임 평활화, RMS 파워 평균,
Peak 창 최댓값, 최신 파형 계약을 기존 기준 구현과 수치 비교합니다. 엔진은 단일
소유자가 사용하고 브리지는 push/reset/close를 잠금으로 보호합니다. Python 출력
복사와 필요한 입력 정규화·잠금, SoundCard WASAPI 공유 모드 캡처가 남아 있어
전체 zero-copy, lock-free 또는 하드 실시간
엔진이 아닙니다. C++ 장치 I/O·ASIO·WASAPI Exclusive는 후속 범위입니다. UI·AI·
오프라인 톤/Reference/코드·레시피는 이번 전환 대상이 아니며, NumPy도 네이티브 FFT를
쓰므로 속도 향상과 전체 곡 Demucs 가속을 가정하지 않습니다. 수치·성능 증거는 QA에
실행한 조건과 함께 기록하고 미실행 항목을 구분합니다.

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
& ..\.venv\Scripts\python.exe tools\build_native.py --zig C:\Tools\zig-0.15.2\zig.exe
& ..\.venv\Scripts\python.exe -m compileall -q .
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
& ..\.venv\Scripts\python.exe app.py --self-test-output .\self-test-v0.0.12.json
& ..\.venv\Scripts\python.exe app.py
```

실행 로그는 우선 EXE 옆 `data\logs`에 기록되고 쓰기 권한이 없으면
`%LOCALAPPDATA%\ToneMatchTMP\logs`를 사용합니다. 앱의 `디버그 번들 ZIP`은
현재 세션 로그, 일별 로그, 실제 배포 소스, 변경 기록과 런타임 상태를 묶습니다.

## 빌드

Git 저장소는 대용량 `resources\ffmpeg.exe`를 추적하지 않습니다. 포터블 개발
ZIP에서 해당 파일을 복사한 뒤 실행하세요.

C++ 재빌드에는 [공식 Zig 0.15.2 Windows x64 ZIP](https://ziglang.org/download/0.15.2/zig-x86_64-windows-0.15.2.zip)을
프로젝트 바깥에 압축 해제합니다. SHA-256은
`3a0ed1e8799a2f8ce2a6e6290a9ff22e6906f8227865911fb7ddedc3cc14cb0c`입니다.
`TONEMATCH_ZIG` 또는 `-ZigPath`로 `zig.exe`를 명시하며, 컴파일러는 배포하지 않습니다.
일반 포터블 실행에는 컴파일러가 필요하지 않습니다. Git은 생성 DLL을 제외하지만
개발 ZIP은 네이티브 소스·헤더·브리지·테스트·빌드 스크립트와 DLL을 포함합니다.

```powershell
& ..\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\build.ps1 -ZigPath C:\Tools\zig-0.15.2\zig.exe -OutputDir C:\원하는\출력폴더
```

호환 NVIDIA PC에서 CUDA 소스 빌드를 만들 때만 기본 환경 검증 후 실행합니다.

```powershell
.\enable_cuda.ps1
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\build.ps1 -ZigPath C:\Tools\zig-0.15.2\zig.exe -OutputDir C:\원하는\출력폴더
```

빌드는 PyInstaller onedir 런타임, 소스, 테스트, 문서, 라이선스, 빌드 재료,
로그 자리, 자체 진단, 파일별 manifest와 ZIP SHA-256을 생성합니다. 모델 가중치가
들어오면 manifest 단계가 실패하도록 막았습니다.

## 패치 버전 절차

1. 재현 테스트를 추가하고 코드를 수정합니다.
2. 모든 함수의 한국어 docstring과 사용자용 한·영 문자열을 유지합니다.
3. `catalog.APP_VERSION`, 최신 `CHANGELOG`, `version_info.txt`, spec, 문서와
   파일명을 다음 패치인 `0.0.13`로 정확히 한 단계 올립니다. 현행 `0.0.12`의
   검증을 먼저 마치고 v0.0.11 이하의 역사 기록은 변경하지 않습니다.
4. 함수 색인과 제3자 라이선스 목록을 다시 생성합니다.
5. 단위 테스트, 소스 자체 진단, 실제 모델 제거·취소 진단, 패키지 자체 진단을
   통과시킵니다. C++ DLL이 실제 로드된 수치 비교·분할 입력·초기화/수명·오류 회귀와
   NumPy 폴백을 구분하고, 네이티브 테스트가 skip된 실행을 릴리스 통과로 기록하지 않습니다.
6. 포터블 ZIP과 SHA-256을 만들고 `BUILD_HISTORY.md`에 검증 결과를 기록합니다.
7. 개인 오디오·URL·로그·모델 캐시·EXE·ZIP을 제외한 소스와 문서를 GitHub에
   커밋합니다.
