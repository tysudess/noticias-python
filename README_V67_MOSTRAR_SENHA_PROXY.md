# V67 — Mostrar/ocultar senha do Proxy Geral

## Objetivo

Na tela de configuração de proxy exibida antes do login, permitir que o
usuário confira visualmente a senha digitada.

## Comportamento

A senha continua oculta por padrão.

Ao marcar:

`Mostrar senha`

o campo passa temporariamente para texto visível.

A opção muda para:

`Ocultar senha`

Ao desmarcar, o campo volta ao modo protegido.

Ao salvar, a senha volta automaticamente a ficar oculta.

## Segurança

Não muda o armazenamento da senha.

Windows:
- DPAPI CurrentUser.

Ubuntu:
- Secret Service / Keyring.

A senha não passa a ser salva em texto puro.

## Arquivo para substituir

`src/monitor_noticias/ui/login_dialog.py`

## Teste novo

`tests/unit/test_proxy_password_visibility_v67.py`

## Windows e Ubuntu

A alteração é compartilhada e vale para os dois.

## WORKFLOW

NÃO PRECISA ALTERAR.
