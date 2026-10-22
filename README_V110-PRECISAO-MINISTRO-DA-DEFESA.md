# Central V110 — Precisão do termo Ministro da Defesa

## Base confirmada

Repositório `tysudess/noticias-python`, branch `main`, commit `5ef609717658cc4ca6cb945fd64831c654c73a15` (22/10/2026). Pacote incremental. Nenhum commit ou push foi realizado.

## Correção

O matcher de vídeos anteriormente tratava os termos significativos como palavras que podiam aparecer separadas no título/resumo. Isso permitia que uma notícia sobre outro ministro correspondesse a `MINISTRO DA DEFESA` quando a palavra "defesa" aparecia em outro trecho.

A V110 torna estritos apenas os termos de cargo:

- `MINISTRO DA DEFESA`: exige a expressão `ministro da defesa` ou `ministra da defesa` contígua;
- `MINISTRA DA DEFESA`: aceita as mesmas duas formas do cargo;
- `MINISTÉRIO DA DEFESA`: exige a expressão do nome institucional `ministério da defesa`.

Os demais termos, como `MARINHA`, continuam usando o matcher existente. O filtro é instalado na inicialização da composição e atualiza o alias usado diretamente por `repositories/video_search.py`, além dos módulos públicos relacionados.

## Arquivos

- `src/monitor_noticias/app/composition.py` — substituir.
- `src/monitor_noticias/matching/video_defense_term_patch.py` — adicionar.
- `tests/unit/test_v110_video_defense_term_precision.py` — adicionar.

## Build

`WORKFLOW: NÃO PRECISA ALTERAR`. Os workflows existentes já executam testes unitários ao detectar alterações em `src/**`.

A validação incluída cobre as formas masculina/feminina, falsos positivos de ministro da Fazenda/Saúde/Educação/Justiça, o termo separado `Ministério da Defesa` e a preservação da correspondência dos demais termos. A conferência final em portables Windows/Ubuntu deve ocorrer após aplicação e build.
