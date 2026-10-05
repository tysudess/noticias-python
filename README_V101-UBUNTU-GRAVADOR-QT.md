# Central V101 — Gravador de Tela Ubuntu: backend Qt/X11 + FFmpeg

Base obrigatória usada: `main` em `a2a2e1e01f0f5a0176d69112c877d55cc2cb24ed`.

## Problema confirmado

Na V98 o botão **LIGAR** executava um teste real do `x11grab` antes de habilitar o gravador. No computador Ubuntu real esse subprocesso permanecia bloqueado ao acessar o `DISPLAY` e o teste era encerrado após 6 segundos. Como essa validação ocorria antes do REC, a gravação nunca chegava a iniciar.

Apenas remover o teste não seria suficiente: o mesmo `x11grab` poderia permanecer vivo sem entregar frames quando o REC fosse pressionado.

## Mudança de backend V101

No Ubuntu/Xorg o FFmpeg deixa de abrir o `DISPLAY`.

Fluxo novo:

1. a Central já possui acesso válido ao monitor através de `QScreen`/Qt;
2. o Qt captura os frames da tela ou da área selecionada;
3. os frames são convertidos para BGRA;
4. um writer dedicado mantém a cadência escolhida e envia os frames por um descritor `pipe:N` separado;
5. FFmpeg recebe `rawvideo` e faz apenas a codificação H.264/libx264;
6. o `stdin` do FFmpeg permanece reservado ao fluxo existente de finalização;
7. antes de Pausar/STOP, o pipe de frames é fechado, entregando EOF ao FFmpeg e evitando bloqueio durante `wait()`.

O áudio Linux continua usando PulseAudio/PipeWire-Pulse. Se o áudio falhar, a gravação de vídeo continua sem áudio, como já previsto na V98.

## Alterações específicas

- removido o pré-teste bloqueante de `x11grab`;
- `LIGAR` verifica somente FFmpeg/libx264 e não acessa o `DISPLAY` pelo FFmpeg;
- REC valida a captura pelo próprio Qt no primeiro frame;
- tela inteira e área personalizada usam as coordenadas do monitor escolhido;
- cursor pode ser desenhado no frame Qt quando a opção estiver marcada;
- writer de vídeo roda em thread própria e mantém o relógio de frames mesmo se a GUI tiver pequenas oscilações;
- captura visual é atualizada no máximo a 30 fps; se 60 fps estiver selecionado, o writer mantém 60 fps repetindo o frame mais recente quando necessário;
- pausa, troca de área e STOP fecham o pipe antes da finalização V95;
- diagnóstico Linux passa a registrar `capture_backend=qt-screen-rawvideo-pipe`;
- `TESTAR-PORTABLE.sh` deixa de tratar `x11grab` como requisito e valida `libx264`.

## Wayland

A V101 ainda não declara captura completa de desktop Wayland. Em Wayland, captura total de outras janelas exige o portal ScreenCast/PipeWire com autorização do usuário. Esta correção é voltada ao Ubuntu/Xorg, que é o caminho em que o erro `x11grab excedeu 6 s ao acessar o DISPLAY` foi observado.

## Windows

O backend Windows continua usando o fluxo existente. As alterações V101 são condicionadas ao Linux.

## Workflow

O arquivo `.github/workflows/build-ubuntu.yml` não precisa ser alterado. O workflow já inclui todos os arquivos modificados pelos seus gatilhos e já empacota `TESTAR-PORTABLE.sh`.

**WORKFLOW: NÃO PRECISA ALTERAR.**
