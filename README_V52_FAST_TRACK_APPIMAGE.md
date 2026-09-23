# V52 FAST TRACK — Primeiro AppImage Ubuntu

Objetivo: parar de fragmentar a portabilidade em micro-etapas e já gerar
o primeiro AppImage real pelo GitHub Actions.

## Resultado esperado

Release com:

- Central-Inteligente-de-Midia-Ubuntu-x86_64.AppImage
- Central-Inteligente-de-Midia-Ubuntu-x86_64.AppImage.sha256

## Incluído no build

- Central PySide6/PyInstaller Linux
- Qt WebEngine
- Proxy seguro Linux
- FFmpeg/FFprobe estáticos
- yt-dlp_linux standalone
- Deno Linux
- Helper Globoplay Linux
- Extrator de Matérias Electron Linux
- Editor de Vídeo
- PDF
- Capas
- Gravador de Tela X11
- áudio PulseAudio/PipeWire-Pulse
- dados graváveis fora do AppImage

## Extrator de Matérias

Electron é gerado com:

npm run dist:linux

O diretório `linux-unpacked` inteiro é incluído no AppImage.

Um launcher compatível com a página PySide6 é criado em:

tools/news_extractor/ExtratorMateriasPortable-V1.25.19

Portanto não tentamos empacotar um AppImage Electron dentro de outro AppImage.

## yt-dlp

A V52 corrige também o updater Linux.

Antes:
releases/latest/download/yt-dlp

Agora:
releases/latest/download/yt-dlp_linux

Isso garante executável Linux standalone e evita depender do Python do
sistema do usuário.

## Wayland

Não bloqueia mais o primeiro release Ubuntu.

- X11: Gravador funcional.
- Wayland: Central funciona normalmente; apenas a captura de tela permanece
  protegida/desativada até a integração xdg-desktop-portal.

A compatibilidade Wayland pode ser finalizada depois do primeiro AppImage.

## Arquivos NOVOS

- .github/workflows/build-ubuntu.yml
- MonitorDeNoticias-Linux.spec
- scripts/pyi_runtime_linux_validation.py
- scripts/validate_linux_bundle.py
- portable/linux/AppRun
- portable/linux/central-inteligente-de-midia.desktop

## Arquivos SUBSTITUIR

- tools/news_extractor/package.json
- src/monitor_noticias/ui/cross_platform_runtime_patch.py

## WORKFLOW

SIM — nesta V52 existe novo workflow:

.github/workflows/build-ubuntu.yml

O workflow Windows atual NÃO é substituído.

## Como usar

Suba todos os arquivos desta V52 na mesma estrutura do repositório.

Ao entrar na main, o workflow:

Build e Release Ubuntu AppImage

deve iniciar automaticamente porque os paths do próprio workflow e arquivos
Ubuntu fazem parte do gatilho.

Também pode ser iniciado manualmente em:

Actions -> Build e Release Ubuntu AppImage -> Run workflow

## Meta desta etapa

Não parar em artifact.

O job final cria uma Release com o AppImage e SHA256.
