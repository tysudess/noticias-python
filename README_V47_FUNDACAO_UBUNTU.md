# V47 — Fundação Multiplataforma Windows + Ubuntu

## Objetivo

Primeira etapa de código da portabilidade para Ubuntu no mesmo repositório.

Esta versão ainda NÃO cria o AppImage.

Ela prepara a camada de plataforma sem alterar o comportamento funcional
da versão Windows.

## Nova estrutura

`src/monitor_noticias/platform/`

- `current.py`
  - detecta Windows/Linux;
  - detecta AppImage;
  - detecta X11/Wayland.

- `binaries.py`
  - Windows: `ffmpeg.exe`;
  - Linux: `ffmpeg`.

- `processes.py`
  - Windows continua com CREATE_NO_WINDOW/taskkill;
  - Linux usa grupo de processos POSIX.

- `startup.py`
  - Windows continua usando HKCU Run;
  - Ubuntu usa `~/.config/autostart/*.desktop`;
  - AppImage aponta para o arquivo AppImage original.

- `desktop.py`
  - Windows: `os.startfile`;
  - Linux: `xdg-open`.

## AppImage e dados

Dentro de um AppImage o bundle é somente leitura.

Por isso `AppPaths` separa:

### `root`
Recursos e binários do aplicativo.

### `state_root`
Dados graváveis.

Windows Portable e desenvolvimento:
`state_root == root`

AppImage:
tenta usar ao lado do AppImage:

`Central-Inteligente-de-Midia-Data/`

Se a pasta não for gravável:

`~/.local/share/CentralInteligenteDeMidia/`

## Compatibilidade Windows

Os imports antigos:

- `monitor_noticias.windows.processes`
- `monitor_noticias.windows.startup`

continuam existindo como fachadas de compatibilidade.

Isso reduz risco de regressão na versão Windows.

## Arquivos novos

- `src/monitor_noticias/platform/__init__.py`
- `src/monitor_noticias/platform/current.py`
- `src/monitor_noticias/platform/binaries.py`
- `src/monitor_noticias/platform/processes.py`
- `src/monitor_noticias/platform/startup.py`
- `src/monitor_noticias/platform/desktop.py`
- `tests/unit/test_platform_foundation.py`

## Arquivos a substituir

- `src/monitor_noticias/app/paths.py`
- `src/monitor_noticias/windows/processes.py`
- `src/monitor_noticias/windows/startup.py`
- `tests/unit/test_paths.py`

## Não alterados nesta etapa

- Proxy/DPAPI
- Gravador de Tela
- Extrator de Notícias Electron
- Extrator de Vídeos
- Editor de Vídeo
- Capas
- workflow Windows
- workflow Ubuntu

## Workflow

NÃO PRECISA ALTERAR WORKFLOW nesta V47.

O `build-portable.yml` do Windows continua sendo o workflow atual.

O `build-ubuntu.yml` será criado quando a aplicação já estiver preparada
para iniciar no runner Ubuntu.
