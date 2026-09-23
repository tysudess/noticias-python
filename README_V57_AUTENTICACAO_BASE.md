# V57 — Base de autenticação da Central

Esta etapa cria o servidor e a infraestrutura do cliente, mas NÃO bloqueia
a abertura da Central ainda.

Isso é proposital: primeiro configuramos o Google Apps Script e obtemos a
URL `/exec`. Só depois ativamos o login obrigatório.

## Servidor

Arquivos:

- tools/auth_server/Code.gs
- tools/auth_server/appsscript.json
- tools/auth_server/README_CONFIGURACAO.md

Servidor:
Google Apps Script

Banco:
Google Sheets

## Recursos

- usuário e senha;
- senha com salt + hash iterado;
- pepper secreto em Script Properties;
- usuário ativo/bloqueado;
- data de validade;
- limite de dispositivos;
- dispositivos registrados;
- sessões com token;
- revogação;
- perfis;
- permissões por aba;
- logs.

## Cliente já preparado

Novos módulos:

- src/monitor_noticias/auth/config.py
- src/monitor_noticias/auth/models.py
- src/monitor_noticias/auth/device.py
- src/monitor_noticias/auth/storage.py
- src/monitor_noticias/auth/client.py

Windows:
token preparado para DPAPI CurrentUser.

Ubuntu:
token preparado para Secret Service / Keyring.

## URL

Em:

`src/monitor_noticias/auth/config.py`

há temporariamente:

`COLE_AQUI_A_URL_DO_APPS_SCRIPT_EXEC`

Não altere application.py nesta etapa.

Depois que a URL for fornecida, a próxima etapa irá:
- colocar a URL no código;
- criar LoginDialog;
- validar token salvo antes de pedir senha;
- bloquear totalmente a MainWindow sem autenticação;
- aplicar permissões às abas;
- mostrar nome/perfil do usuário;
- adicionar logout.

## WORKFLOW

NÃO PRECISA ALTERAR.

Nenhum workflow é modificado nesta V57.
