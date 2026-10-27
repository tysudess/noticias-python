# V119 — Estabilidade e integridade do monitoramento

Base de referência: `main` do repositório `tysudess/noticias-python`, commit `e02c21f46553c3a3a49a1d0a4fef7a24bdba9604`.

## O que muda

- **Acesso concorrente ao SQLite:** `SQLiteConnection` agora possui um `RLock` compartilhado; operações de leitura, gravação, atualização, migração e encerramento de `NewsDb` e `VideoDb` são serializadas pelo mesmo bloqueio da conexão.
- **Transações:** o bloqueio fica retido do `BEGIN` ao `COMMIT`/`ROLLBACK`, evitando interleaving de outra operação na mesma conexão durante a transação.
- **Isolamento por demanda:** uma exceção inesperada ao processar uma demanda é registrada como erro dessa demanda e o monitoramento continua para as demais. A rotina reconsulta o token de cancelamento para que uma interrupção solicitada continue interrompendo o processo, em vez de ser convertida em falha normal.
- **Diagnóstico sem registrar a mensagem bruta da exceção no status:** o campo de erro guarda o tipo da exceção, evitando persistir inadvertidamente URLs ou informações sensíveis que possam estar em mensagens de bibliotecas de rede.

Não altera a autenticação, o proxy, certificados TLS, permissões, seleções de fontes, regras de correspondência, tabelas ou fluxos de compilação.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/database/connection.py`
- `src/monitor_noticias/database/news_db.py`
- `src/monitor_noticias/database/video_db.py`
- `src/monitor_noticias/repositories/news_repository.py`

### ADICIONAR
- `tests/unit/test_v119_stability_and_demand_isolation.py`
- `README_V119_ESTABILIDADE_INTEGRIDADE.md`

### WORKFLOW
`WORKFLOW: NÃO PRECISA ALTERAR`

## Validação

Os testes adicionados exercitam operações SQLite concorrentes e confirmam que uma falha em uma demanda não impede as demandas seguintes. Os builds Windows e Ubuntu devem ser executados pelo GitHub Actions depois de aplicar o pacote. Este ZIP não publica alterações nem inicia builds remotos.
