# V72 — Remover validação periódica da sessão

Foi removida a revalidação automática que rodava a cada 30 minutos.

Continua:
- login obrigatório;
- validação inicial da sessão/token;
- permissões por perfil;
- Minha conta;
- troca de senha;
- logout;
- validação do token na próxima abertura.

Deixa de acontecer:
- fechamento automático da Central por revalidação em segundo plano.

Arquivos:
- substituir `src/monitor_noticias/ui/auth_window_integration.py`
- adicionar `tests/unit/test_no_periodic_auth_validation_v72.py`

Windows e Ubuntu: mesma correção compartilhada.

WORKFLOW: NÃO PRECISA ALTERAR.
