# Central V115 — Primeira etapa de correções funcionais das quatro primeiras abas

## Base
Repositório `tysudess/noticias-python`, branch `main`, commit `80060a6a5d057d1c1e8ed12a0f7d84f5a5c26918` (23/10/2026).

## Correções incluídas
1. **Notícias — período correto:** guarda o intervalo selecionado e recarrega os resultados desse mesmo período após o término da busca. O atalho da Home e a rotina automática continuam usando as últimas 24 horas. O banco recebe uma consulta SQL por intervalo, sem ler todo o histórico para filtrar em Python. Os botões de período ficam desativados durante a busca.
2. **Início — indicadores reais:** “Notícias 24h” conta artigos publicados nas últimas 24 horas; “Vídeos armazenados” conta toda a base; “Vídeos hoje” conta por `captured_at` desde a meia-noite local; “Fontes” usa o catálogo `specialized_sources`. As legendas dos cartões deixam explícito o significado.
3. **Estados honestos de execução:** Notícias e Vídeos não mostram “concluída com sucesso” antes da primeira busca nem quando a execução falhou, foi interrompida ou terminou parcialmente. A aba Demandas preserva a mensagem real da última operação quando ela falha ou é interrompida.
4. **Progresso mais confiável:** a assinatura de atualização da janela passa a considerar `active`, horário de início/fim, encontrados, novos e falhas. Assim a tela atualiza quando esses números mudam mesmo que a etapa atual e o percentual permaneçam iguais.
5. **Vídeos — período exclusivo:** apenas um botão de período fixo permanece selecionado e os controles de intervalo ficam desativados durante a execução.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/app/composition.py`

### ADICIONAR
- `src/monitor_noticias/ui/first_tabs_functional_patch.py`
- `tests/unit/test_v115_first_tabs_functional_fixes.py`
- `README_V115-PRIMEIRAS-ABAS-CORRECOES-FUNCIONAIS.md`

## Workflows
**WORKFLOW: NÃO PRECISA ALTERAR.** Os builds existentes já são acionados por alterações em `src/**` e incluem os testes unitários.

## Validação
Os testes unitários específicos, a compilação Python e a integridade do ZIP foram executados no ambiente disponível. A inspeção visual e os builds completos Windows/Ubuntu continuam necessários após aplicar o pacote.
