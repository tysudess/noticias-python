# V123 — Estabilidade de login, rede e proxy

## Base
Repositório `tysudess/noticias-python`, branch `main`, commit-base confirmado em 27/10/2026: `f07ddd6673e3efd0d20acffda61ac19d3957d17b`.

## Mudanças
- Preserva o token salvo quando a validação falha por causas transitórias, como timeout, rede, proxy, TLS, indisponibilidade ou código de erro não reconhecido.
- Limpa o token salvo apenas para códigos conhecidos que indicam sessão revogada, expirada, inválida, usuário bloqueado/expirado/inexistente ou dispositivo bloqueado/limite atingido.
- Deixa de exibir corpos HTTP arbitrários em mensagens de erro, evitando que respostas intermediárias ou de servidores/proxies revelem dados sensíveis.
- Substitui detalhes brutos de exceções de rede por mensagens estáveis que informam o tipo da falha sem reproduzir URLs, parâmetros ou credenciais.
- Não altera timeouts, proxy, autenticação remota, permissões ou validação TLS.

## Arquivos
### SUBSTITUIR
- `src/monitor_noticias/auth/__init__.py`

### ADICIONAR
- `src/monitor_noticias/auth/reliability_v123.py`
- `tests/unit/test_v123_auth_reliability.py`
- `README_V123_LOGIN_REDE_PROXY.md`

## Workflows
**WORKFLOW: NÃO PRECISA ALTERAR.** A alteração em `src/**` já aciona os workflows existentes de Windows e Ubuntu, que executam a suíte unitária.

## Validação
Os testes V123 foram preparados para cobrir preservação/limpeza do token salvo, mensagens de rede sem detalhes sensíveis e supressão de corpos HTTP arbitrários. Antes de liberar a versão, os workflows Windows e Ubuntu devem passar no GitHub Actions. Nenhum commit ou push foi realizado.
