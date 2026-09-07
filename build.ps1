param(
    [switch]$SkipTests,
    [switch]$SkipZip,
    [string]$OutputDir = "release"
)

$ErrorActionPreference = "Stop"
$Version = "0.0.06"
$AppBaseName = "ToneMatchTMP-v$Version"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = [System.IO.Path]::GetFullPath((Join-Path $ProjectDir "..\.venv\Scripts\python.exe"))
$PyInstallerExe = [System.IO.Path]::GetFullPath((Join-Path $ProjectDir "..\.venv\Scripts\pyinstaller.exe"))
$ReleaseDir = if ([System.IO.Path]::IsPathRooted($OutputDir)) {
    [System.IO.Path]::GetFullPath($OutputDir)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $ProjectDir $OutputDir))
}
$StageParent = [System.IO.Path]::GetFullPath((Join-Path $ProjectDir "build\portable"))
$StageRoot = [System.IO.Path]::GetFullPath((Join-Path $StageParent $AppBaseName))
$DistRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectDir "dist\$AppBaseName"))
$BuildLog = [System.IO.Path]::GetFullPath((Join-Path $ProjectDir "build\$AppBaseName-build.log"))

function Assert-ChildPath {
    param([string]$Path, [string]$Parent)
    $FullPath = [System.IO.Path]::GetFullPath($Path)
    $FullParent = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    if (-not $FullPath.StartsWith($FullParent, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "안전 범위를 벗어난 경로입니다: $FullPath"
    }
}

function Remove-SafeTree {
    param([string]$Path, [string]$Parent)
    Assert-ChildPath -Path $Path -Parent $Parent
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

function Invoke-LoggedNative {
    param([string]$Label, [scriptblock]$Command)
    "[$(Get-Date -Format s)] $Label" | Tee-Object -FilePath $BuildLog -Append
    & $Command 2>&1 | Tee-Object -FilePath $BuildLog -Append
    if ($LASTEXITCODE -ne 0) {
        throw "$Label 실패 (exit $LASTEXITCODE)"
    }
}

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python 가상환경을 찾지 못했습니다: $PythonExe"
}
if (-not (Test-Path -LiteralPath $PyInstallerExe)) {
    throw "PyInstaller를 찾지 못했습니다: $PyInstallerExe"
}
$QaPath = Join-Path $ProjectDir "QA_REPORT_v$Version.json"
if (-not (Test-Path -LiteralPath $QaPath)) {
    throw "현재 버전 QA 보고서가 필요합니다: $QaPath"
}
$QaReport = Get-Content -Raw -LiteralPath $QaPath | ConvertFrom-Json
if ($QaReport.app_version -ne $Version) {
    throw "QA 보고서 버전이 빌드 버전과 다릅니다."
}

Push-Location $ProjectDir
try {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $BuildLog) | Out-Null
    Set-Content -LiteralPath $BuildLog -Encoding utf8 -Value "ToneMatch TMP $Version build log"

    if (-not $SkipTests) {
        # 이전 build/dist의 수천 개 런타임 파일을 다시 컴파일하지 않고 배포 소스만 검사한다.
        Invoke-LoggedNative "Python compileall" {
            & $PythonExe -m compileall -q app.py catalog.py debug_info.py devices.py engine.py i18n.py recorder.py reference_compare.py report.py separator.py spectrum.py voicing.py tests tools
        }
        Invoke-LoggedNative "Unit tests" { & $PythonExe -m unittest discover -s tests -v }
    }

    Invoke-LoggedNative "Collect license notices" {
        & $PythonExe tools\collect_licenses.py --requirements requirements.txt --destination licenses\runtime --inventory THIRD_PARTY_RUNTIME_INVENTORY.txt
    }
    Invoke-LoggedNative "Generate Korean function reference" { & $PythonExe tools\generate_function_reference.py }
    Invoke-LoggedNative "PyInstaller onedir build" { & $PyInstallerExe --noconfirm --clean ToneMatchTMP.spec }

    $ExePath = Join-Path $DistRoot "$AppBaseName.exe"
    if (-not (Test-Path -LiteralPath $ExePath)) {
        throw "빌드 EXE를 찾지 못했습니다: $ExePath"
    }

    Remove-SafeTree -Path $StageRoot -Parent $StageParent
    New-Item -ItemType Directory -Force -Path $StageRoot | Out-Null
    Copy-Item -Path (Join-Path $DistRoot "*") -Destination $StageRoot -Recurse -Force

    $DocsRoot = Join-Path $StageRoot "docs"
    $SourceRoot = Join-Path $StageRoot "source"
    $BuildRoot = Join-Path $StageRoot "build-materials"
    $HistoryRoot = Join-Path $StageRoot "history"
    $LogsRoot = Join-Path $StageRoot "logs"
    $DiagnosticsRoot = Join-Path $StageRoot "diagnostics"
    New-Item -ItemType Directory -Force -Path $DocsRoot,$SourceRoot,$BuildRoot,$HistoryRoot,$LogsRoot,$DiagnosticsRoot | Out-Null

    foreach ($Name in @(
        "README.md", "README_KO.md", "DEVELOPMENT_KO.md", "FUNCTION_REFERENCE_KO.md",
        "DEVELOPER_HANDOFF_KO_EN.md", "BUILD_HISTORY.md", "LICENSE.txt",
        "THIRD_PARTY_NOTICES.txt", "THIRD_PARTY_RUNTIME_INVENTORY.txt"
    )) {
        Copy-Item -LiteralPath (Join-Path $ProjectDir $Name) -Destination $DocsRoot -Force
    }
    Copy-Item -LiteralPath (Join-Path $ProjectDir "licenses") -Destination $DocsRoot -Recurse -Force

    foreach ($Name in @(
        "app.py", "catalog.py", "debug_info.py", "devices.py", "engine.py",
        "i18n.py", "recorder.py", "reference_compare.py", "report.py", "separator.py", "spectrum.py", "voicing.py"
    )) {
        Copy-Item -LiteralPath (Join-Path $ProjectDir $Name) -Destination $SourceRoot -Force
    }
    Copy-Item -LiteralPath (Join-Path $ProjectDir "tests") -Destination $SourceRoot -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $ProjectDir "tools") -Destination $SourceRoot -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $ProjectDir "resources") -Destination $SourceRoot -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $ProjectDir ".gitignore") -Destination $SourceRoot -Force
    Copy-Item -LiteralPath (Join-Path $ProjectDir ".gitattributes") -Destination $SourceRoot -Force
    # source 폴더 하나만 복사해도 새 PC에서 테스트와 빌드를 재현할 수 있도록 필수 문서·메타데이터를 함께 둔다.
    foreach ($Name in @(
        "README.md", "README_KO.md", "DEVELOPMENT_KO.md", "FUNCTION_REFERENCE_KO.md",
        "DEVELOPER_HANDOFF_KO_EN.md", "BUILD_HISTORY.md", "LICENSE.txt",
        "THIRD_PARTY_NOTICES.txt", "THIRD_PARTY_RUNTIME_INVENTORY.txt",
        "ToneMatchTMP.spec", "build.ps1", "requirements.txt", "requirements-cuda126.txt",
        "enable_cuda.ps1", "version_info.txt"
    )) {
        Copy-Item -LiteralPath (Join-Path $ProjectDir $Name) -Destination $SourceRoot -Force
    }
    Copy-Item -LiteralPath (Join-Path $ProjectDir "licenses") -Destination $SourceRoot -Recurse -Force
    if (Test-Path -LiteralPath (Join-Path $ProjectDir "QA_REPORT_v$Version.json")) {
        Copy-Item -LiteralPath (Join-Path $ProjectDir "QA_REPORT_v$Version.json") -Destination $SourceRoot -Force
    }
    Get-ChildItem -LiteralPath $SourceRoot -Directory -Filter "__pycache__" -Recurse | ForEach-Object {
        Assert-ChildPath -Path $_.FullName -Parent $SourceRoot
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }
    Get-ChildItem -LiteralPath $SourceRoot -File -Include "*.pyc","*.pyo" -Recurse | ForEach-Object {
        Assert-ChildPath -Path $_.FullName -Parent $SourceRoot
        Remove-Item -LiteralPath $_.FullName -Force
    }

    foreach ($Name in @(
        "ToneMatchTMP.spec", "build.ps1", "requirements.txt", "requirements-cuda126.txt",
        "enable_cuda.ps1", "version_info.txt"
    )) {
        Copy-Item -LiteralPath (Join-Path $ProjectDir $Name) -Destination $BuildRoot -Force
    }
    Copy-Item -LiteralPath (Join-Path $ProjectDir "BUILD_HISTORY.md") -Destination $HistoryRoot -Force
    # 공개 배포본의 빌드 로그에는 개발 PC의 사용자명과 절대 경로를 남기지 않는다.
    $PublicBuildLog = Get-Content -Raw -LiteralPath $BuildLog
    foreach ($PrivateRoot in @($ProjectDir, $env:USERPROFILE)) {
        if ($PrivateRoot) {
            $PublicBuildLog = $PublicBuildLog.Replace($PrivateRoot, "<PRIVATE_ROOT>")
            # Python/PyInstaller가 repr 형식으로 기록한 이중 백슬래시 경로도 함께 비식별화한다.
            $EscapedPrivateRoot = $PrivateRoot.Replace("\", "\\")
            $PublicBuildLog = $PublicBuildLog.Replace($EscapedPrivateRoot, "<PRIVATE_ROOT>")
        }
    }
    Set-Content -LiteralPath (Join-Path $HistoryRoot (Split-Path -Leaf $BuildLog)) -Encoding utf8 -Value $PublicBuildLog
    Set-Content -LiteralPath (Join-Path $LogsRoot "README.txt") -Encoding utf8 -Value @(
        "ToneMatch TMP는 실행 중 logs 폴더에 날짜별 UTF-8 로그를 기록합니다.",
        "쓰기 권한이 없으면 %LOCALAPPDATA%\ToneMatchTMP\logs를 사용합니다.",
        "공유하기 전에 파일명, 경로, URL 등 개인정보를 검토하세요.",
        "",
        "ToneMatch TMP writes date-stamped UTF-8 logs here at runtime.",
        "If this folder is not writable it uses %LOCALAPPDATA%\ToneMatchTMP\logs.",
        "Review paths, URLs, and other personal data before sharing a log."
    )

    $SelfTestPath = Join-Path $DiagnosticsRoot "$AppBaseName-SELF-TEST.json"
    if (Test-Path -LiteralPath $SelfTestPath) {
        Remove-Item -LiteralPath $SelfTestPath -Force
    }
    "[$(Get-Date -Format s)] Packaged EXE self-test" | Tee-Object -FilePath $BuildLog -Append
    # GUI 하위 시스템 EXE는 PowerShell의 직접 호출이 즉시 반환할 수 있으므로 프로세스 종료까지 명시적으로 기다린다.
    $SelfTestProcess = Start-Process -FilePath $ExePath -ArgumentList @(
        "--self-test-output", "`"$SelfTestPath`""
    ) -Wait -PassThru -WindowStyle Hidden
    if ($SelfTestProcess.ExitCode -ne 0) {
        throw "Packaged EXE self-test 실패 (exit $($SelfTestProcess.ExitCode))"
    }
    $SelfTest = Get-Content -Raw -LiteralPath $SelfTestPath | ConvertFrom-Json
    if (-not $SelfTest.ok -or $SelfTest.app_version -ne $Version) {
        throw "패키지 자체 진단 결과가 올바르지 않습니다."
    }
    # 자체 진단 결과를 공유해도 로컬 사용자 폴더가 노출되지 않도록 캐시 경로를 일반화한다.
    if ($SelfTest.separator_runtime.cache_path) {
        $SelfTest.separator_runtime.cache_path = "%USERPROFILE%\.cache\huggingface\hub\models--adefossez--HTDemucs-6s"
        $SelfTest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $SelfTestPath -Encoding utf8
    }
    # 자체 진단까지 기록된 최종 공개 로그로 앞서 복사한 파일을 덮어쓴다.
    $PublicBuildLog = Get-Content -Raw -LiteralPath $BuildLog
    foreach ($PrivateRoot in @($ProjectDir, $env:USERPROFILE)) {
        if ($PrivateRoot) {
            $PublicBuildLog = $PublicBuildLog.Replace($PrivateRoot, "<PRIVATE_ROOT>")
            $EscapedPrivateRoot = $PrivateRoot.Replace("\", "\\")
            $PublicBuildLog = $PublicBuildLog.Replace($EscapedPrivateRoot, "<PRIVATE_ROOT>")
        }
    }
    Set-Content -LiteralPath (Join-Path $HistoryRoot (Split-Path -Leaf $BuildLog)) -Encoding utf8 -Value $PublicBuildLog
    if (Test-Path -LiteralPath (Join-Path $ProjectDir "QA_REPORT_v$Version.json")) {
        Copy-Item -LiteralPath (Join-Path $ProjectDir "QA_REPORT_v$Version.json") -Destination $DiagnosticsRoot -Force
    }

    & $PythonExe tools\write_manifest.py --root $StageRoot --output (Join-Path $StageRoot "MANIFEST.json") --version $Version
    if ($LASTEXITCODE -ne 0) { throw "배포 manifest 생성에 실패했습니다." }

    New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
    $ZipPath = Join-Path $ReleaseDir "$AppBaseName-Windows-x64-Portable-Dev.zip"
    $ChecksumsPath = Join-Path $ReleaseDir "$AppBaseName-SHA256SUMS.txt"
    if (-not $SkipZip) {
        if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
        Compress-Archive -LiteralPath $StageRoot -DestinationPath $ZipPath -CompressionLevel Optimal
    }

    $ChecksumLines = @()
    $ChecksumLines += "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 -LiteralPath $ExePath).Hash, "$AppBaseName\$AppBaseName.exe"
    $ChecksumLines += "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 -LiteralPath $SelfTestPath).Hash, "$AppBaseName\diagnostics\$(Split-Path -Leaf $SelfTestPath)"
    $ManifestPath = Join-Path $StageRoot "MANIFEST.json"
    $PublicBuildLogPath = Join-Path $HistoryRoot (Split-Path -Leaf $BuildLog)
    $ChecksumLines += "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 -LiteralPath $ManifestPath).Hash, "$AppBaseName\MANIFEST.json"
    $ChecksumLines += "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 -LiteralPath $PublicBuildLogPath).Hash, "$AppBaseName\history\$(Split-Path -Leaf $PublicBuildLogPath)"
    if (-not $SkipZip) {
        $ChecksumLines += "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 -LiteralPath $ZipPath).Hash, (Split-Path -Leaf $ZipPath)
    }
    Set-Content -LiteralPath $ChecksumsPath -Encoding ascii -Value $ChecksumLines

    Write-Host "완료: $StageRoot"
    if (-not $SkipZip) { Write-Host "ZIP:  $ZipPath" }
    Write-Host "SHA:  $ChecksumsPath"
} finally {
    Pop-Location
}
