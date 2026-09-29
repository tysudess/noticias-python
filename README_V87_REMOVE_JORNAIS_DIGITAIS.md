# V87 — Remoção da aba Jornais Digitais

## Base
Patch preparado sobre a `main` confirmada no commit:

`cd82f7dab1ce716568346a0fb9a03acfba60c27b`

## Objetivo
Remover a funcionalidade **Jornais Digitais** da Central Inteligente de Mídia — Windows Portable e Ubuntu Portable — sem alterar as demais funcionalidades.

## Alteração funcional
O `application.py` não importa mais `digital_newspapers_integration` e não chama mais `install_digital_newspapers(window)`.

Com isso:
- a aba **Jornais Digitais** deixa de aparecer na sidebar;
- a página deixa de entrar no `QStackedWidget`;
- nenhum navegador/sessão/download de Jornais Digitais é iniciado pela aplicação;
- login principal, Proxy Geral, Home, Notícias, Vídeos, Fontes, Termos, Capas, Demanda, Editor PDF, Extratores e demais telas permanecem intactos.

## Limpeza do repositório
Um ZIP enviado pelo GitHub não consegue apagar arquivos que já existem no repositório. Por isso o pacote contém `REMOVER_DO_GITHUB_V87.txt` com a relação exata dos arquivos antigos da funcionalidade que devem ser excluídos para uma limpeza completa do código-fonte.

Mesmo antes dessa exclusão física, o novo `application.py` já deixa a funcionalidade totalmente desativada e ausente da interface.

## Arquivos da V87
### Substituir
- `src/monitor_noticias/app/application.py`

### Adicionar
- `tests/unit/test_remove_digital_newspapers_v87.py`
- `README_V87_REMOVE_JORNAIS_DIGITAIS.md`
- `REMOVER_DO_GITHUB_V87.txt`

## Workflow
**WORKFLOW: NÃO PRECISA ALTERAR**
