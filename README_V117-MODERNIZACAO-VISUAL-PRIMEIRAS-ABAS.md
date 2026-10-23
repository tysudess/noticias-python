# Central V117 — Modernização visual das quatro primeiras abas

## Base confirmada
Repositório `tysudess/noticias-python`, branch `main`, commit `28790d281a2c4f245ecd1dfebb4239f757c56d0e` (23/10/2026).

## Conteúdo desta entrega
Esta etapa padroniza visualmente Início, Notícias, Vídeos e Demandas: espaçamentos externos, controles de formulário, foco, botões, cartões, tipografia, barras de progresso, rolagem e cores dos estados de execução. Mantém a paleta azul/branco já utilizada, as ações atuais e o conteúdo de cada tela.

Na aba Notícias, os quatro botões desenhados pela delegate usam largura responsiva para preservar mais área de título em janelas menores. Nos cartões de Vídeos, os botões de ação têm limites de largura mais consistentes. A coloração de status usa propriedades de widget para execução, sucesso, resultado parcial, falha e cancelamento.

## Compatibilidade com as etapas anteriores
A V115 já está na `main`, mas a V116 anterior ainda não está publicada nesse commit. Para que este ZIP possa ser aplicado diretamente sobre a `main` confirmada sem perder a etapa 2, ele carrega também os arquivos da V116 (lista incremental, atualização progressiva e andamento das Demandas). Os arquivos da V116 são a versão do pacote entregue anteriormente; a instalação é mantida antes da camada visual V117.

## Arquivos
### SUBSTITUIR
- `src/monitor_noticias/app/composition.py`
- `src/monitor_noticias/automation/models.py`

### ADICIONAR / PRESERVAR COMO DEPENDÊNCIA DA ETAPA 2
- `src/monitor_noticias/ui/first_tabs_performance_patch.py`
- `tests/unit/test_v116_first_tabs_performance.py`

### ADICIONAR — ETAPA 3
- `src/monitor_noticias/ui/first_tabs_visual_patch.py`
- `tests/unit/test_v117_first_tabs_visual_system.py`
- `README_V117-MODERNIZACAO-VISUAL-PRIMEIRAS-ABAS.md`

## Workflow
**WORKFLOW: NÃO PRECISA ALTERAR.** Os workflows existentes já são disparados pelas alterações em `src/**` e executam testes unitários.

## Validação e limites
Foram executados 15 testes direcionados: 10 da etapa V116 e 5 da etapa V117; todos passaram. A sintaxe Python dos arquivos também foi validada. PySide6 não está disponível neste ambiente para comparação gráfica com a aplicação em execução; portanto, é necessário validar a aparência nos portables Windows e Ubuntu após o build. A integridade do ZIP foi verificada após sua criação.
