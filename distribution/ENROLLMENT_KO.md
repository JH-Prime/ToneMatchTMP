# 무료 서명·Store 계정 시작 안내

2026-11-15 사용자가 두 서비스 모두 아직 준비되지 않았다고 확인했습니다.
아래는 신청 준비 자료이며 가입·서비스 승인·서명·Store 게시 완료 기록이 아닙니다.

## 1. SignPath Foundation

[Foundation 무료 신청](https://signpath.org/apply)에서 시작하세요.
일반 유료 상품이나 체험판을 결제할 필요는 없습니다. 승인 여부는 Foundation이 결정합니다.
본인 연락처·계정 확인은 서비스 양식에 직접 입력합니다. 토큰·인증서는 채팅에 보내지 마세요.

신청에 사용할 공개 프로젝트 정보:

- Project name: ToneMatchTMP
- Repository: https://github.com/JH-Prime/ToneMatchTMP
- Existing releases: https://github.com/JH-Prime/ToneMatchTMP/releases
- License: MIT for project source; bundled upstream licenses are documented separately.
- Maintainer/repository owner: JH-Prime
- Code signing policy: https://github.com/JH-Prime/ToneMatchTMP/blob/main/CODE_SIGNING_POLICY.md
- Privacy: https://github.com/JH-Prime/ToneMatchTMP/blob/main/PRIVACY.md
- Intended signing scope: only the project's root Windows x64 executable. Upstream PE files and the native DSP library are outside the initial signing scope.

영문 설명 초안:

> ToneMatchTMP is an open-source Windows desktop application for local audio analysis,
> chord estimation, manual chord editing, playback-linked chord charts, instrument
> mixing and PDF export. Its source is MIT licensed. It uses Python/PyInstaller and
> a small project-owned native DSP library. Existing unsigned developer releases are
> available on GitHub. We have prepared a manual GitHub-hosted Windows build workflow
> with pinned inputs, source-to-artifact binding and post-signing Authenticode checks.
> We request free Foundation signing for the application's root executable only.
> The workflow is not yet connected to SignPath and no Foundation approval or signed
> release is claimed. We will configure required MFA, repository origin restrictions,
> human signing approval, and the Foundation's policy attribution after acceptance.

승인 후 준비할 항목은 `signpath-settings.example.json`에 있습니다. GitHub App을 해당
저장소에 연결하고, 저장소/branch 출처 확인과 사람의 서명 승인을 유지해야 합니다.
GitHub `signpath-production` environment와 필요한 variables/secrets를 서비스 화면에서
설정합니다. 무료 자산 용량과 유료 초과 사용 차단을 확인하기 전에는 서명 업로드를 켜지 않습니다.

## 2. Microsoft Store

[공식 무료 개발자 등록 시작](https://storedeveloper.microsoft.com/)에서 새 등록 흐름을 사용하세요.
개인 취미 프로젝트인지 사업자 배포인지에 맞는 계정 유형을 직접 선택합니다.
본인 인증·약관 동의·사업자 확인 등은 계정 소유자가 직접 완료해야 합니다.
개인 등록의 신분증·셀피는 공식 서비스에만 제출하세요. 한국 신분증의 실제 인증 성공은
등록 절차에서 확인해야 하며, 이 문서가 인증 가능 여부를 보증하지 않습니다.

등록 후 원하는 앱 이름을 예약하고 **제품 관리 → 제품 ID**에서 다음 공개 값만 확보합니다.
Package Identity Name, Package Identity Publisher, Publisher Display Name,
예약한 앱 표시 이름. `store-identity.example.json`에 설명된 항목에 대응됩니다.
형식을 맞추려고 임의 GUID를 만들거나 validation-only 값을 대신 제출하지 마세요.

현재 MSIX 도구는 이 실제 식별자와 전체 onedir 빌드를 입력받아 unsigned Store 후보를
만듭니다. Store가 심사 후 재서명하므로 별도 유료 인증서 구매가 필요하지 않습니다.
목록 설명·개인정보 URL·실제 화면 캡처·연령/콘텐츠 질문 등 제출 자료는 계정 생성 후
실제 제품 양식에 맞춰 완성해야 합니다. UI 실행·화면 캡처·패키지 설치 검증은 별도 허가 후
진행합니다. 기존 GitHub 배포의 태그·파일은 계속 보존합니다.

준비 후에는 계정 생성 여부와 위 공개 식별자/승인 상태만 알려 주세요.
비밀번호·API 토큰·개인키·신분증은 전달할 필요가 없습니다.
