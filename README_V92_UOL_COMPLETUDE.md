# Central V92 — UOL: completude e corpo multibloco

Base confirmada antes da alteração:

`a62e8a97ff9100cf6a3439fc35a99da2977f3830`

## Caso real usado

URL de teste:

`https://www.uol.com.br/nossa/colunas/historias-do-mar/2026/09/30/marinha-dos-eua-quer-excluir-heroi-negro-e-colocar-trump-em-nome-de-navio.htm`

A Central retornava apenas o trecho inicial e o apresentava como matéria
completa.

A página possui conteúdo dividido em vários blocos, inclusive ao redor de
publicidade. O UOL também identifica esse caso como conteúdo para assinantes.

## Alterações

O novo runtime 1.25.20:

- identifica resultados UOL suspeitos por tamanho e número de blocos;
- para conteúdo público, tenta reunir os blocos seguintes do mesmo documento,
  mantendo a ordem e descartando publicidade, comentários, recomendações e
  áreas de navegação;
- não depende somente do bloco escolhido pelo Readability;
- usa apenas uma conferência adicional curta (18 s, uma tentativa) quando o
  primeiro resultado realmente parece incompleto;
- se o acesso atual recebeu somente preview e a página sinaliza
  "Só para assinantes", não chama o preview de matéria completa;
- não tenta contornar paywall: informa que uma sessão UOL autenticada será
  necessária para obter o conteúdo integral.

## Arquivos

SUBSTITUIR:

- `tools/news_extractor/engine/extrator-materia-v1.25.10-runtime.js`

ADICIONAR:

- `tools/news_extractor/engine/extrator-materia-v1.25.20-runtime.js`
- `tests/unit/test_v92_uol_completeness.py`
- `README_V92_UOL_COMPLETUDE.md`

## Workflow

**WORKFLOW: NÃO PRECISA ALTERAR**
