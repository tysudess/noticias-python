# V141 — Correção de descoberta e extração do Poder Naval

## Base

Branch `main` do repositório `tysudess/noticias-python`, commit-base
`9f2a29835e71d8dbd5ca3dc958c3a72668034b30`.

## Problema identificado

O catálogo já tinha a fonte especializada **Poder Naval**, com o identificador
`especializada-poder-naval`, mas o coletor de últimas notícias não possuía uma
rota direta para esse veículo. Além disso, o motor V1.25.21 não incluía
`naval.com.br` na lista de portais com recuperação específica. Quando a leitura
principal não conseguia interpretar a página, não havia uma segunda tentativa
adaptada ao portal.

## Correções

- Inclui a página de últimas notícias `https://www.naval.com.br/blog/` na rota
direta do coletor para a fonte especializada Poder Naval.
- Reconhece `naval.com.br` e `www.naval.com.br` no runtime de extração.
- Se a leitura genérica falhar ou retornar corpo insuficiente, faz uma segunda
leitura HTML usando o mesmo `fetchComRetry` e a configuração de rede/proxy do
motor já ativo.
- Usa seletores WordPress e `articleBody`/JSON-LD, com filtros para navegação,
comentários, tags, compartilhamento, créditos, publicidade e recomendações.
- Mantém a URL original e os metadados da matéria; se a leitura específica não
conseguir melhorar um resultado principal válido, preserva o resultado já obtido.
- A versão funcional do runtime passa para **1.25.22**. O nome do executável
portable continua `ExtratorMateriasPortable-V1.25.19` para manter compatibilidade
com os workflows Windows e Ubuntu existentes.

## Arquivos do ZIP

| Ação | Caminho |
|---|---|
| Substituir | `src/monitor_noticias/collectors/news/__init__.py` |
| Substituir | `tools/news_extractor/engine/extrator-materia-v1.25.10-runtime.js` |
| Adicionar | `tools/news_extractor/engine/extrator-materia-v1.25.22-runtime.js` |
| Adicionar | `tools/news_extractor/tests/extrator-v12522.test.js` |
| Adicionar | `tests/unit/test_poder_naval_latest.py` |
| Adicionar | `README_V141_PODER_NAVAL.md` |

## Validação

- `node --check` nos runtimes e no teste JavaScript.
- Teste Python específico de descoberta/rota Poder Naval.
- Teste Node do parsing HTML e limpeza do portal após instalar `jsdom` com as
  dependências do extrator.
- Builds oficiais Windows e Ubuntu e validação visual/funcional ainda precisam
  ser executados após o commit na `main`.

O ZIP não altera o GitHub e não troca nomes de executáveis ou workflows.
