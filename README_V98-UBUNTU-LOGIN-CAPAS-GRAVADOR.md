# Central V98 — Correções Ubuntu: Login, Capas e Gravador

Base obrigatória usada nesta correção: `main` em `47afd38d300bc3d3399c2d73c26d006a3aceafb5`.

## 1. Login Ubuntu / Proxy Geral

### Causa encontrada

A V97 executava um GET de *warm-up* antes do POST real de `login`/`validate`. Atrás do proxy corporativo, esse GET podia consumir até 6,5 s antes da autenticação real. Além disso, `ProxySettings._load_password()` fazia `exists()` e depois `load()`. No backend Linux, `exists()` já executa `load()` pelo Secret Service, portanto cada carregamento lia o cofre duas vezes. Como o warm-up relia a configuração, o primeiro login podia acionar várias viagens D-Bus/Secret Service antes do POST real.

### Correção V98

- removido o warm-up GET; a primeira requisição volta a ser o POST real;
- a sessão HTTP reutilizável continua preservada;
- a senha do Proxy Geral é lida uma única vez por `ProxySettings.load()`;
- logs distinguem `connect_timeout`, `read_timeout`, proxy e TLS sem registrar senha/token/payload;
- a autenticação continua obrigatória e nenhuma validação de segurança foi removida;
- a exceção TLS continua limitada a `proxy-7dn.mb:6060`.

Logs principais: `logs/monitor-noticias.log`.

## 2. Capas / Qt WebEngine no Ubuntu

### Causas encontradas

- ao clicar em **ATUALIZAR CAPAS**, o ramo Washington Post já abre Qt WebEngine imediatamente;
- cada resolver criava um `QWebEngineProfile` e o teardown antigo substituía a página por um novo `QWebEnginePage` durante a destruição da view;
- na tela integrada, o motor de Capas permanece em um `QMainWindow` escondido cujo `centralWidget` foi retirado e reparentado; a V97 prendia a `QWebEngineView` a esse host escondido;
- o caminho HTTP/requests de Capas não aplicava `ProxySettings.requests_verify()`, então a cadeia TLS corporativa podia falhar e forçar fallback Chromium desnecessário.

### Correção V98

- `QWebEngineView` Linux passa a usar uma superfície offscreen independente;
- o profile sobrevive até as páginas `deleteLater()` terminarem e só é liberado com margem após o browser;
- teardown não cria mais uma página substituta durante a destruição;
- Chromium de clipping permanece serializado (`MAX_CONCURRENT_NEWSPAPERS=1`);
- requests da aba Capas usa a mesma política TLS do Proxy Geral, ainda restrita ao proxy autorizado;
- habilitados logs de renderer/Qt e `faulthandler` para um eventual crash nativo residual.

Logs novos:

- `logs/covers_webengine.log`
- `logs/covers_qt_messages.log`
- `logs/covers_native_crash.log`

## 3. Gravador de Tela Ubuntu

### Causas encontradas

- o código atual rejeita Wayland explicitamente antes do FFmpeg;
- no X11, não havia teste real de `x11grab`/`DISPLAY` antes da gravação;
- a captura de áudio era iniciada primeiro e qualquer falha PulseAudio/PipeWire cancelava também o vídeo;
- stderr do FFmpeg de áudio era descartado;
- o diagnóstico do portable verificava apenas se `ffmpeg` executava, não se o build continha `x11grab` nem se conseguia capturar o DISPLAY.

### Correção V98

- ao ligar o módulo em X11, o app verifica `ffmpeg -devices` e captura 1 frame real de 16x16 pelo `DISPLAY`;
- falhas de abertura do DISPLAY, Xauthority ou `x11grab` são exibidas e gravadas no log;
- o comando real de cada segmento continua registrado integralmente;
- erro de Pulse/PipeWire não cancela mais uma captura de vídeo válida: o segmento continua sem áudio e registra a falha;
- stderr do FFmpeg de áudio passa para `screen_recorder.log`;
- `TESTAR-PORTABLE.sh` passa a verificar presença de `x11grab` e, quando executado numa sessão X11, captura um frame real;
- caminhos de `bin/ffmpeg` e `bin/ffprobe`, permissões e variáveis gráficas ficam em `screen_recorder_linux_runtime.log`.

**Wayland:** não foi mascarado com XWayland. A captura completa de uma sessão Wayland exige o portal ScreenCast/PipeWire e autorização do usuário; `x11grab` não é equivalente. A V98 mantém a captura completa suportada em **Ubuntu on Xorg/X11** e informa isso explicitamente se a sessão for Wayland.

## GitHub Actions

O run Ubuntu Portable #75 do hash-base concluiu com sucesso. Não havia falha de Actions a corrigir. O diagnóstico foi reforçado via `portable/linux/TESTAR-PORTABLE.sh`, que já é executado pelo workflow Ubuntu existente.

**WORKFLOW: NÃO PRECISA ALTERAR.**
