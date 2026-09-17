# Arquitetura da migração Python

## Fonte da verdade

A migração usa `tysudess/noticias-monitor`, Build SHA `df1701ba5427a04954093e8ebed63f26abb2b2b7`, **mais as transformações executadas por** `.github/workflows/release-v8-extractor-tab-portable.yml`. O destino é `tysudess/MONITOR-DE-NOTICAS-PYTHON`, branch `migration/python-foundation`.

A regra permanente é preservar o motor e o comportamento comprovados. Quando algo não é comprovado: **NÃO DETERMINADO PELO CÓDIGO ANALISADO**.

## Arquitetura atual após o Passo 12

```text
Application
└─ MainWindow (PySide6 QMainWindow)
   ├─ páginas do Monitor migradas no Passo 9
   ├─ Editor de PDF [PdfEditorPage REAL]
   ├─ Extrator de Vídeos [ExtractorPage REAL]
   └─ Editor de Vídeo [VideoEditorPage REAL]
      └─ VideoEditorWindow (janela Qt top-level)
         ├─ QMediaPlayer
         ├─ QVideoWidget
         ├─ QAudioOutput
         ├─ TimelineWidget
         ├─ FFprobe → VideoInfo
         └─ FFmpeg → exportação do clipe selecionado

PdfEditorPage
└─ PdfEditorModel
   ├─ pypdf
   ├─ pypdfium2/PDFium
   └─ Pillow

ExtractorPage / ExtractorEngine
   ├─ yt-dlp nightly/stable
   ├─ ffmpeg / ffprobe / deno
   ├─ YouTube normal/live
   ├─ Globoplay
   ├─ R7/Record
   └─ fallback HTML
```

## Editor PDF — arquitetura preservada do Passo 11

A implementação efetivamente executada pelo Dashboard V5 é `PdfEditorScreenV2.kt`. `PdfEditorScreen.kt` é implementação anterior. O workflow aplica `patch-pdf-editor-naval-layout.py` e `patch-pdf-editor-naval-layout-refine.py` sobre o V2.

O motor original usa Apache PDFBox `3.0.3` (`Loader`, `PDFRenderer`, `PDDocument`, `PDPage`, `LayerUtility`, `PDPageContentStream`, `Matrix`, `LosslessFactory`) e ImageIO/TwelveMonkeys. O Python usa:

- `pypdf==6.18.0` para montagem/exportação vetorial;
- `pypdfium2==5.13.0` para renderização de PDF;
- `Pillow==12.3.0` para imagens/crop/raster;
- `PySide6==6.9.1` para UI/workers.

O modelo preserva itens `PDF`, `IMAGE`, `BLANK`, caminho, página, rotação/flip internos, crop normalizado e uid. Importação aceita `.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tiff`, `.tif`. Preview usa 120 dpi; miniaturas 58 dpi e máximo 56×84; zoom 50–300% em passos de 15%; Redimensionar é somente zoom visual 75/90/100/110/125%.

Undo/redo usa snapshots de páginas+seleção, máximo 30. Atalhos ativos: Ctrl+Z, Ctrl+Y, Delete, Ctrl+S. Rotação/flip permanecem suporte interno sem botão ativo comprovado. A capa usa `data/capa_padrao_usuario.png`, `data/capa_padrao.png`, `resources/pdf-default-cover.b64` e fallback. Exportação cria novo documento, largura 595.276 pt, caminho vetorial para PDF sem transformação e raster para imagem/blank/página transformada.

## Editor de Vídeo — fonte ativa

A revisão do Passo 12 comprovou que o editor efetivamente distribuído pela release V8 **já é Python/PySide6**. A cadeia de execução final é:

```text
DashboardV5Main
  → VIDEO_EDITOR (inserido por integrate-video-editor-tab.py)
  → VideoEditorScreen.kt
  → PySideVideoEditorLauncher
  → video-editor/VideoEditorPySide/VideoEditorPySide.exe
  → source: video_editor_pyside/main.py
```

O workflow executa:

```text
python -m PyInstaller --noconfirm --clean --windowed --onedir
  --name VideoEditorPySide
  --collect-all PySide6
  video_editor_pyside/main.py
```

e copia a pasta resultante para `video-editor/VideoEditorPySide` no portable.

### Ativo x legado/alternativo

| Componente | Classificação | Motivo |
|---|---|---|
| `video_editor_pyside/main.py` | ATIVO | source do EXE empacotado e aberto pelo launcher |
| `VideoEditorScreen.kt` | ATIVO — LAUNCHER | cria workspace e abre o EXE PySide6 |
| `VideoEditorEngine.kt` | LEGADO/ALTERNATIVO | motor Kotlin mais rico, não chamado pelo launcher final |
| `VideoEditorPreview.kt` | LEGADO/ALTERNATIVO | preview por frames JPEG do motor Kotlin alternativo |
| `VideoEditorProcess.kt` | LEGADO/ALTERNATIVO | helper do motor Kotlin alternativo |

Não é permitido combinar funcionalidades dos dois motores para “completar” o editor ativo.

## Motor de preview do Editor de Vídeo

Motor original e motor Python do Passo 12 são o mesmo:

- PySide6 `6.9.1`;
- `PySide6.QtMultimedia.QMediaPlayer`;
- `QVideoWidget` como saída de vídeo;
- `QAudioOutput` como saída de áudio;
- volume inicial `0.85`;
- source via `QUrl.fromLocalFile`;
- seek via `QMediaPlayer.setPosition(ms)`;
- posição via `positionChanged`;
- fim de mídia via `mediaStatusChanged`;
- erro via `errorOccurred`.

Backend nativo interno escolhido pelo QtMultimedia no Windows: **NÃO DETERMINADO PELO CÓDIGO ANALISADO**.

O FFmpeg **não é o player** do editor ativo. FFmpeg é usado somente na exportação; FFprobe analisa a mídia.

## Formatos e análise da mídia

Formatos aceitos exatamente:

- `.mp4`
- `.mkv`
- `.webm`
- `.mov`
- `.avi`
- `.m4v`

O probe usa:

```text
ffprobe.exe -v error -print_format json -show_format -show_streams <arquivo>
```

Timeout: 60 s. O modelo `VideoInfo` recebe duração em ms, largura, altura, FPS, codec de vídeo e primeiro codec de áudio. FPS usa `avg_frame_rate`, fallback `r_frame_rate`. Bitrate e metadata geral não fazem parte do modelo ativo.

## Modelo temporal

`Clip` contém somente:

- `path`;
- `info`;
- `start_ms`, default 0;
- `end_ms`, default `info.duration_ms`;
- propriedade `duration_ms = max(0, end_ms - start_ms)`.

Unidade central: **milissegundos inteiros**.

Conversões:

```text
início global do clipe i = soma(duration_ms dos clipes anteriores)
posição global = início global + max(0, player.position - clip.start_ms)
global → clip/local = percorre durações acumuladas
```

A implementação ativa usa `global_ms <= next_cursor`; por isso o tempo exatamente no limite entre dois clipes ainda mapeia para o final do clipe anterior. Esse detalhe foi preservado e testado.

## Timeline

`TimelineWidget` possui:

- uma track visual de vídeo;
- uma track visual de áudio;
- blocos proporcionais à duração dos clipes;
- seleção de clipe por clique;
- playhead global;
- régua com 5 intervalos, ou 6 quando duração total > 60 s;
- clique → tempo global proporcional → seek.

Não possui thumbnails. `pixels_per_second = 8.0` existe no source, mas o widget ativo não usa esse valor para zoom funcional. Não existe scroll/zoom operacional comprovado. O playhead não tem lógica própria de drag; mouse press faz seek pelo x.

## Reprodução e áudio

Controles ativos:

- `◀ 5s`;
- play/pause no mesmo botão;
- `5s ▶`;
- mute/unmute.

Não existe botão Stop separado.

Ao atingir `clip.end_ms` durante reprodução, `play_next_clip()` carrega o próximo source com autoplay. `EndOfMedia` também chama o próximo clipe. Ao terminar o último, o player pausa e o playhead vai para a duração global total.

Não há transição, crossfade ou preload explícitos. Gap real durante `setSource()` depende do backend do QtMultimedia e é **NÃO DETERMINADO PELO CÓDIGO ANALISADO**.

Mídia sem áudio é aceita: `audio_codec=None`, timeline mostra `Sem áudio`; o player simplesmente não recebe stream de áudio.

## Recursos deliberadamente ausentes

O editor ativo não implementa:

- thumbnails;
- zoom funcional da timeline;
- split/divisão;
- exclusão de clipe;
- duplicação;
- reordenação;
- drag-and-drop de clipes;
- IN/OUT manual;
- range slider;
- ajuste fino temporal;
- undo/redo;
- arquivo de projeto;
- reset/limpar timeline;
- compactação;
- tamanho-alvo;
- estimativa de tamanho;
- seleção de codec/resolução/FPS;
- H.265;
- concatenação;
- progresso de exportação;
- cancelamento de exportação;
- temporários de exportação.

Há botões/abas visuais para `Salvar Projeto`, `Configurações`, `Extração`, `Compactação`, `Corte`, `Unir Vídeos`, `Converter`, mas o source responde explicitamente que essas funções não existem. Nos quick buttons, somente `Cortar Vídeo` chama a exportação real; os demais continuam placeholders.

## Exportação do Editor de Vídeo

A exportação ativa opera somente sobre o clipe selecionado. Como a UI ativa não modifica `start_ms/end_ms`, um clipe recém-importado normalmente representa o arquivo inteiro.

Pasta: `VideoEditorExports/`.

Nome:

```text
<stem>_corte_<IN>_<OUT>.mp4
```

com o tempo formatado e `:`/`.` substituídos por `-`.

Pipeline literal:

```text
ffmpeg.exe -y -i <input>
  -ss <start_seconds_3_decimals>
  -t <duration_seconds_3_decimals>
  -map 0:v:0
  -map 0:a?
  -vf scale=trunc(iw/2)*2:trunc(ih/2)*2
  -c:v libx264
  -preset veryfast
  -crf 20
  -pix_fmt yuv420p
  -c:a aac
  -b:a 160k
  -movflags +faststart
  <output.mp4>
```

`-ss` e `-t` ficam **depois de `-i`**. Timeout: 3600 s. A execução ativa é síncrona por `subprocess.run`; não usa `-progress`, worker ou cancelamento. Reescrever em background agora seria melhoria divergente, não migração fiel.

Áudio é opcional por `-map 0:a?`. Não existe geração de silêncio. Vídeo sempre sai `libx264`, CRF 20, preset veryfast, `yuv420p`; áudio, quando presente, AAC 160k. Não há target bitrate, target size, H.265 ou seleção de resolução. O filtro apenas garante dimensões pares, preservando a resolução efetiva salvo arredondamento para múltiplos de 2.

## FFmpeg/FFprobe do portable

O workflow baixa FFmpeg/FFprobe no mesmo pacote de binários do Monitor. Tenta primeiro BtbN `ffmpeg-n9.0-latest-win64-gpl-9.0.zip` e depois Gyan `ffmpeg-release-essentials.zip`.

Qual fonte venceu no artefato aprovado e qual versão/build string concreta está no ZIP: **NÃO DETERMINADO PELO CÓDIGO ANALISADO** sem inspeção do artefato/log correspondente.

## Integração Python

O placeholder `Section.VIDEO_EDITOR` foi substituído por `VideoEditorPage`. Assim como o Kotlin `VideoEditorScreen`, ele funciona como workspace/launcher e abre uma janela nativa de editor.

Diferença arquitetural deliberada antes do portable final:

- release Kotlin: launcher cria **processo separado** `VideoEditorPySide.exe`;
- Passo 12 Python: `VideoEditorPage` cria `VideoEditorWindow` como janela top-level **no mesmo processo**.

Isso permite usar exatamente o mesmo código PySide6 sem antecipar PyInstaller/portable. Essa diferença mantém `MIG-068`/`MIG-110` em `EM TESTE` até o passo de empacotamento e validação interativa. O motor de preview não foi trocado.

## Testes do Passo 12

Foram adicionados testes para:

- formatos aceitos;
- `VideoInfo`/`Clip`;
- milissegundos, FPS e formatação de tempo;
- duração total e global↔local, incluindo limite `<=`;
- comando/parsing FFprobe por fixture controlada;
- comando FFmpeg e nome de saída literais;
- matemática pixel↔tempo da timeline;
- existência real de `QMediaPlayer`, `QVideoWidget`, `QAudioOutput` e volume 0,85;
- controles ativos e placeholders;
- proibição automatizada de split/delete/duplicate/reorder/undo/zoom/target-size/thumbnails inventados.

A matriz `Python migration tests` executou `compileall` e toda a regressão em Windows e Ubuntu no run `34726977912`; os dois jobs passaram. O Windows executou **132 testes**.

O runner Ubuntu precisou de `libpulse0` para carregar QtMultimedia; essa dependência foi adicionada ao ambiente de CI, não contornada no código.

## Estado após o Passo 12

O Editor de Vídeo real está conectado à MainWindow e os contratos determinísticos foram protegidos. Permanecem em teste:

- launcher como processo separado no portable final;
- decode/play humano de formatos reais;
- áudio/mute real;
- precisão medida de seek;
- transição entre sources sob reprodução real;
- exportação com os binários exatos da release;
- FFprobe do arquivo realmente exportado.

Não houve sessão manual humana; Qt `offscreen` não é tratado como teste manual. Portable final não foi iniciado.
