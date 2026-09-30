# Central V94 — Administração de usuários

Base confirmada antes da alteração:

`b21f7775d2d93cc648fe4fd41ef70725ef3563ca`

## Objetivo

Adicionar uma aba administrativa dentro da Central para que o perfil ADMIN
possa gerenciar usuários sem abrir diretamente a planilha Google Sheets.

## Visibilidade

A aba **Administração**:

- não faz parte da navegação normal;
- não é criada para OPERADOR, EDICAO ou CONSULTA;
- só é instalada quando a sessão autenticada possui `profile == ADMIN`;
- o Apps Script valida novamente token, dispositivo, validade, status e perfil
  ADMIN em toda ação administrativa.

Portanto, esconder a aba não é a única proteção: o backend também recusa
requisições administrativas de qualquer outro perfil.

## Criar usuário

A aba permite informar:

- usuário;
- nome;
- perfil: OPERADOR / CONSULTA / EDICAO / ADMIN;
- senha temporária;
- validade opcional;
- limite de dispositivos;
- permissões opcionais.

Quando `PERMISSOES` fica vazio, o usuário herda as permissões padrão do perfil.
Para OPERADOR e ADMIN isso corresponde ao comportamento atual do servidor.

A senha temporária:

- precisa ter no mínimo 8 caracteres;
- é hashada no Apps Script;
- a coluna NOVA_SENHA permanece vazia;
- SALT, SENHA_HASH e ITERACOES são gravados diretamente;
- `TROCAR_SENHA` fica TRUE;
- portanto o novo usuário troca a senha no primeiro login.

## Redefinir senha

O ADMIN seleciona um usuário na tabela e informa uma nova senha temporária.

O servidor:

1. autentica novamente a sessão ADMIN;
2. gera novo salt/hash;
3. nunca grava a senha em texto puro;
4. ativa `TROCAR_SENHA`;
5. revoga todas as sessões anteriores do usuário.

A própria senha do ADMIN atual continua sendo alterada pela função
**Minha conta**, evitando revogar de forma inconsistente a sessão administrativa
que está sendo usada naquele momento.

## Servidor

O Auth Server passa para:

`1.3.0`

Novas ações:

- `admin_list_users`
- `admin_create_user`
- `admin_reset_password`

Depois de substituir `tools/auth_server/Code.gs`, é obrigatório criar uma
**NOVA versão da implantação do Web App** no Google Apps Script.

Não é preciso alterar a estrutura existente da planilha nem recriar usuários.

## Arquivos

SUBSTITUIR:

- `src/monitor_noticias/app/application.py`
- `tools/auth_server/Code.gs`

ADICIONAR:

- `src/monitor_noticias/auth/admin_api.py`
- `src/monitor_noticias/ui/admin_users_page.py`
- `src/monitor_noticias/ui/admin_users_integration.py`
- `tests/unit/test_v94_admin_users.py`
- `README_V94_ADMIN_USUARIOS.md`

## Workflow

**WORKFLOW: NÃO PRECISA ALTERAR**
