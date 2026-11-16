# Microsoft Store 제출 준비

2026-11-16 검증 기록: 전체 v0.1.09 onedir로 만든 validation-only MSIX의 MakeAppx
구조 검증과 내부 4,904개 파일 해시 대조를 통과했습니다. 크기 321,532,858바이트,
SHA-256 `b286c1b72c0e86e9628883f7b4b05b85f3217ee903073076cb8cc156c3e662a5`입니다.
검증 소스는 `a4ec3590c5492b6ddadccad2e310206853e4ee14`이고 실제 설치·서명·인증은
하지 않았습니다. 아래의 초기 fixture 검사와 전체 런타임 검사를 구분하세요.

현재 준비 범위는 unsigned MSIX 생성 도구·manifest·필수 아이콘·런타임 분기입니다.
실제 Partner Center 앱 ID, Store 서명, 설치 시험 및 Store 인증은 완료되지 않았습니다.
GitHub 포터블 배포와는 별도 채널이며, Store의 서명이 GitHub ZIP에 적용되지는 않습니다.

## 계정 소유자가 준비할 값

앱 이름을 예약한 뒤 Partner Center의 **제품 관리 → 제품 ID(Product identity)**에서
다음 값을 그대로 복사합니다. 값의 의미는 [Microsoft 앱 ID 안내](https://learn.microsoft.com/en-us/windows/apps/publish/view-app-identity-details)를 따릅니다.

| JSON 항목 | 출처 |
|---|---|
| `name` | Package/Identity/Name |
| `publisher` | Package/Identity/Publisher (`CN=<GUID>`) |
| `publisher_display_name` | Package/Properties/PublisherDisplayName |
| `display_name` | Store에서 예약한 앱 표시 이름 |
| `description` | 256자 이하의 사실에 맞는 앱 설명 |
| `partner_center_confirmed` | 위 값을 직접 대조한 뒤 `true` |

`store-identity.example.json`은 의도적으로 패키징이 거부되는 빈 템플릿입니다.
실제 값은 Git에서 제외되는 `work/store-identity.json` 등에 저장하세요.
도구는 형식과 입력 확인을 검사할 수 있지만, ID가 실제 계정에 배정됐는지 온라인으로
인증하지 않습니다. 무작위 GUID나 예시 ID를 실사용 값으로 사용하지 마세요.
신분증·셀피·개인키·토큰은 저장소나 채팅에 제출하지 않고 서비스 화면에서 처리합니다.

## 패키지 생성

먼저 [배포 규칙](../DISTRIBUTION_KO.md)에 따라 현재 소스에서 빌드합니다.
입력은 `dist/ToneMatchTMP-v0.1.09` 같은 PyInstaller **onedir** 폴더입니다.
포터블 전체 배포 폴더나 사용자 데이터 폴더를 입력하지 마세요.
앱 EXE 옆의 `_internal` 구조를 `app/` 아래에 그대로 유지하므로 FFmpeg·네이티브 DLL·
Python 런타임의 상대 위치가 변하지 않습니다. 모델 가중치와 개인 음원은 포함하지 않습니다.

```powershell
& '..\.venv\Scripts\python.exe' tools/package_msix.py `
  --app-dir dist/ToneMatchTMP-v0.1.09 --version 0.1.09 `
  --identity work/store-identity.json --output-dir release/store-v0.1.09-attempt1 `
  --makeappx '<검증한 Windows SDK의 x64 makeappx.exe>' `
  --source-commit '<해당 소스의 40자리 Git 커밋>'
```

출력 디렉터리는 반드시 새 경로여야 합니다. 기존 출력은 덮어쓰거나 삭제하지 않습니다.
실패한 시도도 조사할 수 있도록 남기므로 재시도 때 새 경로를 사용하세요.
`--prepare-only`를 추가하면 도구가 없어도 manifest·필수 PNG 아이콘·앱 폴더와
`packaging-receipt.json`을 준비하며, 이 상태는 MSIX 검증 완료가 아닙니다.
영수증은 실제 EXE 버전, x64 구조, 패키지 파일 해시, 수행한 검사만 기록합니다.
`source_commit`은 호출자가 제공한 소스 라벨이며 바이너리 출처 증명은 함께 보관한
빌드 기록으로 확인해야 합니다. unsigned 제출 후보도 `publishable=false`입니다.
`submission_eligible=true`는 실 ID 설정으로 MakeAppx를 통과했다는 뜻이며,
Store 심사나 아래 실제 실행 검사를 대신하지 않습니다.

Store ID 없이 구조만 검사할 때는 `--identity` 대신 **`--validation-only`**를 사용합니다.
이때 manifest ID·표시 이름·출력 파일에 검증용 표시가 들어가고
`submission_eligible=false`가 유지됩니다. `NONPUBLISHABLE` 패키지는 제출·게시하지 마세요.
두 모드를 동시에 지정할 수 없으며, 검증용 패키지를 이름만 바꿔 제출하지 않습니다.

## 버전·manifest 정책

앱 버전과 Store 버전은 의도적으로 다릅니다. `major.minor.patch` 앱 버전을
**`(major+1).minor.patch.0`**으로 변환합니다. 앱 `0.1.09` → Store `1.1.9.0`,
앱 `1.0.00` → Store `2.0.0.0`입니다. 앞의 0과 Store 예약 마지막 자리를 피하고
향후 major 증가 때도 순서가 유지됩니다. EXE의 고정 파일·제품 버전은 앱 버전인
`0.1.9.0`과 일치해야 하며, Store 버전으로 바꾸지 않습니다.
허용 범위를 넘기거나 4자리 앱 버전·접미사·음수 등을 입력하면 중단합니다.
[Microsoft 패키지 버전 규칙](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/package-version-numbering?pivots=store-installer-msix)

Windows x64, 최소 Windows 10 2004(19041)를 대상으로 합니다. manifest는
`packagedClassicApp` / `mediumIL`과 `runFullTrust`만 선언합니다.
추가 장치·파일 접근 capability는 선언하지 않았으며, 실제 녹음 권한과 오디오 동작은
패키지 설치 후 별도로 확인해야 합니다. 아이콘 44×44, 150×150, Store 50×50은
프로젝트가 생성한 단순한 파형 그림입니다. Store 목록용 스크린샷·마케팅 이미지와
실제 표시 품질 검토는 별도 제출 준비 항목입니다.
[Microsoft 수동 manifest 안내](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-manual-conversion)

## 무료 패키징 도구

Windows SDK의 `MakeAppx.exe`를 PATH 또는 기본 Windows Kits 경로에서 찾습니다.
없으면 공식 [Microsoft.Windows.SDK.BuildTools NuGet](https://www.nuget.org/packages/Microsoft.Windows.SDK.BuildTools)에서
확인한 고정 버전을 작업 폴더에 풀고 `--makeappx`로 지정할 수 있습니다.
시스템 설치나 유료 서비스는 필요하지 않습니다. 출처·버전·해시와 Microsoft Authenticode
유효성을 확인하고, 임의 웹사이트의 실행 파일은 사용하지 마세요.
도구는 `pack /h SHA256 /no`로 실행하며 `/nv`로 semantic 검사를 끄지 않습니다.
[MakeAppx 명령·검증 안내](https://learn.microsoft.com/en-us/windows/msix/package/create-app-package-with-makeappx-tool)

이번 구조 검사에서는 공식 NuGet `10.0.28000.2957`의 x64 도구를 작업 폴더에만 풀었습니다.
다운로드한 nupkg SHA-256은
`b7163fc6f636172726d0985963e4f7f11c41afe1c7fdfe78f8051877360ed696`이고,
MakeAppx Authenticode는 Microsoft Corporation, `Valid`로 확인했습니다.
기존 v0.1.08 EXE와 런타임 파일 일부로 만든 **실행 불가능한 구조 시험 fixture**에서
MakeAppx가 `Package creation succeeded`를 반환했습니다. 이 결과는 전체 v0.1.09
런타임이나 설치 가능성 검증이 아니며, 개인 음원·실제 계정 ID를 사용하지 않았습니다.

## 제출 전 남은 확인

- 실제 발급 ID·게시자·예약 이름을 대조하고 새 버전 전체 onedir를 다시 패키징합니다.
- 사용자 승인 후 격리된 Windows 환경에서 설치·실행·삭제 및 Windows App Certification Kit 검사를 수행합니다.
- Store 설치에서 GitHub 자체 교체 updater가 실행되지 않고, 설정·로그·캡처·Numba 캐시가 설치 폴더 밖에 생성되는지 확인합니다.
- 오디오 입출력·FFmpeg 하위 프로세스·네이티브 DSP·모델 다운로드/캐시·오프라인 처리와 업데이트 후 데이터 보존을 확인합니다.
- 개인정보 안내 URL, 지원 연락처, 라이선스 고지, 연령·콘텐츠 설문, 정확한 설명·스크린샷을 준비합니다.
- `runFullTrust`는 기존 데스크톱 Python 앱과 FFmpeg/네이티브 오디오 구성 실행에 필요하다는 사실을 검토 메모로 설명합니다.
- 계정 소유자가 후보를 검토하고 Partner Center에 수동 제출합니다. Store 승인·서명 후 배포 상태를 별도로 확인합니다.

설명 초안: “로컬 음원의 코드 진행과 기타 보이싱을 분석하고 코드 차트를 작성하며,
Tone Master Pro와 Quad Cortex 사용자를 위한 비공식 톤 레시피를 제공합니다.”
Fender·Neural DSP·Microsoft의 공식 제품·보증·제휴라고 표현하지 않습니다.
앱의 네트워크 동작과 로컬 저장 범위는 [개인정보 안내](../PRIVACY.md)를 함께 검토하세요.
