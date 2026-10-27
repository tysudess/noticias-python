# V121 — Diagnóstico seguro e exportação de suporte

## Base

`main` conferido em 27/10/2026: commit `8b1882d8c8fd35acd83a30f8eeaf4d538b025935`.

## Objetivo

Fortalecer o ZIP de diagnóstico já existente, sem alterar login, proxy, permissões ou a execução dos coletores.

## Mudanças

- Sanitiza mensagens de exceção no JSON exportado, não apenas os logs anexados.
- Mascara atribuições comuns de senha, token, segredo, chave de API, e-mail e credenciais.
- Mascara cabeçalhos Authorization/Proxy-Authorization, cookies, credenciais embutidas em URLs, parâmetros secretos em query strings e tokens JWT.
- Preserva no log exportado o contexto não sensível útil à investigação.
- Limita anexos a no máximo 10 arquivos `.log`, cada um limitado aos últimos 512 KB.
- Não modifica nem apaga os logs originais locais.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/diagnostics.py`

### ADICIONAR
- `tests/unit/test_v121_diagnostic_redaction.py`
- `README_V121_DIAGNOSTICO_SEGURO.md`

### WORKFLOW
`WORKFLOW: NÃO PRECISA ALTERAR`

## Validação

Testes direcionados cobrem formas comuns de vazamento por atribuições, cabeçalhos HTTP, cookies, URLs, query strings, JWT e conteúdo tanto do relatório quanto dos logs no ZIP. A suíte completa e os builds Windows/Ubuntu ainda precisam ser verificados no repositório após aplicação.
