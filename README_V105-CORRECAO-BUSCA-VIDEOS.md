# Central V105 — Correções prioritárias na busca de vídeos

## Base consultada

Repositório `tysudess/noticias-python`, branch `main`, commit confirmado antes da preparação: `0ad304a918f8ceb4cd21771f5fa8aa23222faadd` (14/10/2026).

## Objetivo desta versão

Corrigir problemas de precisão antes de iniciar uma otimização dedicada às buscas regionais. O mesmo código Python é usado na versão Windows e na versão Ubuntu Portable.

## Correções incluídas

- **Datas do YouTube:** quando a aba do canal não informa data relativa válida, o coletor deixa `publishedAt=0` em vez de reutilizar o horário da coleta. A data do feed RSS prevalece quando disponível. Isso evita que vídeos antigos sejam classificados automaticamente como recém-publicados.
- **Período antes da página individual:** candidatos com data conhecida fora da janela solicitada são descartados antes de abrir a página individual. Candidatos sem data ainda podem ser abertos para tentativa de enriquecimento; se a data permanecer desconhecida, não passam pelo filtro do período.
- **Band por programa/afiliada:** fontes específicas da Band não aceitam mais qualquer rota genérica `/videos/`. Precisam corresponder a uma das rotas específicas declaradas em `linkHints`. A fonte geral Band continua permitindo a rota geral.
- **Busca interna como fallback nacional:** se a listagem inicial de uma fonte nacional incluída na correção não contiver correspondência com termos ou demandas, o sistema consulta a busca interna do portal. Demandas ativas e termos próprios da instalação têm prioridade; em seguida, usa a ordem prioritária dos termos padrão. O fallback é limitado a seis consultas por fonte e é intencionalmente restrito às fontes nacionais nesta etapa.
- **Globoplay Jornalismo geral:** passa a poder acionar o fallback de consulta por termo em vez de depender exclusivamente dos vídeos expostos na categoria geral.
- **Testes:** novos testes cobrem datas desconhecidas/relativas, filtro de período, identificação de rota específica da Band e fallback nacional. As buscas regionais não recebem ainda consultas extras, para a otimização regional ficar separada na próxima etapa.

## Arquivos

### SUBSTITUIR

- `src/monitor_noticias/collectors/video/youtube.py`
- `src/monitor_noticias/matching/video_rules.py`
- `src/monitor_noticias/repositories/video_search.py`

### ADICIONAR

- `tests/unit/test_v105_video_search_accuracy.py`
- `README_V105-CORRECAO-BUSCA-VIDEOS.md`

## Workflows

**WORKFLOW: NÃO PRECISA ALTERAR.** A correção muda módulos Python já cobertos pelos fluxos de build e acrescenta teste em `tests/unit/`; não exige dependências ou executáveis novos.

## Validação executada e limites

Os três módulos modificados passaram por `py_compile`; os nove testes novos passaram em um harness local com dependências simuladas. Esse harness não substitui a execução da suíte unitária completa dentro do repositório nem uma busca real nos portais. O código ainda precisa ser exercitado nas fontes reais, pois mudanças no HTML, bloqueios, autenticação e proxy podem afetar a coleta. Data ausente é tratada como desconhecida, não estimada como se fosse confirmada.

A etapa seguinte será medir e reduzir o tempo da varredura das fontes regionais, sem aumentar o número de requisições por portal sem controle.
