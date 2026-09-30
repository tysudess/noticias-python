# Central V96 — correção dos testes de versão do Auth Server

Base conferida antes da correção:

`e4fc9b210b1b93d82c36bf82774ab56a08f3294e`

## Erro confirmado no GitHub Actions

Os logs reais dos builds Windows e Ubuntu falharam em:

`tests/unit/test_v90_auth_server_diagnostics.py::test_v90_apps_script_keeps_all_auth_actions_and_bumps_version`

O teste V90 exigia literalmente:

`const AUTH_VERSION = "1.2.0"`

Porém a V94 atualizou corretamente o Auth Server para:

`const AUTH_VERSION = "1.3.0";`

Portanto o workflow estava rejeitando uma versão MAIS NOVA do servidor por causa
de um teste legado congelado na versão antiga.

## Correção

O teste V90 agora:

- valida que `AUTH_VERSION` usa versão semântica `MAJOR.MINOR.PATCH`;
- exige versão mínima `>= 1.2.0`;
- continua verificando login, validate, logout, change_password e
  `server_timing_ms`.

O teste V94 também foi tornado resiliente para evitar a mesma regressão no
próximo aumento de versão:

- exige Auth Server `>= 1.3.0`;
- continua verificando todos os endpoints administrativos e a proteção ADMIN.

Nenhuma lógica de autenticação, nenhuma senha, nenhum endpoint e nenhum código
do gravador V95 foram alterados.

## Warning do Node.js 20

O aviso visto no runner sobre ações GitHub ainda baseadas em Node.js 20 é
somente um warning do ambiente do GitHub Actions. Ele não foi a causa desta
falha.

## Arquivos

SUBSTITUIR:

- `tests/unit/test_v90_auth_server_diagnostics.py`
- `tests/unit/test_v94_admin_users.py`

ADICIONAR:

- `README_V96_CORRECAO_TESTES_AUTH_WORKFLOW.md`

## Workflow

**WORKFLOW: NÃO PRECISA ALTERAR**
