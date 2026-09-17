param(
    [Parameter(Mandatory=$true)][string]$ZipPath
)

$ErrorActionPreference = "Stop"
$ZipPath = (Resolve-Path $ZipPath).Path
$ExpectedHashFile = "$ZipPath.sha256"
if (-not (Test-Path $ExpectedHashFile)) { throw "Arquivo SHA-256 ausente: $ExpectedHashFile" }
$expected = ((Get-Content $ExpectedHashFile -Raw).Trim() -split "\s+")[0].ToLowerInvariant()
$actual = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($expected -ne $actual) { throw "SHA-256 do ZIP não confere." }

$ExtractBase = Join-Path $env:RUNNER_TEMP "Edição Portable Monitor de Notícias"
if (Test-Path $ExtractBase) { Remove-Item $ExtractBase -Recurse -Force }
New-Item -ItemType Directory -Force $ExtractBase | Out-Null
Expand-Archive $ZipPath $ExtractBase -Force
$PortableRoot = Get-ChildItem $ExtractBase -Directory | Where-Object { Test-Path (Join-Path $_.FullName "MonitorDeNoticias.exe") } | Select-Object -First 1
if (-not $PortableRoot) { throw "Raiz portable não encontrada após reextrair o ZIP." }
$Root = $PortableRoot.FullName

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
    "README_PORTABLE.txt",
    "THIRD_PARTY_NOTICES.txt",
    "BUILD-INFO.json",
    "BUILD-SHA.txt"
)
foreach ($rel in $required) {
    if (-not (Test-Path (Join-Path $Root $rel))) { throw "Item ausente no ZIP reextraído: $rel" }
}
foreach ($forbidden in @("src", "tests", ".git", ".venv", "venv")) {
    if (Test-Path (Join-Path $Root $forbidden)) { throw "Conteúdo de desenvolvimento indevido no portable: $forbidden" }
}

$qwindows = Get-ChildItem (Join-Path $Root "_internal") -Recurse -Filter "qwindows.dll" | Select-Object -First 1
if (-not $qwindows) { throw "qwindows.dll não encontrado no portable." }
$qtCore = Get-ChildItem (Join-Path $Root "_internal") -Recurse -Filter "Qt6Core.dll" | Select-Object -First 1
$qtGui = Get-ChildItem (Join-Path $Root "_internal") -Recurse -Filter "Qt6Gui.dll" | Select-Object -First 1
$qtWidgets = Get-ChildItem (Join-Path $Root "_internal") -Recurse -Filter "Qt6Widgets.dll" | Select-Object -First 1
$qtMultimedia = Get-ChildItem (Join-Path $Root "_internal") -Recurse -Filter "Qt6Multimedia.dll" | Select-Object -First 1
$qtMultimediaWidgets = Get-ChildItem (Join-Path $Root "_internal") -Recurse -Filter "Qt6MultimediaWidgets.dll" | Select-Object -First 1
if (-not $qtCore -or -not $qtGui -or -not $qtWidgets -or -not $qtMultimedia -or -not $qtMultimediaWidgets) { throw "DLLs Qt essenciais ausentes." }
$mediaPlugins = Get-ChildItem (Join-Path $Root "_internal") -Recurse -File | Where-Object { $_.FullName -match "plugins[\\/]multimedia" }
if (-not $mediaPlugins) { throw "Plugins QtMultimedia ausentes." }

# Prova que FFmpeg/FFprobe próprios funcionam sem depender do PATH do sistema.
$SampleDir = Join-Path $env:RUNNER_TEMP "portable-media"
if (Test-Path $SampleDir) { Remove-Item $SampleDir -Recurse -Force }
New-Item -ItemType Directory -Force $SampleDir | Out-Null
$Sample = Join-Path $SampleDir "amostra portable.mp4"
$ExportProbe = Join-Path $SampleDir "probe.json"
& (Join-Path $Root "bin/ffmpeg.exe") -y -f lavfi -i "testsrc=size=320x240:rate=25" -f lavfi -i "sine=frequency=440:sample_rate=44100" -t 2 -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 96k $Sample | Out-Null
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Sample)) { throw "FFmpeg incluído não conseguiu gerar mídia de teste." }
& (Join-Path $Root "bin/ffprobe.exe") -v error -show_streams -show_format -of json $Sample | Set-Content $ExportProbe -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "FFprobe incluído falhou." }
$probe = Get-Content $ExportProbe -Raw | ConvertFrom-Json
if (-not ($probe.streams | Where-Object codec_type -eq "video")) { throw "FFprobe não encontrou vídeo." }
if (-not ($probe.streams | Where-Object codec_type -eq "audio")) { throw "FFprobe não encontrou áudio." }

function New-PortableProcess([bool]$Smoke, [string]$SmokeResult = "") {
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = Join-Path $Root "MonitorDeNoticias.exe"
    $psi.WorkingDirectory = $env:WINDIR
    $psi.UseShellExecute = $false
    # Remove Python/FFmpeg/etc. externos: somente APIs do Windows ficam no PATH.
    $psi.Environment["PATH"] = "$env:WINDIR\System32;$env:WINDIR"
    if ($Smoke) {
        $psi.Environment["MONITOR_PORTABLE_SMOKE"] = "1"
        $psi.Environment["MONITOR_PORTABLE_SMOKE_RESULT"] = $SmokeResult
    }
    return [System.Diagnostics.Process]::Start($psi)
}

# Primeira abertura NORMAL do EXE, não do hook: prova startup frozen, AppContainer,
# paths e criação de dados sem Python instalado/configurado no ambiente do processo.
$process = New-PortableProcess $false
if (-not $process) { throw "Não foi possível iniciar MonitorDeNoticias.exe." }
try {
    $deadline = [DateTime]::UtcNow.AddSeconds(25)
    do {
        Start-Sleep -Milliseconds 500
        if ($process.HasExited) { throw "MonitorDeNoticias.exe encerrou prematuramente com código $($process.ExitCode)." }
        $ready = (Test-Path (Join-Path $Root "data/news.db")) -and (Test-Path (Join-Path $Root "data/videos.db")) -and (Test-Path (Join-Path $Root "logs/monitor-noticias.log"))
    } while (-not $ready -and [DateTime]::UtcNow -lt $deadline)
    if (-not $ready) { throw "Primeira execução não criou bancos/log dentro da raiz portable." }
    Start-Sleep -Seconds 2
    if ($process.HasExited) { throw "Monitor encerrou após primeira inicialização." }
    Write-Host "PORTABLE_NORMAL_START_OK pid=$($process.Id) root=$Root"
}
finally {
    if ($process -and -not $process.HasExited) {
        $process.Kill($true)
        $process.WaitForExit(10000) | Out-Null
    }
}

# O runner de Actions não fornece desktop interativo confiável para UI Automation.
# O mesmo EXE congelado é relançado com um runtime hook INERTE no uso normal.
# Esse hook instancia as classes reais empacotadas, navega o MainWindow, testa PDF,
# Extrator, QMediaPlayer, seek, FFmpeg/FFprobe, exportação e shutdown.
$SmokeResult = Join-Path $env:RUNNER_TEMP "portable-smoke-result.json"
if (Test-Path $SmokeResult) { Remove-Item $SmokeResult -Force }
$smoke = New-PortableProcess $true $SmokeResult
if (-not $smoke) { throw "Não foi possível iniciar o mesmo EXE em modo de validação interna." }
if (-not $smoke.WaitForExit(180000)) {
    $smoke.Kill($true)
    throw "Smoke interno do portable excedeu 180 segundos."
}
if (-not (Test-Path $SmokeResult)) { throw "Smoke interno não produziu resultado." }
$smokePayload = Get-Content $SmokeResult -Raw | ConvertFrom-Json
Get-Content $SmokeResult
if ($smoke.ExitCode -ne 0 -or -not $smokePayload.ok) {
    throw "Smoke interno do próprio EXE falhou (exit=$($smoke.ExitCode)): $($smokePayload.error)"
}

$expectedPages = @("HOME","NEWS","VIDEOS","DEMANDS","SOURCES","HISTORY","TERMS","STOP","SETTINGS","PDF_EDITOR","EXTRACTOR","VIDEO_EDITOR")
foreach ($page in $expectedPages) {
    if ($smokePayload.navigated -notcontains $page) { throw "Navegação empacotada não percorreu $page." }
}
if ($smokePayload.video_codec -ne "h264" -or $smokePayload.audio_codec -ne "aac") { throw "Exportação empacotada não preservou H.264/AAC." }
if ([int]$smokePayload.player_position_ms -lt 300) { throw "Preview empacotado não avançou." }
if ([Math]::Abs([int]$smokePayload.seek_position_ms - 1000) -gt 250) { throw "Seek empacotado fora da tolerância." }

# O hook testa shutdown coordenado e libera handles. A pasta temporária precisa ser removível.
$RootTemp = Join-Path $Root "temp"
if (Test-Path $RootTemp) {
    Get-ChildItem $RootTemp -Force | Remove-Item -Recurse -Force
    if (Get-ChildItem $RootTemp -Force | Select-Object -First 1) { throw "Temporários residuais bloqueados após smoke." }
}
$orphans = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in @("ffmpeg", "ffprobe") -and $_.Path -like "$Root*" }
if ($orphans) { throw "Processo FFmpeg/FFprobe órfão após a operação portable." }

# Reabertura normal usando os bancos/configurações já criados.
$reopen = New-PortableProcess $false
if (-not $reopen) { throw "Não foi possível reabrir o portable." }
try {
    Start-Sleep -Seconds 5
    if ($reopen.HasExited) { throw "Portable falhou na reabertura (exit=$($reopen.ExitCode))." }
    Write-Host "PORTABLE_REOPEN_OK pid=$($reopen.Id)"
}
finally {
    if ($reopen -and -not $reopen.HasExited) {
        $reopen.Kill($true)
        $reopen.WaitForExit(10000) | Out-Null
    }
}

Write-Host "PORTABLE_RUNTIME_SMOKE_OK player=$($smokePayload.player_position_ms)ms seek=$($smokePayload.seek_position_ms)ms codec=$($smokePayload.video_codec) audio=$($smokePayload.audio_codec) resolution=$($smokePayload.resolution)"
Write-Host "PORTABLE_ZIP_VALIDATION_OK sha256=$actual"
