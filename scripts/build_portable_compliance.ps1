param(
    [string]$OutputDir = "portable-out"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

Write-Host "== Build funcional base =="
& (Join-Path $PSScriptRoot "build_portable.ps1") -OutputDir $OutputDir
if ($LASTEXITCODE -ne 0) { throw "Build funcional base falhou." }

$PortableRoot = Join-Path $Root "dist/MonitorDeNoticias"
if (-not (Test-Path (Join-Path $PortableRoot "MonitorDeNoticias.exe"))) {
    throw "Raiz portable construída não encontrada."
}

Write-Host "== Compliance de redistribuição =="
Copy-Item (Join-Path $Root "portable/THIRD_PARTY_NOTICES.txt") (Join-Path $PortableRoot "THIRD_PARTY_NOTICES.txt") -Force
python scripts/collect_portable_licenses.py $PortableRoot
if ($LASTEXITCODE -ne 0) { throw "Coleta de textos/notices de compliance falhou." }

foreach ($required in @(
    "THIRD_PARTY_NOTICES.txt",
    "LICENSES-MANIFEST.json",
    "licenses/python-runtime/LICENSE.txt",
    "licenses/ffmpeg/COPYING.GPLv3.txt",
    "licenses/ffmpeg/LICENSE.md",
    "licenses/yt-dlp-stable/THIRD_PARTY_LICENSES.txt",
    "licenses/yt-dlp-stable/LICENSE.txt",
    "licenses/yt-dlp-nightly/THIRD_PARTY_LICENSES.txt",
    "licenses/yt-dlp-nightly/LICENSE.txt",
    "licenses/deno/LICENSE.md"
)) {
    if (-not (Test-Path (Join-Path $PortableRoot $required))) {
        throw "Compliance obrigatório ausente: $required"
    }
}

$licenseCount = (Get-ChildItem (Join-Path $PortableRoot "licenses") -Recurse -File | Measure-Object).Count
if ($licenseCount -lt 20) { throw "Inventário de licenças inesperadamente pequeno: $licenseCount arquivos." }
Write-Host "PORTABLE_LICENSE_FILE_COUNT=$licenseCount"

Write-Host "== Recriação do ZIP com compliance =="
$ZipName = "MONITOR-DE-NOTICIAS-PYTHON-portable-windows-x64.zip"
$Out = (Resolve-Path $OutputDir).Path
$ZipPath = Join-Path $Out $ZipName
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
if (Test-Path "$ZipPath.sha256") { Remove-Item "$ZipPath.sha256" -Force }
Compress-Archive -Path $PortableRoot -DestinationPath $ZipPath -CompressionLevel Optimal
$hash = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $ZipName" | Set-Content "$ZipPath.sha256" -Encoding ascii
$folderBytes = (Get-ChildItem $PortableRoot -Recurse -File | Measure-Object Length -Sum).Sum
$zipBytes = (Get-Item $ZipPath).Length
Write-Host "COMPLIANCE_PORTABLE_ZIP=$ZipPath"
Write-Host "COMPLIANCE_PORTABLE_SHA256=$hash"
Write-Host "COMPLIANCE_PORTABLE_FOLDER_BYTES=$folderBytes"
Write-Host "COMPLIANCE_PORTABLE_ZIP_BYTES=$zipBytes"
