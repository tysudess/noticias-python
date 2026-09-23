# V49 — Binários externos e caminhos graváveis no Ubuntu

## Dependência

Aplique a V48 antes desta V49.

A `main` do GitHub já contém a V47, mas no momento da criação desta versão
a V48 ainda não estava na `main`.

## Objetivo

Preparar Extrator de Vídeos, Editor de Vídeo e Extrator de Matérias para
rodarem dentro de um AppImage sem tentar gravar dentro do bundle.

## O que muda

### AppPaths

Novos conceitos:

- `videos`
- `video_editor_exports`
- `user_bin`
- `runtime_binary(name)`
- `writable_binary(name)`
- `AppPaths.for_app_root(...)`

### Binários

Windows continua usando:

- `ffmpeg.exe`
- `ffprobe.exe`
- `yt-dlp.exe`
- `deno.exe`

Linux usa:

- `ffmpeg`
- `ffprobe`
- `yt-dlp`
- `deno`

### Atualização do yt-dlp no AppImage

O AppImage é somente leitura.

Por isso, no Linux:

- a versão incluída no AppImage continua sendo usada normalmente;
- quando o usuário atualiza o yt-dlp, a nova versão é salva em:

`Central-Inteligente-de-Midia-Data/bin/yt-dlp`

- essa versão passa a ter prioridade sobre a embutida no AppImage;
- o arquivo recebe permissão de execução automaticamente.

No Windows nada muda.

### Extrator de Vídeos

No Linux:

- downloads vão para a área gravável `Videos/`;
- histórico/config do Extrator ficam em `data/extractor/`;
- logs ficam em `logs/`;
- FFmpeg/FFprobe/yt-dlp/Deno usam os nomes Linux;
- sessão Globoplay passa a usar o keyring seguro da V48.

### Extrator de Matérias

A página passa a esperar no Linux:

`tools/news_extractor/ExtratorMateriasPortable-V1.25.19`

sem `.exe`.

O workflow Linux irá gerar/copiar esse runtime em etapa posterior.

Resultados temporários passam a usar a área gravável.

### Editor de Vídeo

No Linux:

- pasta `Videos/` fica na área gravável;
- FFmpeg e FFprobe são resolvidos pela camada multiplataforma.

## Arquivos NOVOS

- `src/monitor_noticias/ui/cross_platform_runtime_patch.py`
- `tests/unit/test_runtime_paths_platform.py`

## Arquivos SUBSTITUIR

- `src/monitor_noticias/platform/binaries.py`
- `src/monitor_noticias/app/paths.py`
- `src/monitor_noticias/ui/video_editor_page.py`
- `src/monitor_noticias/app/application.py`

## Não mexemos ainda

- Gravador de Tela X11/Wayland/PipeWire;
- build do helper de login Globoplay para Linux;
- empacotamento Electron Linux do Extrator de Matérias;
- AppImage/workflow Ubuntu.

## Workflow

NÃO PRECISA ALTERAR WORKFLOW nesta V49.

O workflow Windows atual continua separado e intacto.

A criação do `build-ubuntu.yml` virá depois que os módulos restantes
de inicialização estiverem preparados.
