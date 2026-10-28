# V124 — Correção de integração da sessão salva

## Motivo
A V124 já possui o módulo `saved_session_v124.py`, os testes unitários e a documentação na `main`, mas a tela `login_dialog.py` ainda não chama esse módulo. Este patch integra a lógica na tela real.

## Arquivo
- `PATCH_login_dialog_v124.diff`: substitui o arquivo de patch antigo com hunks corrigidos e aplica as alterações a `src/monitor_noticias/ui/login_dialog.py`.

## Aplicação recomendada
Na cópia local atualizada do repositório:

```bash
git pull origin main
git apply --check PATCH_login_dialog_v124.diff
git apply PATCH_login_dialog_v124.diff
python -m pytest -q tests/unit/test_v124_saved_session.py tests/unit/test_v123_auth_reliability.py
git diff --check
git diff -- src/monitor_noticias/ui/login_dialog.py
```

Se `git apply --check` falhar, não force a aplicação: envie a mensagem completa para que o patch seja ajustado à versão real do arquivo.

## Comportamento esperado
- Se o servidor confirmar um código definitivo de sessão inválida/expirada/revogada, limpa o token salvo e solicita novo login.
- Em falha transitória de rede, timeout, proxy, TLS ou código desconhecido, preserva o token salvo e permite tentar login manual.
- Não altera as regras do servidor, a validação TLS, timeouts, proxy ou permissões.

## Importante
Não há confirmação de que o patch foi aplicado à `main` nem de que os builds Windows/Ubuntu foram executados. Depois de aplicar e publicar pelo fluxo habitual, confira o commit e os workflows antes de iniciar uma nova versão.
