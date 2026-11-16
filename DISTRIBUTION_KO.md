# 무료 서명·Store 배포 운영 규칙

이 규칙은 v0.1.09 준비 작업부터 **이후 모든 빌드와 릴리스**에 적용합니다.
현재 상태는 기술 준비 단계입니다. SignPath Foundation 승인·실제 서명·Microsoft Store
인증 완료를 의미하지 않습니다. 게시된 v0.1.08과 이전 태그·배포 파일은 보존합니다.
기술 검증은 완료했으며 두 서비스 계정은 아직 준비되지 않았습니다.
실제 신청에 복사할 자료는 저장소의 [가입 안내](https://github.com/JH-Prime/ToneMatchTMP/blob/main/distribution/ENROLLMENT_KO.md)에 있습니다.

## 빌드 결과의 구분

기본 `build.ps1`은 `SigningInput` 모드로 서명 전 포터블 폴더만 만듭니다.
공개 ZIP이나 체크섬 파일을 만들지 않습니다. 이 폴더는 신뢰된 배포본이 아닙니다.
기존 로컬 환경은 부모 폴더의 `.venv`를 사용하고, CI에서는 `-PythonExe`로 명시합니다.
테스트는 `tools/verify_headless.py`로 창 생성을 차단하며, 실제 UI 검증은 별도입니다.

```powershell
.\build.ps1 -ZigPath <검증한-Zig-0.15.2-zig.exe>
```

서명 없는 개발자 ZIP이 명시적으로 필요할 때만 다음 모드를 사용합니다. 기존 ZIP과
체크섬 경로가 있으면 중단합니다. 새 버전 또는 별도의 신규 출력 경로를 사용하세요.

```powershell
.\build.ps1 -DistributionMode Development -OutputDir <새-개발자-출력폴더> -ZigPath <zig.exe>
```

각 빌드는 `diagnostics/DISTRIBUTION.json`에 서명 전 상태와 실제 검사 범위를 남깁니다.
`SigningInput` 또는 `Development` 성공을 코드 서명 성공으로 보고하지 마세요.
공개 서명본은 SignPath 결과 검증 뒤 최종 manifest·ZIP·SHA-256을 새로 만들어야 합니다.
이미 게시한 파일에 나중에 서명해 덮어쓰는 방법은 사용하지 않습니다.

## SignPath 무료 경로

GitHub의 수동 `Windows distribution` workflow로 표준 Windows hosted runner에서 빌드합니다.
공개 저장소의 무료 표준 runner만 사용하며 larger runner나 유료 서비스는 설정하지 않습니다.
고정된 Python 의존성과 Zig를 사용하고, FFmpeg는 문서화한 해시를 검증한 파일만 사용합니다.
예전 앱 EXE를 다시 서명하는 대신 현재 소스에서 앱을 새로 빌드합니다.

Foundation의 무료 프로그램은 공개 MIT 소스만으로 자동 승인되지 않습니다. 검증 가능한
빌드 출처와 프로젝트 평판·관리 주체·라이선스 등을 심사합니다. 계정 소유자가
[신청 페이지](https://signpath.org/apply)에서 프로젝트를 신청하고 GitHub 저장소 연결,
2단계 인증, 승인자 설정을 완료해야 합니다. 저장소 소유자는 `JH-Prime`입니다.

신청 자료: 저장소 https://github.com/JH-Prime/ToneMatchTMP,
기존 배포 https://github.com/JH-Prime/ToneMatchTMP/releases,
MIT 소스, Windows x64 Python/PyInstaller 로컬 음원 분석 프로그램,
[코드 서명 정책](CODE_SIGNING_POLICY.md), [개인정보 안내](PRIVACY.md).
정확한 SignPath 조직·프로젝트·서명 정책 ID와 승인된 인증서 식별정보는 승인 후 설정합니다.
API 토큰은 GitHub Actions secret에 직접 입력하고 채팅·소스·로그에 붙이지 마세요.
`distribution/signpath-settings.example.json`에 필요한 값의 이름이 있습니다.
`SIGNPATH_FOUNDATION_APPROVED`와 `FREE_CI_STORAGE_CONFIRMED`는 빌드 job도 읽으므로
동일한 이름의 저장소 변수로 설정하고, 보호된 `signpath-production` environment에도
승인 상태와 서명 식별자를 설정합니다. 해당 environment는 main만 허용하고 사람의 검토를
요구하도록 설정하세요. Foundation의 매 서명 수동 승인 역시 유지합니다.
저장 용량 확인 변수는 계정의 남은 무료 Actions 자산 용량과 유료 초과 사용 차단을 확인한
경우에만 true로 합니다. 기본 검사 실행은 자산을 업로드하지 않고, 승인된 서명 실행만
압축한 자산을 1일 보관합니다. 공개 저장소의 무료 실행 시간과 자산 저장 과금은 별개입니다.

첫 서명 범위는 프로젝트 자체 EXE입니다. 제3자 FFmpeg/Python/DLL에는 프로젝트 인증서를
덧붙이지 않습니다. 자체 DSP DLL도 최초 범위에서는 manifest로 무결성을 확인하며,
별도 서명 범위 확장 때 제품 메타데이터와 정책을 보완해야 합니다.
서비스의 수동 승인 후에도 반환 파일·게시자·인증서·원본 빌드 대응을 검증해야 합니다.
과거 updater와 호환되도록 서명된 개발자 ZIP도 `Portable-Dev.zip` 이름을 유지합니다.
서명 여부는 파일명에서 추측하지 않고 실제 EXE 서명과 배포 진단으로 확인합니다.
신뢰할 수 있는 서명과 SmartScreen 평판은 별개이므로 경고가 즉시 사라진다고 약속하지 않습니다.

## Microsoft Store 무료 경로

[Store 개발자 등록 시작](https://storedeveloper.microsoft.com/)의 새 무료 등록 경로를 사용합니다.
실명·신분증·셀피 등 본인 인증은 계정 소유자가 서비스 화면에서 직접 수행합니다.
이 자료를 채팅이나 저장소에 보관하지 않습니다. 한국 본인 인증의 실제 완료 여부는
계정 등록 단계에서 확인해야 합니다. 외부 서비스의 승인 결과를 대신 만들어내지 않습니다.

Store에서 앱 이름을 예약한 다음 Partner Center의 제품 ID 정보에 있는 Package Identity
Name, Publisher, Publisher Display Name 등 정확한 공개 식별자를 패키징 설정에 입력합니다.
`distribution/store-identity.example.json`은 예시일 뿐 실제 발급 값이 아닙니다.
`--validation-only` 패키지는 구조 검사 전용이며 등록·설치·배포 가능한 제품으로 취급하지 않습니다.

Store 버전은 `(앱 major + 1).minor.patch.0`으로 정합니다. 예를 들어 앱 `0.1.09`는
Store 패키지 `1.1.9.0`입니다. 첫 숫자 0을 피하고 이후 앱 major 증가에도 단조 증가하도록
채널 버전을 구분합니다. EXE의 제품 버전은 `0.1.09`를 유지합니다.
MSIX 내부 앱은 Store 업데이트를 사용하고, 설정·로그·캡처·JIT 캐시는 설치 폴더 밖에 씁니다.
Windows 패키지 감지가 실패하면 자체 업데이트는 생략하고 사용자 데이터 위치로 폴백합니다.

Store의 MSIX 서명은 Store 심사를 통과한 패키지에 적용됩니다. GitHub 포터블 ZIP은 별도로
SignPath 서명 검증을 거쳐야 합니다. 실제 설치·오디오 입출력·CQT/FFmpeg 동작·업데이트 시
데이터 유지 및 Store 인증은 구조 검증만으로 통과했다고 기록하지 않습니다.
필요한 실제 창 실행·설치 검사는 사용자 허가를 받은 뒤 수행합니다.

## 릴리스 완료 기준

소스 버전·내장 EXE 버전·QA가 맞고 headless 및 배포 관련 검사를 통과해야 합니다.
서명 후 무결성 목록을 새로 만들고, 공개 파일을 실제 다시 내려받아 크기와 해시를 확인합니다.
기존 사용자 음원·모델 가중치·비밀정보·로컬 캐시는 포함하지 않습니다.
계정 승인이나 실제 서명이 대기 중이면 상태를 그대로 보고하며, 서명된 릴리스나
Store 게시 완료로 표시하지 않습니다. 초기화 애니메이션은 이 배포 준비 다음의 별도 후속입니다.
