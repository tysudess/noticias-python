# V60 — Troca obrigatória e voluntária de senha

## NOVO

- senha temporária com troca obrigatória no primeiro acesso;
- coluna `TROCAR_SENHA` na planilha;
- tela de alteração obrigatória antes da MainWindow;
- `Minha conta -> Alterar senha`;
- `Alterar senha` no menu da bandeja;
- validação da senha atual;
- novo salt/hash em cada alteração;
- revogação das sessões antigas;
- nova sessão emitida após a troca;
- funciona com conexão direta ou Proxy Geral;
- Windows e Ubuntu.

## SUBSTITUIR NO GITHUB

- `tools/auth_server/Code.gs`
- `src/monitor_noticias/auth/models.py`
- `src/monitor_noticias/auth/client.py`
- `src/monitor_noticias/auth/runtime.py`
- `src/monitor_noticias/ui/login_dialog.py`
- `src/monitor_noticias/ui/auth_window_integration.py`

## NOVOS

- `src/monitor_noticias/ui/password_change_dialog.py`
- `tools/auth_server/README_CONFIGURACAO_SENHA.md`
- `tests/unit/test_auth_password_change.py`

## DEPOIS DE SUBIR OS ARQUIVOS

No Apps Script:

1. substitua `Code.gs` pelo novo;
2. execute `setupCentralAuth` uma vez;
3. confira a nova coluna `TROCAR_SENHA`;
4. atualize a implantação existente para `Nova versão`.

Para cadastrar um usuário com senha temporária:

- coloque a senha em `NOVA_SENHA`;
- deixe `TROCAR_SENHA` vazio ou `TRUE`;
- execute `Central Auth -> Processar senhas pendentes`.

## WORKFLOW

NÃO PRECISA ALTERAR.
