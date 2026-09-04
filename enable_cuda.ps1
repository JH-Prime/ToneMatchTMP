[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$PythonPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RequirementsPath = Join-Path $ProjectDir "requirements-cuda126.txt"

# 경로를 생략하면 활성 가상환경, 프로젝트 상위 가상환경, 프로젝트 내부 가상환경 순으로 찾는다.
if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $Candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:VIRTUAL_ENV)) {
        $Candidates += Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
    }
    $Candidates += Join-Path $ProjectDir "..\.venv\Scripts\python.exe"
    $Candidates += Join-Path $ProjectDir ".venv\Scripts\python.exe"

    foreach ($Candidate in $Candidates) {
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
            $PythonPath = $Candidate
            break
        }
    }
}

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    throw "Python 가상환경을 찾지 못했습니다. -PythonPath 매개변수로 가상환경의 python.exe 경로를 지정해 주세요."
}

if (-not [System.IO.Path]::IsPathRooted($PythonPath)) {
    $PythonPath = Join-Path (Get-Location) $PythonPath
}
$ResolvedPython = [System.IO.Path]::GetFullPath($PythonPath)

if (-not (Test-Path -LiteralPath $ResolvedPython -PathType Leaf)) {
    throw "Python 실행 파일을 찾을 수 없습니다: $ResolvedPython"
}
if (-not (Test-Path -LiteralPath $RequirementsPath -PathType Leaf)) {
    throw "CUDA 요구사항 파일을 찾을 수 없습니다: $RequirementsPath"
}

# 잘못된 Python 또는 32비트 환경에 설치하지 않도록 먼저 실행 환경을 확인한다.
$EnvironmentCode = @'
import json
import platform
import sys

print(json.dumps({
    "major": sys.version_info.major,
    "minor": sys.version_info.minor,
    "version": platform.python_version(),
    "system": platform.system(),
    "architecture": platform.architecture()[0],
    "machine": platform.machine(),
}))
'@
$EnvironmentJson = & $ResolvedPython -c $EnvironmentCode
if ($LASTEXITCODE -ne 0) {
    throw "Python 실행 환경을 확인하지 못했습니다."
}
$EnvironmentInfo = $EnvironmentJson | ConvertFrom-Json

if (($EnvironmentInfo.major -ne 3) -or ($EnvironmentInfo.minor -ne 12)) {
    throw "이 CUDA wheel은 CPython 3.12 전용입니다. 현재 버전: $($EnvironmentInfo.version)"
}
if ($EnvironmentInfo.system -ne "Windows") {
    throw "이 CUDA wheel은 Windows 전용입니다. 현재 운영체제: $($EnvironmentInfo.system)"
}
if ($EnvironmentInfo.architecture -ne "64bit") {
    throw "이 CUDA wheel은 Windows x64 전용입니다. 현재 아키텍처: $($EnvironmentInfo.architecture) / $($EnvironmentInfo.machine)"
}

Write-Host "ToneMatch TMP GPU 개발 런타임을 준비합니다." -ForegroundColor Cyan
Write-Host "Python: $ResolvedPython"
Write-Host "환경: $($EnvironmentInfo.system), Python $($EnvironmentInfo.version), $($EnvironmentInfo.architecture), $($EnvironmentInfo.machine)"
Write-Host "참고: CUDA wheel은 매우 커서 일반 portable ZIP에는 포함되지 않습니다." -ForegroundColor Yellow

# CPU용 torch를 같은 버전의 공식 CUDA 12.6 wheel로 교체한다.
& $ResolvedPython -m pip install --force-reinstall --no-deps --requirement $RequirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "PyTorch CUDA 12.6 wheel 설치에 실패했습니다. 위의 pip 오류를 확인해 주세요."
}

# 설치 직후 CUDA 빌드 버전, 실제 사용 가능 여부, 선택된 GPU 이름을 함께 검증한다.
$VerificationCode = @'
import json
import torch

available = bool(torch.cuda.is_available())
print(json.dumps({
    "torch_version": str(torch.__version__),
    "cuda_build": torch.version.cuda,
    "cuda_available": available,
    "gpu_name": torch.cuda.get_device_name(0) if available else None,
}))
'@
$VerificationJson = & $ResolvedPython -c $VerificationCode
if ($LASTEXITCODE -ne 0) {
    throw "설치된 PyTorch의 CUDA 상태를 확인하지 못했습니다."
}
$Verification = $VerificationJson | ConvertFrom-Json

Write-Host "PyTorch 버전: $($Verification.torch_version)"
Write-Host "PyTorch CUDA 빌드: $($Verification.cuda_build)"
Write-Host "CUDA 사용 가능: $($Verification.cuda_available)"

if ([string]::IsNullOrWhiteSpace([string]$Verification.cuda_build)) {
    throw "CUDA 빌드가 아닌 PyTorch가 설치되었습니다. requirements-cuda126.txt와 네트워크 상태를 확인해 주세요."
}
if ($Verification.cuda_build -ne "12.6") {
    throw "요청한 CUDA 12.6 빌드와 다릅니다. 확인된 CUDA 빌드: $($Verification.cuda_build)"
}
if (-not ([string]$Verification.torch_version).StartsWith("2.13.0+cu126", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "요청한 PyTorch 2.13.0+cu126 빌드와 다릅니다. 확인된 버전: $($Verification.torch_version)"
}
if (-not $Verification.cuda_available) {
    Write-Warning "CUDA 12.6 wheel은 설치되었지만 GPU를 사용할 수 없습니다. NVIDIA GPU, 드라이버, 재부팅 필요 여부를 확인해 주세요."
    throw "GPU 검증에 실패했으므로 GPU용 EXE 빌드를 진행하지 마세요."
}

Write-Host "GPU 이름: $($Verification.gpu_name)" -ForegroundColor Green
Write-Host "CUDA GPU 런타임 검증을 완료했습니다. 이제 이 가상환경으로 GPU용 EXE를 빌드할 수 있습니다." -ForegroundColor Green
