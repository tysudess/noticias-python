# V124 — Tratamento da sessão salva no login

## Base verificada
Repositório `tysudess/noticias-python`, branch `main`, commit-base:
`3434ad2f64f8a8d2554583eeb512fb5990d01070` (27/10/2026).
A V123 já está incorporada na `main`.

## Problema corrigido
A tela de login valida o token salvo diretamente com `runtime.client.validate(token)`.
Por isso, a correção `AuthRuntime.validate_saved()` da V123 não controlava esse caminho
da interface. Quando o servidor rejeitava definitivamente um token antigo, ele podia
permanecer salvo e ser tentado novamente na próxima inicialização.

## Aplicação
### ADICIONAR
- `src/monitor_noticias/auth/saved_session_v124.py`
- `tests/unit/test_v124_saved_session.py`

### APLICAR PATCH
- `PATCH_login_dialog_v124.diff` altera `src/monitor_noticias/ui/login_dialog.py`.
  Aplicar na raiz do repositório, com `git apply PATCH_login_dialog_v124.diff`.

## Comportamento
- Sessão expirada/revogada/inválida e demais códigos definitivos já definidos pela V123:
  limpa o token salvo e pede novo login.
- Timeout, rede, proxy, TLS e códigos desconhecidos: preserva o token, mostra mensagem
  clara e permite que o usuário tente entrar manualmente.
- Não altera autenticação no servidor, política de permissões, TLS, proxy ou timeouts.

## Workflows
**WORKFLOW: NÃO PRECISA ALTERAR.** A mudança no arquivo `src/**` já aciona os workflows
existentes de Windows e Ubuntu. Ambos executam `tests/unit`.

## Validação
Os testes V124 cobrem falha definitiva, falha transitória, código desconhecido e
normalização do código. O ZIP foi verificado estruturalmente; os testes completos e
builds Windows/Ubuntu precisam ser confirmados nos GitHub Actions após a aplicação.
Nenhum commit ou push foi realizado por esta preparação.
