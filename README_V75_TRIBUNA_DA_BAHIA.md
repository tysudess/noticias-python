# V75 — Tribuna da Bahia como fonte real

## O que estava errado na V73

A V73 tentou adicionar `Tribuna da Bahia` apenas visualmente depois que a
interface já estava criada.

Isso não alterava corretamente o catálogo usado pelo `AppContainer`,
pelo controller e pelo `RuntimeNewsRunner`.

## Correção V75

A Tribuna da Bahia agora é adicionada ao catálogo ANTES de:

`from monitor_noticias.app.composition import AppContainer`

Assim, quando `composition.py` importa `NEWS_SOURCES`, a nova fonte já está
presente e segue para:

- aba Fontes;
- controller;
- seleção manual de fontes;
- RuntimeNewsRunner;
- buscas filtradas por fonte.

## Cadastro

ID:
`ba-tribuna-da-bahia`

Nome:
`Tribuna da Bahia`

Estado:
`BA`

Região:
`Nordeste`

Grupo:
`Bahia • Nordeste`

Aliases:
- `Tribuna Bahia`
- `Jornal Tribuna da Bahia`

## Arquivos

SUBSTITUIR:
- `src/monitor_noticias/ui/sources_bahia_patch.py`
- `src/monitor_noticias/app/application.py`

ADICIONAR:
- `tests/unit/test_tribuna_bahia_catalog_v75.py`

## Windows e Ubuntu

A correção é compartilhada.

## WORKFLOW

NÃO PRECISA ALTERAR.
