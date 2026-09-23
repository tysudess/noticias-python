# V51 — Gravador de Tela Ubuntu X11 + PipeWire/PulseAudio

## Ordem

V48 -> V49 -> V50 -> V51

## Windows

Nenhuma alteração funcional.

Continua usando:
- gdigrab
- WASAPI
- PyAudioWPatch

## Ubuntu X11

Gravação real ativada com:
- FFmpeg x11grab
- tela inteira
- área personalizada
- 30/60 FPS
- mouse
- CRF
- pausa/retomada por segmentos
- finalização MP4

## Áudio Ubuntu

A V51 procura fontes pelo `pactl`.

Suporta:
- áudio do sistema pela fonte `.monitor`;
- microfone pela source padrão;
- PipeWire quando o desktop fornece compatibilidade PipeWire-Pulse.

O áudio é gravado em WAV por um processo FFmpeg separado e depois usa o
mesmo fluxo de sincronização/mux já existente no Gravador.

Sem `pactl`, o vídeo continua disponível sem áudio.

## Wayland

É detectado automaticamente e não recebe `x11grab`.

A captura Wayland precisa do fluxo oficial xdg-desktop-portal ScreenCast:
CreateSession -> SelectSources -> Start -> OpenPipeWireRemote.

Isso será conectado na V52.

## NOVOS

- src/monitor_noticias/ui/screen_recorder_linux.py
- src/monitor_noticias/ui/screen_recorder_linux_patch.py
- tests/unit/test_screen_recorder_linux_audio.py
- tests/unit/test_screen_recorder_linux_x11.py

## SUBSTITUIR

- src/monitor_noticias/app/application.py

## WORKFLOW

NÃO PRECISA ALTERAR WORKFLOW nesta V51.
