# Central V97 — Ubuntu: login, Capas e Gravador de Tela

Base verificada antes da alteração:

`241f3f0e9563ba2f8e4e3bf66e0fdd7c4a37610b`

## 1. Login lento / timeout intermitente no Ubuntu

### Sintoma

Com Proxy Geral corporativo ativo (`proxy-7dn.mb:6060`), o login ou a
validação da sessão salva pode permanecer vários segundos aguardando e terminar
em:

`Tempo limite ao acessar o servidor de autenticação.`

### V97

Somente no Ubuntu/Linux e somente para o proxy corporativo autorizado, a
Central faz um GET curto de aquecimento antes do primeiro POST de
`validate/login`.

Esse GET:

- não contém usuário;
- não contém senha;
- não contém token;
- usa a mesma `requests.Session`;
- reaproveita o túnel CONNECT/TLS quando o proxy permite;
- também aquece o Web App do Apps Script antes do POST real;
- tem orçamento curto de 2,5 s de conexão / 4 s de leitura;
- é executado no máximo uma vez por execução do cliente;
- se falhar, não bloqueia o login normal.

Windows, conexão direta e outros proxies não são alterados.

## 2. Aba Capas fechando a Central no Ubuntu ao Atualizar

O fluxo de Capas usa Qt WebEngine/Chromium para páginas que dependem de
JavaScript. A implementação existente podia manter várias QWebEngineView em
paralelo e posicioná-las em `x=-5000`, com viewport de grande dimensão.

No Linux isso pode terminar o processo Chromium/Qt de forma nativa, sem passar
por uma exceção Python.

### V97

Somente no Linux:

- Chromium usa `--disable-gpu`;
- `--disable-gpu-compositing`;
- `--disable-dev-shm-usage`;
- NÃO desativa o sandbox;
- a QWebEngineView usa `WA_DontShowOnScreen`;
- deixa de ser posicionada em coordenada negativa;
- WebGL e canvas 2D acelerado ficam desligados para esse navegador auxiliar;
- o clipping das Capas passa de 4 navegadores simultâneos para 1;
- encerramento do render process passa a ser registrado no log.

O patch é instalado antes do patch de autenticação do Proxy Geral, portanto as
credenciais do proxy continuam sendo aplicadas ao Chromium.

## 3. Gravador de Tela não iniciando no Ubuntu

### Causa confirmada

O `linux_boot_patch.py` já resolvia corretamente:

`<portable>/bin/ffmpeg`

Mas a V95, depois disso, executava novamente:

`_ffmpeg_for(self.app_root)`

No Ubuntu, `self.app_root` havia sido convertido para a raiz gravável de estado
(`data/...`), então a V95 sobrescrevia o caminho correto com algo equivalente a:

`<state_root>/bin/ffmpeg`

Esse arquivo não existe. A gravação não conseguia iniciar.

### V97

Depois da V95, e antes de criar a página do Gravador, a Central reaplica:

- `runtime_paths.runtime_binary("ffmpeg")`;
- a raiz real do bundle em `self.app_root`, permitindo que V95 também encontre
  `bin/ffprobe`.

Os diretórios de gravação, temporários e logs permanecem na raiz gravável
definida anteriormente; não voltam para uma área somente leitura.

Também é criado:

`logs/screen_recorder_linux_runtime.log`

com:

- tipo de sessão (`x11` / `wayland`);
- DISPLAY;
- WAYLAND_DISPLAY;
- caminho do bundle;
- caminho e existência de FFmpeg;
- caminho e existência de FFprobe.

### Wayland

O motor existente da Central continua usando `x11grab` no Ubuntu e portanto é
um backend X11. A V97 não falsifica `XDG_SESSION_TYPE` nem captura via XWayland
como se fosse o desktop completo.

Se o log indicar `session=wayland`, é necessário implementar um backend
Wayland/PipeWire/ScreenCast específico em uma etapa própria. Se indicar
`session=x11`, a regressão de caminho da V95 está corrigida nesta versão.

## Arquivos

SUBSTITUIR:

- `src/monitor_noticias/app/application.py`
- `src/monitor_noticias/ui/screen_recorder_integration.py`

ADICIONAR:

- `src/monitor_noticias/auth/linux_auth_transport_patch.py`
- `src/monitor_noticias/ui/covers_linux_stability_patch.py`
- `src/monitor_noticias/ui/screen_recorder_linux_runtime_fix.py`
- `tests/unit/test_v97_ubuntu_reliability.py`
- `README_V97-UBUNTU-LOGIN-CAPAS-GRAVADOR.md`

## Workflow

**WORKFLOW: NÃO PRECISA ALTERAR**
