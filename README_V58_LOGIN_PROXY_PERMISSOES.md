# V58 — Login + Proxy Geral + Permissões

## Estado da autenticação

A V58 já contém a tela de login e toda a integração.

Por segurança operacional, ela só se torna obrigatória quando:

`src/monitor_noticias/auth/config.py`

contiver uma URL válida do Apps Script terminada em:

`/exec`

Enquanto existir o placeholder:

`COLE_AQUI_A_URL_DO_APPS_SCRIPT_EXEC`

a Central continua abrindo normalmente.

## Fluxo quando a URL estiver configurada

Central
  -> Login
      -> existe token salvo?
          -> valida token pelo Apps Script
          -> token válido: entra
          -> token inválido: pede usuário/senha
      -> Proxy Geral ativo?
          -> SIM: autenticação passa pelo proxy
          -> NÃO: conexão direta
      -> usuário autorizado
          -> abre MainWindow
          -> aplica permissões às abas

## Proxy antes do login

A tela de login contém:

- status do Proxy Geral;
- Configurar proxy;
- Testar conexão com servidor.

O mesmo Proxy Geral já existente na Central é reutilizado.

Windows:
senha do proxy -> DPAPI.

Ubuntu:
senha do proxy -> Keyring/Secret Service.

## Sessão

"Manter conectado neste computador":

Windows:
token -> DPAPI CurrentUser.

Ubuntu:
token -> Keyring/Secret Service.

A senha do usuário nunca é salva pela Central.

## Permissões por aba

Mapeamento:

home -> Início
news -> Notícias
videos -> Vídeos
demands -> Demandas
sources -> Fontes
history -> Histórico
terms -> Termos
stop -> Parar buscas
news_extractor -> Extrator de Notícias
covers -> Capas
pdf_editor -> Editor de PDF
extractor -> Extrator de Vídeos
video_editor -> Editor de Vídeo
settings -> Configurações

Abas sem permissão são ocultadas.

Mesmo que alguma função tente navegar programaticamente para uma aba
bloqueada, a navegação é recusada.

## Usuário conectado

Depois do login, o cabeçalho mostra:

- nome;
- perfil;
- botão "Sair da conta".

Também é criada a opção "Sair da conta" no menu da bandeja.

## Revalidação

A sessão é revalidada a cada 30 minutos.

Se o servidor informar que:
- usuário foi bloqueado;
- sessão foi revogada;
- acesso expirou;

a Central limpa o token e encerra.

## Arquivos NOVOS

- src/monitor_noticias/auth/runtime.py
- src/monitor_noticias/ui/login_dialog.py
- src/monitor_noticias/ui/auth_window_integration.py
- tests/unit/test_auth_proxy_client.py
- tests/unit/test_auth_permissions.py

## SUBSTITUIR

- src/monitor_noticias/auth/client.py
- src/monitor_noticias/auth/__init__.py
- src/monitor_noticias/app/application.py

## Depois de publicar o Apps Script

Enviar a URL:

https://script.google.com/macros/s/.../exec

Então basta substituir o valor de `AUTH_API_URL` em:

`src/monitor_noticias/auth/config.py`

A partir desse build o login passa a ser obrigatório.

## WORKFLOW

NÃO PRECISA ALTERAR.

As alterações ficam em `src/**`, portanto os workflows Windows e Ubuntu
atuais já percebem a mudança.
