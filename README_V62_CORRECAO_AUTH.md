# V62 — Corrigir troca de senha e exibir Minha conta

## Problemas confirmados

1. A mensagem `Ação inválida.` significa que o Web App publicado no Google Apps Script ainda está em uma versão que não reconhece `change_password`.
2. O botão `Minha conta` não aparecia porque a busca pelo layout do cabeçalho não entrava em layouts instalados dentro de QWidgets intermediários.
3. A main ainda estava com o servidor 1.1.0; a V61 não havia sido aplicada nela.

## O que a V62 faz

- servidor Apps Script passa para versão 1.1.2;
- mantém a migração da V61 para `TROCAR_SENHA`;
- senha definida pelo administrador continua sendo temporária;
- `Testar conexão` rejeita servidor anterior a 1.1.2;
- `change_password` transforma `Ação inválida.` em uma orientação clara para atualizar a implantação;
- corrige a localização do cabeçalho;
- `Minha conta` e `Sair da conta` passam a ser inseridos no cabeçalho;
- menu da bandeja continua oferecendo `Alterar senha`.

## SUBSTITUIR no GitHub

- `tools/auth_server/Code.gs`
- `src/monitor_noticias/auth/client.py`
- `src/monitor_noticias/ui/auth_window_integration.py`

## ADICIONAR

- `tests/unit/test_auth_password_force_v62.py`
- `tests/unit/test_auth_server_version_v62.py`

## Ordem correta para atualizar

### 1. Google Apps Script primeiro

Substitua o Code.gs pelo da V62 e execute `setupCentralAuth`.

Depois: `Implantar -> Gerenciar implantações -> Editar -> Nova versão -> Implantar`.

A URL `/exec` permanece a mesma.

### 2. Confirme a versão

Na tela de login use `Testar conexão com servidor`. O resultado precisa mostrar `versão 1.1.2`.

### 3. Só depois gere/baixe o novo portable

Suba os arquivos Python da V62 no GitHub e aguarde o novo release.

## WORKFLOW

NÃO PRECISA ALTERAR.
