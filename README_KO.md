# ToneMatch TMP 0.0.04

로컬 오디오·영상 또는 Windows PC 재생음을 분석해 Fender Tone Master Pro용 톤 레시피 3개를 추천하는 비공식 Windows 프리뷰입니다. v0.0.04는 AI 분리의 자동/CPU/CUDA 선택과 성능 진단, NumPy 네이티브 최적화, 출력 연결별 Amp/Cab 체인 정정을 추가합니다.

추천 카탈로그는 Tone Master Pro 펌웨어 1.8.58과 Model Guide Rev. J의 공개 모델명·컨트롤명을 기준으로 작성했습니다.

> 이 프로그램은 원곡 장비나 Fender DSP를 식별·복제하지 않습니다. `매칭 %`는 정확도 확률이 아니라 측정 특징에 가까운 시작점을 정렬하기 위한 내부 유사도와 분석 신뢰도의 조합입니다.

## 처음 사용하기 전에

- 배포 ZIP은 반드시 별도 폴더에 모두 압축 해제한 뒤 실행하세요. ZIP 내부에서 EXE를 직접 실행하지 마세요.
- `풀믹스/영상 → AI 기타 분리`를 처음 실행할 때 Demucs `htdemucs_6s` 모델 파일을 Hugging Face에서 내려받으므로 인터넷 연결과 여유 저장 공간이 필요합니다.
- 모델은 배포 ZIP에 포함되지 않습니다. 한 번 정상 다운로드되면 같은 Windows 사용자 캐시를 재사용하므로 이후 분석은 보통 오프라인에서도 가능합니다.
- `이미 기타만 있는 파일 → 분리 생략`은 AI 모델을 사용하지 않으므로 첫 모델 다운로드 없이 실행할 수 있습니다.
- 포터블 EXE는 호환성을 위해 CPU 런타임을 포함합니다. 자동 모드는 CUDA를 사용할 수 없으면 CPU를 선택하며, 특히 5~20분 곡은 실제 재생 시간보다 오래 걸릴 수 있습니다.
- CUDA는 호환 NVIDIA PC의 소스 개발 환경에 별도로 설치하고 재빌드해야 합니다. 이번 릴리스 PC에는 CUDA GPU가 없어 실제 GPU 추론은 하드웨어 검증하지 못했습니다.

## 로컬 파일 빠른 사용법

1. `ToneMatchTMP-v0.0.04.exe`를 실행합니다. 서명되지 않은 프리뷰라 Windows가 경고하면 배포자가 제공한 SHA-256과 파일 해시를 먼저 비교하세요.
2. 입력 방법에서 `로컬 오디오/영상 파일`을 선택하고, 직접 보유하거나 분석 권한이 있는 파일을 고릅니다.
3. 시작·끝 시간을 초 단위로 지정합니다.
   - 최소 분석 길이는 3초입니다.
   - 끝 시간을 `0` 또는 빈칸으로 두면 시작 지점부터 파일 끝까지 분석하되 최대 20분에서 멈춥니다.
   - 끝 시간을 입력해도 한 번에 처리하는 최대 구간은 20분입니다.
4. 소스 구성을 고릅니다.
   - 일반 음원·뮤직비디오·밴드 믹스: `풀믹스/영상 → AI 기타 분리 (권장)`
   - 이미 기타만 녹음된 DI·앰프·타브 영상: `이미 기타만 있는 파일 → 분리 생략`
5. 내 기타의 픽업과 Tone Master Pro 출력 연결 방식을 선택합니다. 이 선택에 따라 Amp/Cab 포함 여부와 실제 적용 순서가 달라집니다.
6. `성능 · DSP 진단`에서 연산 장치를 자동, CPU 또는 CUDA로 고릅니다. CUDA를 고를 수 없는 환경에서는 자동을 사용하세요.
7. 필요하면 YouTube 주소를 참고 URL에 적습니다. 주소는 출처 기록과 브라우저 열기에만 쓰며 영상 스트림을 직접 추출하지 않습니다.
8. `톤 분석 시작`을 누릅니다. AI 모드는 30초 단위 조각 진행률을 표시하며, `분석 취소`는 현재 조각 처리가 끝난 뒤 반영될 수 있습니다.
9. 추천 1~3의 블록 순서, 모델, 파라미터와 이유를 비교한 뒤 JSON 또는 HTML 리포트를 저장합니다.
10. Tone Master Pro 본체나 Pro Control에서 값을 수동 입력하고, 원곡과 같은 체감 음량으로 A/B하며 조정합니다.

## PC 재생음 녹음

로컬 파일이 없을 때 YouTube 등 브라우저에서 정상 재생되는 소리를 Windows WASAPI loopback으로 임시 WAV에 녹음해 분석할 수 있습니다. 이 기능은 사이트에서 파일이나 스트림을 추출하는 다운로더가 아닙니다.

1. 브라우저에서 합법적으로 재생할 수 있는 곡을 열고 원하는 지점 직전에 일시 정지합니다.
2. ToneMatch TMP 입력 방법에서 `PC 재생음 또는 오디오 입력 녹음`을 선택합니다.
3. 장치 목록에서 실제 재생에 쓰는 출력의 `PC 재생음`(loopback) 항목을 고릅니다. 기타·마이크를 직접 녹음하려면 `오디오 입력` 항목을 고릅니다.
4. 최대 녹음 시간을 정하고 `재생음 녹음 시작`을 누른 뒤 브라우저 재생을 시작합니다.
5. 필요한 구간이 끝나면 `녹음 중지`를 누릅니다. 3초 미만 녹음은 분석할 수 없고, 최대 녹음 시간은 20분입니다.
6. 일반 곡이라면 AI 기타 분리를 선택해 분석합니다.

녹음에는 알림음과 다른 앱 소리도 함께 들어갈 수 있습니다. 알림을 끄고 정확한 출력 장치를 선택하세요. 보호된 재생 경로를 우회하지 않으며, 녹음·분석 권한과 서비스 이용 조건을 지킬 책임은 사용자에게 있습니다.

## AI 기타 분리와 DSP 분석

풀믹스/영상 모드의 처리 순서는 다음과 같습니다.

```text
로컬 파일 또는 PC 재생음
  → FFmpeg 44.1 kHz/16-bit PCM 변환
  → Demucs htdemucs_6s, 30초 단위 guitar stem 분리
  → 22.05 kHz 분석 PCM 변환
  → NumPy 네이티브 DSP 특징 추출
  → 코드·베이스/역위·음역·간격 타임라인 추정(실험)
  → Tone Master Pro 템플릿 매칭
  → 추천 3개와 JSON/HTML 결과
```

선택 구간과 분리된 stem은 임시 작업 영역에서 처리됩니다. 앱은 오디오를 분석 서버에 업로드하지 않지만, 첫 AI 실행의 모델 다운로드에는 네트워크가 사용됩니다.

DSP 단계는 포화도, 밝기, 바디, 압축감, 다이내믹, 공간감, 스테레오 폭, 모듈레이션, 딜레이 반복 단서 등을 계산합니다. 출력 연결에 따라 다음처럼 블록을 조정합니다.

- FRFR·헤드폰·USB·PA: `Amp Only`와 별도 `Cabinet`을 포함하고 Cabinet의 로우/하이 컷을 한 번만 적용
- 파워앰프 + 실제 기타 캐비닛: `Amp Only`만 포함하고 Cabinet/IR은 제외하며 기준 Cabinet 정보는 비교 참고값으로 보존
- 기타 앰프 전면 입력: Amp/Cab을 모두 제외하고 이펙트 중심으로 추천

성능 진단은 요청 장치와 실제 선택 장치, CUDA 가용성·빌드, GPU 모델과 총/여유 VRAM, Demucs 전체·조각별 추론 시간, 실시간 배수와 최대 GPU 메모리 사용량을 표시합니다. 실제 분석을 하지 않은 값은 해당 없음으로 남습니다. 연산 선택은 설정에 저장됩니다.

## 첫 AI 모델 다운로드와 캐시

기본 캐시 위치는 다음과 같습니다.

```text
%USERPROFILE%\.cache\huggingface\hub\models--adefossez--HTDemucs-6s
```

`HF_HOME` 환경 변수가 설정돼 있으면 다음 위치를 사용합니다.

```text
%HF_HOME%\hub\models--adefossez--HTDemucs-6s
```

다운로드가 실패하면 인터넷·방화벽·프록시·디스크 여유 공간을 확인한 뒤 다시 분석하세요. 캐시를 지우면 다음 AI 분석에서 다시 다운로드합니다. 모델 가중치는 크기와 별도 배포 조건 때문에 포터블 ZIP에 넣지 않습니다.

## 다른 PC에서 실행하거나 개발을 재개하는 방법

### EXE만 사용할 때

1. 포터블 ZIP 전체를 쓰기 가능한 새 폴더에 압축 해제합니다.
2. SHA-256을 확인하고 `ToneMatchTMP-v0.0.04.exe`를 실행합니다.
3. 새 PC에는 이전 PC의 사용자 캐시가 없으므로 첫 AI 기타 분리 때 모델을 다시 다운로드합니다.
4. 다운로드를 반복하고 싶지 않다면 모델의 배포 조건을 확인한 뒤 이전 PC의 `models--adefossez--HTDemucs-6s` 폴더 전체를 새 PC의 동일한 캐시 경로로 복사하거나, 두 PC에서 같은 구조의 `HF_HOME`을 지정하세요.

### 소스 개발을 이어갈 때

1. 개발 ZIP을 `C:\ToneMatchTMP-dev` 같은 쓰기 가능한 경로에 압축 해제합니다.
2. 압축 안의 `ToneMatchTMP-v0.0.04\source`가 자체 완결된 프로젝트 폴더입니다.
3. 64-bit Python 3.12를 설치하고 패키지 루트에 `.venv`를 새로 만듭니다. 기존 PC의 가상환경은 절대 경로와 네이티브 패키지를 포함하므로 복사해 재사용하지 마세요.
4. `source\requirements.txt`로 의존성을 설치하고 테스트를 실행합니다.
5. `DEVELOPER_HANDOFF_KO_EN.md`와 `BUILD_HISTORY.md`를 먼저 읽은 뒤 작업을 이어갑니다.

```powershell
Set-Location C:\ToneMatchTMP-dev\ToneMatchTMP-v0.0.04
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r .\source\requirements.txt

Set-Location .\source
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
& ..\.venv\Scripts\python.exe app.py
```

CUDA 지원 NVIDIA PC에서 소스 빌드를 가속하려면 위 기본 환경과 테스트를 먼저 확인한 뒤 `source`에서 다음을 실행합니다.

```powershell
.\enable_cuda.ps1
& ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\build.ps1
```

`enable_cuda.ps1`은 `requirements-cuda126.txt`에 고정된 PyTorch CUDA 런타임을 설치합니다. NVIDIA 드라이버·GPU·PyTorch CUDA 빌드가 모두 호환되어야 하며, 설치만으로 모든 PC에서 CUDA가 보장되지는 않습니다. 가상환경을 다른 PC로 복사하지 말고 PC마다 다시 만드세요.

공개 소스는 `git clone https://github.com/JH-Prime/ToneMatchTMP.git`으로 받을 수도 있습니다. Git 저장소는 용량이 큰 `resources\ffmpeg.exe`를 제외하므로, 소스 실행·빌드 전 포터블 ZIP의 `source\resources\ffmpeg.exe`를 같은 위치에 복사하세요. `build.ps1`은 프로젝트의 형제 폴더에 있는 `..\.venv`를 사용합니다. 자세한 인수인계·빌드·검증 절차는 `DEVELOPER_HANDOFF_KO_EN.md`를 참고하세요. Codex나 다른 개발 도구에서 재개할 때는 `source` 또는 Git clone 폴더를 작업 폴더로 열고 두 인수인계 문서를 먼저 읽도록 지시하세요. 대화 기록이나 이전 PC의 임시 파일은 ZIP에 자동 포함되지 않습니다.

## 개발자 옵션

오른쪽 위 `개발자 옵션`을 켜면 처리 시퀀스, 실시간 로그, 클릭형 배포 소스와 변경 기록을 확인할 수 있습니다. v0.0.04에서는 성능·DSP 진단에 연산 장치, CUDA/GPU/VRAM 상태와 마지막 분리 벤치마크가 함께 표시됩니다. NumPy 최적화는 기존 파이썬 UI·AI 구조를 유지하면서 컴파일된 네이티브 연산을 활용합니다.

## 중요한 한계

- Demucs 6-stem의 guitar 출력은 실험적인 추정입니다. 키보드·보컬·심벌이 남거나 기타가 일부 사라지고, 위상감·어택·잔향에 인공음이 생길 수 있습니다.
- AI가 분리한 stem이 거의 무음이면 분석을 중단합니다. 실제 기타가 잘 들리는 구간을 선택하세요.
- 긴 곡의 외부 처리는 30초 단위지만 CPU/GPU 추론 시간은 PC 성능, CUDA 호환성과 VRAM에 크게 좌우됩니다.
- PC 재생음 녹음 품질은 Windows 출력 장치, 드라이버, 시스템 음량과 다른 앱 소리에 영향을 받습니다.
- 코드·보이싱 분석은 NumPy 스펙트럼의 피치 클래스 단서를 이용하는 실험 기능입니다. 복잡한 왜곡, 드롭 튜닝, 카포, 벤딩, 베이스·건반 누출에서는 코드명·최저음·음역이 틀릴 수 있으며 악보 채보 결과로 간주하면 안 됩니다.
- 취소되거나 중단된 AI 분석을 중간 조각부터 재개하는 체크포인트는 없습니다. 완전히 내려받은 모델 캐시만 재사용되며 분석은 처음부터 다시 실행합니다.
- 추천값은 완성 프리셋이 아니라 시작점입니다. Gain → Cab/Mic → EQ → Delay/Reverb 순으로 조정하세요.
- C++ 실시간 오디오·링 버퍼·FFT·ASIO 엔진은 후속 로드맵입니다. v0.0.04는 실시간 입력 톤 매칭이나 C++ 오디오 엔진을 제공하지 않습니다.
- Tone Master Pro/Pro Control은 임의 블록과 모든 값을 쓰는 공개 API를 제공하지 않습니다. 기기 연결, 프리셋 자동 생성·전송, 노브 자동 조작을 하지 않습니다.
- JSON은 분석 데이터이며 Tone Master Pro가 가져오는 `.preset` 파일이 아닙니다.
- Tone Master Pro 외 장치 프로필은 현재 선택 자리만 있으며 분석은 지원하지 않습니다.

## YouTube·저작권·상표

YouTube URL은 참고 링크 전용입니다. ToneMatch TMP는 YouTube 다운로드, 스트림 추출 또는 접근 제한 우회를 제공하지 않습니다. PC 재생음 녹음도 정상 재생되는 운영체제 출력을 사용합니다. 직접 소유했거나 녹음·분석 권한이 있는 오디오만 사용하고 저작권 음원, 녹음 WAV, AI stem을 허가 없이 재배포하지 마세요.

Fender, Tone Master, Tone Master Pro와 Pro Control은 각 권리자의 상표입니다. ToneMatch TMP는 Fender Musical Instruments Corporation과 제휴·승인·후원 관계가 없는 비공식 도구입니다. Fender의 모델링 DSP·펌웨어·원 프리셋을 포함하거나 추출하지 않습니다.

배포물에 포함되는 제3자 구성요소와 소스 링크는 `THIRD_PARTY_NOTICES.txt`, `LICENSE.txt`와 `licenses` 폴더에서 확인하세요. AI 모델 가중치는 배포물에 포함되지 않습니다.

## 버전 및 개발 기록

정식 출시 전 패치는 `0.0.01`, `0.0.02`, `0.0.03`, `0.0.04` 순으로 올립니다. 앱 버전, Windows 파일 정보, EXE·ZIP 이름, README, 변경 기록과 SHA-256은 같은 버전이어야 합니다.

- `0.0.04`: 자동/CPU/CUDA 연산 선택과 GPU·VRAM·추론 벤치마크 진단, NumPy 네이티브 최적화, 출력 경로별 Amp/Cab 체인 정정, 별도 CUDA 소스 설치 경로
- `0.0.03`: 포터블 개발 ZIP과 한·영 인수인계, 빌드/검증 이력, 로그 전달 기준, NumPy 코드·보이싱 분석(실험)
- `0.0.02`: 한국어/English 전환, 확장형 장치 선택, 최대 20분, Demucs guitar stem, PC 재생음/입력 녹음과 취소
- `0.0.01`: 로컬 짧은 구간 DSP 특징 분석과 Tone Master Pro 추천 3개, JSON/HTML, 개발자 코드 뷰

- 개발 인수인계: `DEVELOPER_HANDOFF_KO_EN.md`
- 빌드 이력과 검증 기록: `BUILD_HISTORY.md`
- 개발자 구조 설명: `DEVELOPMENT_KO.md`
- 전체 함수·한국어 docstring 색인: `FUNCTION_REFERENCE_KO.md`

## 향후 정확도와 자동화 개선에 유용한 자료

공유 권한이 있는 다음 자료가 있으면 모델·컨트롤 범위와 특징→설정값 보정을 개선할 수 있습니다.

- 펌웨어 1.8.58에서 Pro Control로 내보낸 빈 프리셋과 단일 블록 프리셋
- Gain 또는 Cabinet 마이크 위치 하나만 다르게 저장한 프리셋 쌍
- 같은 연주의 드라이 DI와 해당 프리셋 처리 후 WAV
- 기타 종류·픽업·출력 방식·펌웨어가 기록된 비교 샘플

비공개 `.preset` 형식은 구조와 체크섬을 확인하기 전 임의로 생성하지 않습니다. 상용 프리셋이나 타인 저작물은 허가 없이 제공하지 말고, 공유 전 개인정보를 지우고 원본을 백업하세요.

## 참고 자료

- Fender Tone Master Pro 한국어 사용설명서 `OM_2274900000_Tone-Master-PRO_KR`
- Fender 공식 [Tone Master Pro Model Guide Rev. J](https://www.fmicassets.com/Damroot/Original/10151/OM_2274900000_Tone-Master-Pro-Model-Guide-J_EN.pdf)
- Fender 공식 [펌웨어 및 Pro Control 업데이트 기록](https://support.fender.com/hc/en-us/articles/46768129660315-Fender-Tone-Master-Pro-Firmware-and-Pro-Control-App-Updates)
- Fender 공식 [Tone Master Pro 제품 페이지](https://www.fender.com/products/tone-master-pro)
- 기능 방향 참고: [Mule ToneForge 소개 글](https://www.mule.co.kr/bbs/info/muleboard?idx=67998871&v=v)

앱에 들어가는 모델명·컨트롤명·제어 한계는 공식 매뉴얼과 Model Guide를 우선합니다.
