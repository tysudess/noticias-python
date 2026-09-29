# Central V91 — Extrator de Notícias confiável

Base confirmada antes da correção:

`462760ec65035ce31df8ef433949fd9533e6fda9`

## Regressão identificada

A V88 trocou o fluxo comprovado:

`1 URL -> 1 Electron -> 1 resultado -> encerra`

por:

`Electron persistente -> stdin -> várias URLs`

Nos Portables reais, o Electron podia permanecer aberto sem consumir a linha
enviada pelo `QProcess`. Como a UI não possuía um timeout final da requisição,
a tela ficava indefinidamente em "Extraindo...".

Os prints de teste com Veja/Abril e Terra confirmaram esse comportamento.

## V91

A extração volta a ser one-shot:

1. resolve o link direto;
2. lê o Proxy Geral;
3. cria um JSON temporário;
4. abre UM Electron headless;
5. passa URL e arquivo por variáveis de ambiente;
6. recebe o JSON;
7. encerra o Electron.

Não existe reutilização por stdin.

## Tempo limite

Existem agora duas proteções:

- motor Electron: 38 s no modo rápido;
- interface PySide6: 50 s.

Se o site/proxy travar, a Central devolve uma mensagem clara e libera o botão.

## Velocidade

O motor não executa mais uma segunda extração completa automaticamente.
O mecanismo interno de rede do extrator continua possuindo seus próprios
retries para erros transitórios.

O stdout do Electron também é drenado pelo QProcess para impedir bloqueio de
pipe em execuções que produzam muitos logs.

## Qualidade

O motor V1.25.19 permanece intacto. Toda a lógica de Readability, JSON-LD,
limpeza por portal, título, subtítulo, autor, data e corpo continua sendo usada.

A V91 corrige somente a orquestração do processo e seus limites de tempo.

## Arquivos

SUBSTITUIR:

- `src/monitor_noticias/ui/news_extractor_speed_patch.py`
- `tools/news_extractor/monitor-main.js`
- `tests/unit/test_v88_auth_extractor_performance.py`

ADICIONAR:

- `tests/unit/test_v91_news_extractor_reliable.py`
- `README_V91_EXTRATOR_CONFIAVEL.md`

## Workflow

**WORKFLOW: NÃO PRECISA ALTERAR**
