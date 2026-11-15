param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string]$ExpectedPublisher,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Fa-f0-9]{40}$')][string]$ExpectedThumbprint,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+$')][string]$Version
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
if ([string]::IsNullOrWhiteSpace($ExpectedPublisher)) {
    throw 'Configure the exact approved Authenticode publisher subject.'
}
$File = Get-Item -LiteralPath $FilePath
if ($File.PSIsContainer -or ($File.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Authenticode input must be a regular file.'
}
$BeforeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $File.FullName).Hash
$Signature = Get-AuthenticodeSignature -LiteralPath $File.FullName
if ($Signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
    throw "Authenticode validation failed: $($Signature.Status)."
}
if ($Signature.SignatureType -ne 'Authenticode') {
    throw 'An embedded Authenticode signature is required; catalog trust is insufficient.'
}
if (-not $Signature.SignerCertificate -or
    $Signature.SignerCertificate.Subject -cne $ExpectedPublisher -or
    $Signature.SignerCertificate.Thumbprint -ine $ExpectedThumbprint) {
    throw 'Authenticode publisher or certificate thumbprint differs from the approved identity.'
}
if (-not $Signature.TimeStamperCertificate) {
    throw 'A trusted Authenticode timestamp is required for a public release.'
}
$Info = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($File.FullName)
if ($Info.ProductName -cne 'ToneMatch TMP' -or $Info.ProductVersion -cne $Version -or
    $Info.FileVersion -cne $Version -or $Info.OriginalFilename -cne "ToneMatchTMP-v$Version.exe") {
    throw 'Authenticode file metadata does not match the expected product/version/filename.'
}
$AfterHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $File.FullName).Hash
if ($BeforeHash -cne $AfterHash) { throw 'Authenticode input changed during validation.' }
[ordered]@{
    status = 'Valid'
    publisher = $Signature.SignerCertificate.Subject
    thumbprint = $Signature.SignerCertificate.Thumbprint.ToUpperInvariant()
    timestamp_publisher = $Signature.TimeStamperCertificate.Subject
    product_version = $Info.ProductVersion
    sha256 = $AfterHash
} | ConvertTo-Json -Depth 4
