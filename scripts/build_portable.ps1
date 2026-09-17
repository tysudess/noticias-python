param(
    [string]$OutputDir = "portable-out"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

if (-not $IsWindows) { throw "A build portable deve ser executada no Windows." }
if ($env:PROCESSOR_ARCHITECTURE -notmatch "AMD64") { throw "A build deste passo é Windows x64." }

$pythonVersion = (& python --version 2>&1 | Out-String).Trim()
if ($pythonVersion -notmatch "Python 3\.12\.") { throw "Python 3.12.x é obrigatório para a build. Detectado: $pythonVersion" }

Write-Host "== Limpeza de build anterior =="
foreach ($path in @("build", "dist", ".globoplay-helper-build", ".portable-tools", $OutputDir)) {
    if (Test-Path $path) { Remove-Item $path -Recurse -Force }
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Write-Host "== Dependências de build =="
python -m pip install --disable-pip-version-check -r requirements.txt -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependências." }

Write-Host "== Helper interno Globoplay =="
python tools/build-globoplay-login-helper.py
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar GloboplayLoginHelper.exe." }
$helper = Join-Path $Root "resources/globoplay-login-helper/GloboplayLoginHelper.exe"
if (-not (Test-Path $helper) -or (Get-Item $helper).Length -lt 20000000) { throw "Helper Globoplay ausente ou incompleto." }

Write-Host "== PyInstaller onedir =="
python -m PyInstaller --noconfirm --clean MonitorDeNoticias.spec
if ($LASTEXITCODE -ne 0) { throw "Falha no PyInstaller." }
$PortableRoot = Join-Path $Root "dist/MonitorDeNoticias"
$Exe = Join-Path $PortableRoot "MonitorDeNoticias.exe"
if (-not (Test-Path $Exe)) { throw "MonitorDeNoticias.exe não foi gerado." }

Write-Host "== Estrutura externa gravável/resources =="
foreach ($dir in @("resources", "bin", "data", "logs", "temp", "Videos", "VideoEditorExports")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $PortableRoot $dir) | Out-Null
}
Copy-Item (Join-Path $Root "resources/*") (Join-Path $PortableRoot "resources") -Recurse -Force
Copy-Item (Join-Path $Root "portable/README_PORTABLE.txt") (Join-Path $PortableRoot "README_PORTABLE.txt") -Force
Copy-Item (Join-Path $Root "portable/THIRD_PARTY_NOTICES.txt") (Join-Path $PortableRoot "THIRD_PARTY_NOTICES.txt") -Force

Write-Host "== Binários do Extrator/Editor =="
$ToolsRoot = Join-Path $Root ".portable-tools"
$BinStage = Join-Path $ToolsRoot "bin"
New-Item -ItemType Directory -Force -Path $BinStage | Out-Null

# PASSO 27: manter exatamente as versões do portable já validado; não usar aliases latest mutáveis.
Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/download/2026.08.30.232658/yt-dlp.exe" -OutFile (Join-Path $BinStage "yt-dlp.exe") -TimeoutSec 180
Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp.exe" -OutFile (Join-Path $BinStage "yt-dlp-stable.exe") -TimeoutSec 180
Invoke-WebRequest -Uri "https://github.com/denoland/deno/releases/download/v2.9.6/deno-x86_64-pc-windows-msvc.zip" -OutFile (Join-Path $ToolsRoot "deno.zip") -TimeoutSec 180
Expand-Archive (Join-Path $ToolsRoot "deno.zip") (Join-Path $ToolsRoot "deno") -Force
Copy-Item (Join-Path $ToolsRoot "deno/deno.exe") (Join-Path $BinStage "deno.exe") -Force

# FFmpeg/FFprobe: o workflow deve materializar os executáveis byte-a-byte do último portable validado.
# Não baixar/recompilar/substituir FFmpeg neste passo.
$validatedFfmpegDir = $env:MONITOR_VALIDATED_FFMPEG_DIR
if (-not $validatedFfmpegDir -or -not (Test-Path $validatedFfmpegDir)) {
    throw "MONITOR_VALIDATED_FFMPEG_DIR ausente. O build requer os binários FFmpeg/FFprobe auditados do portable validado."
}
$ffmpegPath = Join-Path $validatedFfmpegDir "ffmpeg.exe"
$ffprobePath = Join-Path $validatedFfmpegDir "ffprobe.exe"
if (-not (Test-Path $ffmpegPath) -or -not (Test-Path $ffprobePath)) { throw "ffmpeg.exe/ffprobe.exe auditados ausentes." }
$expectedFfmpegSha = "91678b935eb52cc740249474574b6042768b744c622347f28a1b487e1ed29915"
$expectedFfprobeSha = "c42ada47df746e3788e2ba3ed2f7af07662a58f9088f9894e1b14d3d5c432263"
$downloadedFfmpegSha = (Get-FileHash $ffmpegPath -Algorithm SHA256).Hash.ToLowerInvariant()
$downloadedFfprobeSha = (Get-FileHash $ffprobePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($downloadedFfmpegSha -ne $expectedFfmpegSha) { throw "FFmpeg materializado diverge do binário auditado: $downloadedFfmpegSha" }
if ($downloadedFfprobeSha -ne $expectedFfprobeSha) { throw "FFprobe materializado diverge do binário auditado: $downloadedFfprobeSha" }
Write-Host "FFMPEG_AUDITED_SHA256=$downloadedFfmpegSha"
Write-Host "FFPROBE_AUDITED_SHA256=$downloadedFfprobeSha"
Copy-Item $ffmpegPath (Join-Path $BinStage "ffmpeg.exe") -Force
Copy-Item $ffprobePath (Join-Path $BinStage "ffprobe.exe") -Force

foreach ($name in @("yt-dlp.exe", "yt-dlp-stable.exe", "deno.exe", "ffmpeg.exe", "ffprobe.exe")) {
    $source = Join-Path $BinStage $name
    if (-not (Test-Path $source) -or (Get-Item $source).Length -lt 100000) { throw "Binário inválido: $name" }
    Copy-Item $source (Join-Path $PortableRoot "bin/$name") -Force
}

$ytNightly = (& (Join-Path $PortableRoot "bin/yt-dlp.exe") --version 2>&1 | Select-Object -First 1)
$ytStable = (& (Join-Path $PortableRoot "bin/yt-dlp-stable.exe") --version 2>&1 | Select-Object -First 1)
$denoVersion = (& (Join-Path $PortableRoot "bin/deno.exe") --version 2>&1 | Select-Object -First 1)
$ffmpegVersion = (& (Join-Path $PortableRoot "bin/ffmpeg.exe") -version 2>&1 | Select-Object -First 1)
$ffprobeVersion = (& (Join-Path $PortableRoot "bin/ffprobe.exe") -version 2>&1 | Select-Object -First 1)

Write-Host "== Compliance de redistribuição =="
python scripts/collect_portable_licenses.py $PortableRoot
if ($LASTEXITCODE -ne 0) { throw "Falha ao coletar textos oficiais de licença/notice." }

Write-Host "== Metadata da build =="
$commit = (& git rev-parse HEAD).Trim()
$buildDate = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$pyside = (& python -c "import PySide6; print(PySide6.__version__)" 2>&1 | Out-String).Trim()
$qt = (& python -c "from PySide6.QtCore import qVersion; print(qVersion())" 2>&1 | Out-String).Trim()
$pyinstaller = (& python -m PyInstaller --version 2>&1 | Out-String).Trim()
$info = [ordered]@{
    APP_VERSION = "technical-step18-portable"
    BUILD_COMMIT = $commit
    BUILD_DATE = $buildDate
    PYTHON = $pythonVersion
    PYSIDE6 = $pyside
    QT = $qt
    PYINSTALLER = $pyinstaller
    ARCHITECTURE = "windows-x64"
    BUILD_TYPE = "onedir"
    YT_DLP_NIGHTLY = "$ytNightly"
    YT_DLP_STABLE = "$ytStable"
    DENO = "$denoVersion"
    FFMPEG = "$ffmpegVersion"
    FFPROBE = "$ffprobeVersion"
}
$info | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $PortableRoot "BUILD-INFO.json") -Encoding utf8
$commit | Set-Content (Join-Path $PortableRoot "BUILD-SHA.txt") -Encoding ascii

Write-Host "== Validações estruturais =="
$required = @(
    "MonitorDeNoticias.exe",
    "_internal",
    "resources/monitor-icon.svg",
    "resources/pdf-default-cover.b64",
    "resources/globoplay-login-helper/GloboplayLoginHelper.exe",
    "bin/yt-dlp.exe",
    "bin/yt-dlp-stable.exe",
    "bin/deno.exe",
    "bin/ffmpeg.exe",
    "bin/ffprobe.exe",
    "data",
    "logs",
    "temp",
    "Videos",
    "VideoEditorExports",
    "README_PORTABLE.txt",
    "THIRD_PARTY_NOTICES.txt",
    "licenses",
    "LICENSES-MANIFEST.json",
    "licenses/python-runtime/LICENSE.txt",
    "licenses/ffmpeg/COPYING.GPLv3.txt",
    "licenses/yt-dlp-stable/THIRD_PARTY_LICENSES.txt",
    "licenses/yt-dlp-nightly/THIRD_PARTY_LICENSES.txt",
    "licenses/deno/LICENSE.md",
    "BUILD-INFO.json",
    "BUILD-SHA.txt"
)
foreach ($rel in $required) {
    if (-not (Test-Path (Join-Path $PortableRoot $rel))) { throw "Item obrigatório ausente: $rel" }
}
$qwindows = Get-ChildItem (Join-Path $PortableRoot "_internal") -Recurse -Filter "qwindows.dll" | Select-Object -First 1
if (-not $qwindows) { throw "Plugin Qt platforms/qwindows.dll ausente." }
$multimediaDlls = Get-ChildItem (Join-Path $PortableRoot "_internal") -Recurse -Filter "*.dll" | Where-Object { $_.FullName -match "multimedia" }
if (-not $multimediaDlls) { throw "Plugins/DLLs QtMultimedia não encontrados." }
if (Test-Path (Join-Path $PortableRoot "src")) { throw "src/ não pode entrar no portable." }
if (Test-Path (Join-Path $PortableRoot "tests")) { throw "tests/ não pode entrar no portable." }
if (Test-Path (Join-Path $PortableRoot ".git")) { throw ".git não pode entrar no portable." }

Write-Host "== Smoke local da pasta recém-construída =="
$LocalSmokeResult = Join-Path $env:RUNNER_TEMP "passo18-local-portable-smoke.json"
if (Test-Path $LocalSmokeResult) { Remove-Item $LocalSmokeResult -Force }
$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $Exe
$psi.WorkingDirectory = $env:WINDIR
$psi.UseShellExecute = $false
$psi.Environment["PATH"] = "$env:WINDIR\System32;$env:WINDIR"
$psi.Environment["MONITOR_PORTABLE_SMOKE"] = "1"
$psi.Environment["MONITOR_PORTABLE_SMOKE_RESULT"] = $LocalSmokeResult
$localSmoke = [System.Diagnostics.Process]::Start($psi)
if (-not $localSmoke) { throw "Não foi possível iniciar smoke local da pasta construída." }
if (-not $localSmoke.WaitForExit(240000)) {
    $localSmoke.Kill($true)
    throw "Smoke local excedeu 240 segundos."
}
if (-not (Test-Path $LocalSmokeResult)) { throw "Smoke local não produziu resultado." }
$localPayload = Get-Content $LocalSmokeResult -Raw | ConvertFrom-Json
if ($localSmoke.ExitCode -ne 0 -or -not $localPayload.ok) {
    Get-Content $LocalSmokeResult
    throw "Smoke local falhou (exit=$($localSmoke.ExitCode)): $($localPayload.error)"
}
Write-Host "LOCAL_PORTABLE_SMOKE_OK"
Get-Content $LocalSmokeResult
Remove-Item $LocalSmokeResult -Force

Write-Host "== Limpeza de estado artificial antes do ZIP =="
foreach ($dir in @("data", "logs", "temp", "Videos", "VideoEditorExports")) {
    $full = Join-Path $PortableRoot $dir
    if (Test-Path $full) {
        Get-ChildItem $full -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    }
}
foreach ($dir in @("data", "logs", "temp", "Videos", "VideoEditorExports")) {
    $full = Join-Path $PortableRoot $dir
    if (Get-ChildItem $full -Force -ErrorAction SilentlyContinue | Select-Object -First 1) {
        throw "Diretório gravável contém estado de teste antes do ZIP: $dir"
    }
}
$sensitiveNames = Get-ChildItem $PortableRoot -Recurse -File | Where-Object {
    $_.Name -match "(?i)(monitor_prefs\.properties|news\.db|videos\.db|\.dpapi$|cookies?|session\.txt$)" -and
    $_.FullName -notmatch "resources\\globoplay-login-helper"
}
if ($sensitiveNames) {
    $names = ($sensitiveNames | Select-Object -ExpandProperty FullName) -join "; "
    throw "Estado sensível/pessoal inesperado antes do ZIP: $names"
}

Write-Host "== ZIP final =="
$ZipName = "MONITOR-DE-NOTICIAS-PYTHON-portable-windows-x64.zip"
$ZipPath = Join-Path (Resolve-Path $OutputDir).Path $ZipName
Compress-Archive -Path $PortableRoot -DestinationPath $ZipPath -CompressionLevel Optimal
$hash = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $ZipName" | Set-Content "$ZipPath.sha256" -Encoding ascii

$folderBytes = (Get-ChildItem $PortableRoot -Recurse -File | Measure-Object Length -Sum).Sum
$zipBytes = (Get-Item $ZipPath).Length
Write-Host "PORTABLE_ROOT=$PortableRoot"
Write-Host "PORTABLE_ZIP=$ZipPath"
Write-Host "PORTABLE_SHA256=$hash"
Write-Host "PORTABLE_FOLDER_BYTES=$folderBytes"
Write-Host "PORTABLE_ZIP_BYTES=$zipBytes"
Write-Host "FFMPEG_VERSION=$ffmpegVersion"
Write-Host "FFPROBE_VERSION=$ffprobeVersion"
