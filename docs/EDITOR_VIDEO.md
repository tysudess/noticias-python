# Editor de Vídeo — Passo 12

## Fonte da verdade

- Repositório original: `tysudess/noticias-monitor`
- Baseline: Build SHA `df1701ba5427a04954093e8ebed63f26abb2b2b7` + workflow `.github/workflows/release-v8-extractor-tab-portable.yml`
- Destino: `tysudess/MONITOR-DE-NOTICAS-PYTHON`
- Branch: `migration/python-foundation`

Quando um comportamento não é comprovado: **NÃO DETERMINADO PELO CÓDIGO ANALISADO**.

## Descoberta principal

O Editor de Vídeo efetivamente distribuído na release analisada **não é o motor Kotlin `VideoEditorEngine.kt`**. A cadeia ativa é:

`DashboardV5Main` → aba `VIDEO_EDITOR` (inserida por `tools/integrate-video-editor-tab.py`) → `VideoEditorScreen.kt` → `PySideVideoEditorLauncher` → `video-editor/VideoEditorPySide/VideoEditorPySide.exe`.

O workflow compila esse executável a partir de `video_editor_pyside/main.py` com PyInstaller e `PySide6==6.9.1`. O script de integração valida explicitamente `QMediaPlayer`, `QVideoWidget` e `QAudioOutput`.

### Classificação

| Arquivo/implementação | Classe | Status na release V8 | Evidência |
|---|---|---|---|
| `video_editor_pyside/main.py` | `MainWindow`, `TimelineWidget`, `Clip`, `VideoInfo` | **ATIVO** | PyInstaller no workflow e cópia para o portable |
| `VideoEditorScreen.kt` | `VideoEditorScreen`, `PySideVideoEditorLauncher` | **ATIVO — LAUNCHER** | abre `VideoEditorPySide.exe` |
| `VideoEditorEngine.kt` | `VideoEditorEngine` | **LEGADO/ALTERNATIVO** | não é chamado pelo launcher final; contém pipeline mais rico não empacotado como motor ativo |
| `VideoEditorPreview.kt` | `VideoEditorPreviewController` | **LEGADO/ALTERNATIVO** | preview por JPEG/FFmpeg pertence ao motor Kotlin alternativo |
| `VideoEditorProcess.kt` | utilitário de processo | **LEGADO/ALTERNATIVO** | suporte do motor Kotlin alternativo |

Não misturar funcionalidades dessas implementações.

## Motor de preview original

- **MOTOR:** Qt Multimedia
- **BIBLIOTECA:** `PySide6.QtMultimedia.QMediaPlayer`
- **VERSÃO:** PySide6 `6.9.1`
- **BACKEND DE PLATAFORMA:** **NÃO DETERMINADO PELO CÓDIGO ANALISADO**; o source não fixa backend interno do Qt Multimedia.
- **ARQUIVO:** `video_editor_pyside/main.py`
- **CLASSE:** `MainWindow`
- **INICIALIZAÇÃO:** `QMediaPlayer(self)` + `QAudioOutput(self)` + `QVideoWidget(self)`
- **ARQUIVO:** `player.setSource(QUrl.fromLocalFile(...))`
- **FRAME:** `player.setVideoOutput(video_widget)`
- **ÁUDIO:** `player.setAudioOutput(audio)`; volume inicial `0.85`; mute booleano.
- **SEEK:** `player.setPosition(local_ms)`.
- **POSIÇÃO:** signal `positionChanged`.
- **DURAÇÃO:** o editor não usa a duração reportada pelo player como fonte do projeto; usa FFprobe/`VideoInfo.duration_ms`.

### Motor Python

O Passo 12 mantém exatamente **QMediaPlayer + QVideoWidget + QAudioOutput**. Não houve troca de motor.

## FFprobe

Comando ativo:

```text
ffprobe.exe -v error -print_format json -show_format -show_streams <arquivo>
```

Timeout: 60 s.

Campos utilizados:

- duração do `format.duration` e, se maior, `stream.duration` do primeiro vídeo;
- largura/altura;
- FPS por `avg_frame_rate`, com fallback `r_frame_rate`;
- codec do primeiro stream de vídeo;
- codec do primeiro stream de áudio.

Bitrate e metadata geral não são usados no modelo ativo.

## Formatos aceitos

Exatamente:

- `.mp4`
- `.mkv`
- `.webm`
- `.mov`
- `.avi`
- `.m4v`

Imagens e áudios possuem abas visuais desabilitadas; não são mídias importáveis pelo motor ativo.

## Modelo

### `VideoInfo`

- `duration_ms`
- `width`
- `height`
- `fps`
- `video_codec`
- `audio_codec`
- propriedade `has_audio`

### `Clip`

- `path`
- `info`
- `start_ms`, default `0`
- `end_ms`, default `info.duration_ms`
- `duration_ms = max(0, end_ms - start_ms)`

Não existem no modelo ativo ID, thumbnail, track, efeitos, projeto persistido ou estado de undo.

## Tempo e timeline

Unidade central: **milissegundos inteiros**.

- tempo local do arquivo: posição do `QMediaPlayer`;
- trecho local: `start_ms..end_ms`;
- duração do clipe: `end_ms - start_ms`;
- tempo global: soma das durações dos clipes anteriores + posição local relativa ao `start_ms`.

Conversão global → clipe/local preserva uma particularidade do source: usa `global_ms <= next_cursor`; portanto o limite exato entre dois clipes ainda é mapeado ao final do clipe anterior.

A timeline desenha uma track de vídeo e uma de áudio. Não possui thumbnails. A régua usa 5 intervalos, ou 6 quando a duração total passa de 60 s. O clique calcula tempo proporcional pela largura disponível. O playhead acompanha `positionChanged` e seeks.

`pixels_per_second = 8.0` existe no source, mas o widget ativo não implementa zoom funcional a partir desse valor. Não inventar zoom.

## Reprodução

Controles ativos:

- voltar 5 s;
- play/pause;
- avançar 5 s;
- mute/unmute.

Não existe botão Stop separado.

Durante play, ao chegar a `clip.end_ms`, o editor carrega o próximo clipe com autoplay. No último clipe, pausa e posiciona o global no fim da sequência. Não há transição, crossfade ou preload explicitamente implementado.

Gap/latência real entre fontes depende de `QMediaPlayer.setSource()` e **NÃO DETERMINADO PELO CÓDIGO ANALISADO** como duração garantida.

## Funcionalidades NÃO existentes no motor ativo

Apesar de nomes visuais no layout ou da implementação Kotlin alternativa, o `main.py` ativo não implementa:

- split/divisão;
- exclusão de clipe;
- duplicação;
- reordenação;
- drag-and-drop de clipes;
- thumbnails;
- zoom da timeline;
- IN/OUT manual;
- range slider;
- ajuste fino de IN/OUT;
- undo/redo;
- arquivo de projeto;
- reset/limpar timeline;
- compactação;
- tamanho-alvo;
- estimativa de tamanho;
- seleção de codec;
- seleção de resolução;
- seleção de FPS;
- H.265;
- concatenação por FFmpeg;
- exportação da sequência inteira;
- progresso FFmpeg;
- cancelamento de exportação;
- temporários de exportação.

`Salvar Projeto`, `Configurações`, `Extração`, `Compactação`, `Corte`, `Unir Vídeos`, `Converter`, além dos quick buttons equivalentes, são placeholders. `Cortar Vídeo` e `Exportar trecho` chamam a única exportação real.

## Exportação ativa

A exportação opera **somente sobre o clipe selecionado**. Como a UI ativa não fornece edição de `start_ms/end_ms`, um clipe importado normalmente representa o arquivo inteiro.

Pasta: `VideoEditorExports/`.

Nome:

```text
<stem>_corte_<IN-formatado>_<OUT-formatado>.mp4
```

Formato de tempo no nome troca `:` e `.` por `-`.

Comando:

```text
ffmpeg.exe -y -i <input>
  -ss <start segundos, 3 casas>
  -t <duration segundos, 3 casas>
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

`-ss` e `-t` aparecem **depois** de `-i`, como no source aprovado. Timeout: 3600 s. A chamada ativa é síncrona (`subprocess.run`), sem `-progress`; portanto o Passo 12 não inventa barra de progresso nem cancelamento.

Não há lógica de H.265, bitrate variável por resolução, target MB, pad/crop para aspect ratios mistos, silence synthesis ou concatenação.

## FFmpeg / FFprobe do portable

A release usa os mesmos `bin/ffmpeg.exe` e `bin/ffprobe.exe` montados pelo workflow do Monitor. O workflow tenta primeiro BtbN `ffmpeg-n9.0-latest-win64-gpl-9.0.zip` e depois Gyan `ffmpeg-release-essentials.zip`.

Qual das duas fontes foi usada no ZIP aprovado, e o build/version string concreto do binário final: **NÃO DETERMINADO PELO CÓDIGO ANALISADO** sem o artefato/log correspondente.

## Integração no Monitor Python

O placeholder de `Section.VIDEO_EDITOR` foi substituído por `VideoEditorPage`. O workspace reproduz o launcher e abre `VideoEditorWindow` como janela top-level PySide6.

Diferença arquitetural conhecida: a release Kotlin inicia um EXE PyInstaller em **processo separado**. No Passo 12, antes do portable final, a janela está no mesmo processo Python para permitir integração/teste sem fabricar prematuramente um segundo executável. O motor de preview e a lógica do editor permanecem os mesmos. Essa diferença mantém `MIG-068`/workspace em teste até o passo de empacotamento e validação interativa.

## Testes automatizados

Foram adicionados testes para:

- formatos exatos;
- formatação temporal e FPS;
- modelo `VideoInfo/Clip`;
- duração global;
- global → clipe/local e regra de fronteira;
- comando FFprobe/parsing;
- comportamento quando FFprobe está ausente;
- comando FFmpeg literal;
- nome do arquivo de saída;
- matemática proporcional da timeline;
- QMediaPlayer/QVideoWidget/QAudioOutput + volume 0.85;
- controles ativos;
- proteção contra introdução silenciosa de split/delete/duplicate/reorder/undo/zoom/target-size/thumbnails.

A matriz de regressão carrega QtMultimedia em Windows e Ubuntu; Ubuntu requer `libpulse0` no runner.

## Validação real pendente

Sem os binários finais `bin/ffmpeg.exe`/`bin/ffprobe.exe` da release e sem sessão desktop humana interativa neste passo, não é correto afirmar aprovação de:

- decode/play real de todos os formatos;
- precisão medida de seek;
- áudio/mute real;
- troca de fonte durante reprodução;
- exportação FFmpeg real;
- abertura e FFprobe do arquivo exportado.

Esses itens permanecem `EM TESTE`, não são mascarados por mocks ou Qt offscreen.
