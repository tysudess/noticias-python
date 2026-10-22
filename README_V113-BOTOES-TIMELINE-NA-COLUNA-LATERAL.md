# Central V113 — Controles da timeline na coluna lateral da pré-visualização

## Base confirmada
Repositório `tysudess/noticias-python`, branch `main`, commit `edcab133178fcca2aa1021285b433464950503a9` (22/10/2026).

## Alteração
Os controles de ajuste fino (−1s, −100ms, −10ms, +10ms, +100ms, +1s), duplicação, ordenação esquerda/direita, corte e exclusão de trecho passam para um painel compacto na coluna branca à direita da pré-visualização, abaixo das opções de marcação rápida.

Os próprios widgets são movidos — não duplicados — portanto conservam seus sinais, atalhos e comportamento. A timeline permanece para selecionar clipes e posicionar o cursor, mas deixa de ocupar espaço com a barra de ações. A prévia ampliada V112 é mantida.

## Arquivos
- SUBSTITUIR `src/monitor_noticias/app/composition.py`
- ADICIONAR `src/monitor_noticias/ui/video_timeline_side_controls_patch.py`
- ADICIONAR `tests/unit/test_v113_timeline_controls_side_panel.py`

## Workflow
WORKFLOW: NÃO PRECISA ALTERAR. Os workflows existentes disparam a partir de `src/**` e executam os testes unitários.

## Validação
A sintaxe dos arquivos e a integridade do pacote são verificadas localmente. Os testes visuais com PySide6 devem rodar no CI e a disposição final deve ser conferida dentro dos portables Windows/Ubuntu após o build.
