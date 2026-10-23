# Central V116 — Desempenho das listas e progresso de Demandas

## Base
Repositório `tysudess/noticias-python`, branch `main`, commit `28790d281a2c4f245ecd1dfebb4239f757c56d0e` (23/10/2026). A V115 funcional está presente na `main` e esta entrega é incremental a ela.

## O que muda

1. **Notícias e resultados de Demandas:** `NewsModel.set_rows` deixa de reiniciar a lista quando a sequência de matérias é igual. Quando o mesmo artigo só tem campos atualizados ou muda o selo NOVO, emite `dataChanged` apenas para as linhas alteradas. Inserção, remoção e reordenação continuam usando reset de modelo, para manter a ordem correta.
2. **Notícias progressivas:** durante buscas ativas, a UI recarrega a janela temporal selecionada quando a assinatura do progresso muda. Como o repositório já persiste resultados por consulta/fonte, as novas matérias podem aparecer antes do fim da busca.
3. **Resultado de Demandas:** corrige o contrato de `DemandSweepResult` para carregar os itens e links novos que o repositório já retornava. Os quatro argumentos existentes continuam compatíveis; itens e links novos possuem valores padrão. Isso permite que os selos NOVO e os resultados retornados pela varredura sejam propagados pelo serviço.
4. **Vídeos:** os indicadores continuam atualizando, mas os cartões de vídeos só são removidos/recriados quando muda a assinatura dos resultados (inclusões, remoções, ordenação, metadados ou selo NOVO). Também preserva a seleção exclusiva dos botões de período da V115 e desativa os controles de período durante a execução.
5. **Demandas:** os cartões de demanda só são reconstruídos se cadastro, ativação ou dados da última execução realmente mudarem. Durante a busca, os botões Buscar/Excluir ficam desativados.
6. **Progresso de varredura:** a busca de todas as demandas reporta veículo/assunto atual, quantidade já verificada, encontrados, novos e falhas. O status é atualizado sem esperar o término de toda a varredura.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/app/composition.py`
- `src/monitor_noticias/automation/models.py`

### ADICIONAR
- `src/monitor_noticias/ui/first_tabs_performance_patch.py`
- `tests/unit/test_v116_first_tabs_performance.py`
- `README_V116-DESEMPENHO-LISTAS-E-PROGRESSO.md`

## Workflows
**WORKFLOW: NÃO PRECISA ALTERAR.** Os workflows existentes já são acionados por alterações em `src/**`.

## Validação e limites
Os testes unitários cobrem assinaturas de linhas, atualizações de modelo, progresso de Demandas e instalação incremental. O teste integrado com Qt e o build completo dos portables Windows/Ubuntu devem ser realizados no ambiente que contém as dependências do projeto. Nenhum commit ou push é realizado por este pacote.
