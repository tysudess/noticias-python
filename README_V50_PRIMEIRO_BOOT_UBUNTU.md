# V50 — Primeiro boot Ubuntu: helper, páginas reais e identidade

## Dependência

Aplicar na ordem:

V48 -> V49 -> V50

A V50 contém somente arquivos novos/substituídos desta etapa.

## Correções importantes encontradas

A MainWindow usa `ReferenceVideoEditorPage`, não a página base modificada
na V49.

Por isso a V50 corrige a página REAL usada pelo programa.

Também o Gravador de Tela é criado logo na inicialização. Ele ainda tentava
criar `Videos/`, `temp/` e `logs/` dentro do AppImage, o que poderia impedir
o primeiro boot por o bundle ser somente leitura.

## Globoplay

`resolve_bundled_helper()` agora é multiplataforma.

Windows:
- resources/globoplay-login-helper/GloboplayLoginHelper.exe

Ubuntu:
- resources/globoplay-login-helper/GloboplayLoginHelper

O helper é sempre materializado na área gravável antes de executar.

No Ubuntu recebe permissão de execução automaticamente.

`tools/build-globoplay-login-helper.py` agora também gera o helper no Linux.

## Editor de Vídeo real

`ReferenceVideoEditorPage` no Ubuntu passa a usar:

- `Central-Inteligente-de-Midia-Data/Videos`
- `ffmpeg`
- `ffprobe`

via AppPaths/runtime_binary.

Windows permanece no comportamento anterior.

## Editor PDF

O editor PDF ainda pressupõe que recursos e `data/` ficam sob a mesma raiz.

No Linux, a V50 copia apenas os pequenos assets de capa necessários para
a raiz gravável e inicia o modelo PDF nessa área.

Isso evita escrever dentro do AppImage.

## Gravador de Tela

A página agora pode ser criada sem gravar no AppImage.

Diretórios no Linux:
- Videos/GravacoesTela
- temp/screen_recorder
- logs/

ficam na área gravável.

O FFmpeg também é resolvido pelo nome Linux.

IMPORTANTE:
o motor atual ainda é `gdigrab + WASAPI`, portanto não ativamos gravação
real no Linux nesta versão.

Ao tentar ligar o Gravador no Ubuntu, a interface explica que o backend
X11/PipeWire/Wayland será ligado na próxima etapa.

Isso evita executar comandos Windows inválidos no Linux.

## Identidade visual

Windows continua mostrando:
`Windows Portable v4.0.2`

Linux em desenvolvimento:
`Ubuntu/Linux v4.0.2`

AppImage:
`Ubuntu AppImage v4.0.2`

A opção de configurações passa a mostrar:
`Iniciar com o sistema`

no Linux.

## Capas

O cache/configuração do módulo Capas passa a usar a área de dados gravável
do Central no Linux:

`data/capas/`

Downloads continuam em:
`~/Downloads/Principais Capas`

## Arquivos NOVOS

- src/monitor_noticias/ui/linux_boot_patch.py
- tests/unit/test_globoplay_helper_platform.py
- tests/unit/test_platform_identity.py

## Arquivos SUBSTITUIR

- src/monitor_noticias/extractor/login_helper.py
- tools/build-globoplay-login-helper.py
- src/monitor_noticias/app/application.py

## Workflow

NÃO PRECISA ALTERAR WORKFLOW ainda.

O novo `build-ubuntu.yml` será criado depois que o backend Linux do Gravador
e o runtime Linux do Extrator de Matérias estiverem prontos.

## Próxima etapa

V51:
- Gravador de Tela Linux;
- X11 via x11grab;
- Wayland/PipeWire;
- áudio do sistema/microfone Linux;
- manter gdigrab/WASAPI intactos no Windows.
