# V124 — Integração do tratamento de sessão salva

## Arquivo a substituir no GitHub
Substitua o arquivo existente:
`src/monitor_noticias/ui/login_dialog.py`

O ZIP preserva o caminho relativo do repositório. Não contém scripts de aplicação local, executáveis ou workflows desnecessários.

## Base conferida
Repositório: `tysudess/noticias-python`
Último commit conferido nesta preparação: `0949a1145a9663041387f769ee2e70d029d9e895`
Arquivo-base: `src/monitor_noticias/ui/login_dialog.py`
O arquivo-base ainda não importava nem chamava `handle_saved_session_failure`.

## Alteração
- Integra `handle_saved_session_failure` na tela de login.
- Em falha definitiva conhecida da sessão salva, limpa o token e solicita novo login.
- Em falhas transitórias ou desconhecidas, preserva o token e permite login manual.
- Não altera os workflows: ambos já disparam quando há alterações em `src/**`.

## Verificações realizadas aqui
- Conferência da `main` e do arquivo-base no GitHub.
- Sintaxe Python do arquivo de saída validada com `ast.parse`.
- ZIP criado e caminho interno conferido.

## Ainda pendente
Não foi possível executar pytest contra o clone completo nem confirmar builds Windows/Ubuntu nesta preparação. Após colocar o arquivo no GitHub, verifique os dois workflows e o novo commit antes de considerar a V124 concluída.
