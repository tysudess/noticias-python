# V125 — Otimização da leitura do token de sessão (GitHub source)

## Base conferida
- Repositório: `tysudess/noticias-python`
- `main` usada como base: commit `8ce444aecb7dfbe82aa48819cd9f0df7b73e3e4b`
- Arquivo de origem: `src/monitor_noticias/auth/storage.py`

## Arquivos do ZIP

**SUBSTITUIR** no repositório:
- `src/monitor_noticias/auth/storage.py`

**ADICIONAR** ao repositório:
- `tests/unit/test_v125_auth_token_store.py`

Este README é apenas a instrução de aplicação. Não é necessário adicioná-lo ao repositório, se preferir manter as instruções fora do código.

## O que muda
- Remove a chamada `exists()` seguida por `load()` no token de sessão.
- No backend Linux, `exists()` já executava uma leitura do Secret Service; portanto, o fluxo anterior podia consultar o cofre duas vezes antes de validar a sessão.
- Preserva o armazenamento seguro existente (DPAPI no Windows e Secret Service/Keyring no Linux), sem fallback em texto simples e sem alterar regras de autenticação.
- Registra no log somente leituras que demorem 250 ms ou mais, informando duração e backend, sem registrar o token.
- Adiciona testes unitários para leitura única, token ausente, cofre indisponível e backend ausente.

## Workflows
Não alterar workflows. O arquivo de produção altera `src/**`, que está incluído nos triggers. O teste é adicionado em `tests/**` e será executado pelos workflows depois que a mudança em `src/**` disparar a execução.

## Verificação
A V124 foi integrada à `main` no commit `8ce444a`. Na consulta inicial desta preparação, os workflows Windows e Ubuntu desse commit estavam em execução. Antes de publicar a V125, confira se ambos terminaram; como o workflow usa `cancel-in-progress`, um novo push durante a execução poderá cancelar a rodada anterior.

Nenhum commit ou push foi feito por esta preparação.
