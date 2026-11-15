# No build side effects: decide output policy before compiling or deleting staging.
function Copy-PublicDistribution {
    param([Parameter(Mandatory)][string]$Source, [Parameter(Mandatory)][string]$Destination)
    # Deliberate allowlist: local account/identity files must never enter an archive.
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($Name in @('signpath-artifact-configuration.xml', 'signpath-settings.example.json',
                         'store-identity.example.json', 'STORE_SUBMISSION_KO.md')) {
        Copy-Item -LiteralPath (Join-Path $Source $Name) -Destination $Destination -Force
    }
}

function Get-DistributionPlan {
    param(
        [Parameter(Mandatory)][string]$Version,
        [Parameter(Mandatory)][string]$OutputDir,
        [ValidateSet('SigningInput', 'Development')][string]$Mode = 'SigningInput',
        [switch]$SkipZip
    )
    if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid application version.' }
    $Base = "ToneMatchTMP-v$Version"
    $ZipPath = Join-Path $OutputDir "$Base-Windows-x64-Portable-Dev.zip"
    $ChecksumsPath = Join-Path $OutputDir "$Base-SHA256SUMS.txt"
    $WriteReleaseFiles = $Mode -eq 'Development'
    if ($WriteReleaseFiles) {
        foreach ($ArtifactPath in @($ZipPath, $ChecksumsPath)) {
            if (Test-Path -LiteralPath $ArtifactPath) {
                throw "Refusing to replace an existing artifact: $ArtifactPath"
            }
        }
    }
    [pscustomobject]@{
        Mode = $Mode
        Status = if ($WriteReleaseFiles) { 'unsigned_development' } else { 'unsigned_signing_input' }
        WriteReleaseFiles = $WriteReleaseFiles
        CreateZip = $WriteReleaseFiles -and -not $SkipZip
        ZipPath = $ZipPath
        ChecksumsPath = $ChecksumsPath
    }
}
