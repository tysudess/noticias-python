# Central V95 — Gravador de Tela: sincronismo A/V

Base conferida antes da alteração:

`34061b85fadb59692088d101132d7f11ad9c42d3`

## Problema encontrado

O Gravador de Tela capturava vídeo e áudio em processos/relógios diferentes.

Na finalização de cada segmento, a sequência antiga era:

1. pedir ao FFmpeg de vídeo para encerrar;
2. esperar o processo de vídeo terminar;
3. somente depois parar o áudio;
4. medir o WAV, que portanto continha uma sobra no final;
5. acelerar/comprimir a faixa inteira com `atempo` para fazê-la caber no vídeo.

Essa estratégia transforma uma sobra de encerramento em drift progressivo:
quanto maior a gravação, mais perceptível pode ficar o desencontro.

Pausar/retomar ou mudar a área cria vários segmentos e ainda podia somar
timestamps/priming AAC na concatenação.

## Correções V95

### 1. Encerramento praticamente simultâneo

Ao pausar, parar ou mudar a área:

- o capturador de áudio recebe imediatamente uma solicitação de parada;
- logo em seguida o FFmpeg de vídeo recebe `q`;
- só depois os dois são aguardados/finalizados.

No Linux, o capturador PulseAudio recebe `q` sem bloquear antes de o vídeo
receber seu próprio comando de encerramento.

### 2. Sem compressão artificial para compensar sobra

O áudio não é mais acelerado porque o WAV ficou maior que o vídeo.

O alinhamento usa:

- diferença real de início áudio/vídeo;
- corte somente do trecho que começou antes do vídeo;
- silêncio somente quando o áudio começou depois;
- padding de silêncio no final quando necessário;
- corte final exatamente na duração do vídeo.

### 3. Correção de clock limitada

Para gravações suficientemente longas, a V95 compara:

`duração das amostras WAV / duração real do capturador`

Somente diferenças plausíveis de clock recebem correção e o ajuste aplicado
fica limitado a ±0,5%.

Medições curtas ou anômalas não recebem `atempo`.

### 4. Primeiro buffer WASAPI

O callback chega depois que o primeiro bloco de 1024 amostras já corresponde a
áudio capturado. Quando esse callback realmente já existe, a V95 considera o
início do primeiro sample, reduzindo um deslocamento inicial de aproximadamente
21 ms em 48 kHz.

### 5. Pausa/retomada e mudança de área

Com áudio habilitado, a concatenação de vários segmentos não copia mais
diretamente cada AAC.

O vídeo H.264 continua podendo ser copiado sem perda, mas o áudio é decodificado
e codificado uma única vez na concatenação final, evitando acumular atraso de
encoder/timestamps a cada segmento.

### 6. Verificação final com ffprobe

A V95 mede as durações das trilhas de vídeo e áudio do MP4 final.

O log registra linhas como:

`[A/V SYNC V95] FINAL video=60.033333s audio=60.032000s delta=-0.001333s`

Se a diferença final ultrapassar 180 ms, a Central executa uma normalização
final de duração do áudio sem alterar a velocidade do conteúdo.

### 7. Windows e Ubuntu

O patch resolve automaticamente:

- `bin/ffmpeg.exe` / `bin/ffprobe.exe` no Windows;
- `bin/ffmpeg` / `bin/ffprobe` no Ubuntu.

## Arquivos

SUBSTITUIR:
- `src/monitor_noticias/ui/screen_recorder_integration.py`

ADICIONAR:
- `src/monitor_noticias/ui/screen_recorder_sync_patch.py`
- `tests/unit/test_v95_screen_recorder_sync.py`
- `README_V95_GRAVADOR_SINCRONISMO_AV.md`

## Workflow

**WORKFLOW: NÃO PRECISA ALTERAR**
