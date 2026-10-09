# V102 — correção do Gravador de Tela Ubuntu

Base conferida: `tysudess/noticias-python`, branch `main`, commit `6123fb9f7416d567254d38e47850c3a36983042e`.

## Causa confirmada pelos logs do Ubuntu

O FFmpeg está encerrando com código 234 nos dois comandos de captura. Tanto o input PulseAudio quanto o input `rawvideo` recebem a opção de fila e o FFmpeg rejeita a inicialização antes de começar a capturar vídeo. A V102 recompõe esses dois comandos sem essa opção. O comando de vídeo continua recebendo frames BGRA do Qt pelo descritor de pipe dedicado; o Windows não usa estes métodos corrigidos.

## Arquivos

**Substituir**
- `src/monitor_noticias/ui/screen_recorder_integration.py`

**Adicionar**
- `src/monitor_noticias/ui/screen_recorder_linux_ffmpeg_fix.py`
- `tests/unit/test_v102_ubuntu_ffmpeg_input_options.py`
- `portable/linux/TESTAR-PORTABLE.sh`

## Validação

A validação unitária V102 protege a ausência da opção rejeitada nos dois comandos e verifica que o patch é instalado antes de criar a página. O script de diagnóstico portable também roda uma codificação sintética de dois frames pelo mesmo input `rawvideo` e valida o MP4 resultante com `ffprobe`.

`WORKFLOW: NÃO PRECISA ALTERAR` — o workflow Ubuntu já executa os testes unitários e `TESTAR-PORTABLE.sh` após extrair o arquivo TAR.GZ.
