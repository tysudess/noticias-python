# Central V112 — Pré-visualização maior do editor de vídeo

## Base confirmada
Repositório `tysudess/noticias-python`, branch `main`, commit `d4b4372d972595e5a3f7fd39e2f93e218525a447` (22/10/2026).

## Objetivo
Deixar a pré-visualização do editor de vídeo bem maior na vertical e com proporção visual próxima de 16:9, em vez da área achatada limitada a 235–305 px.

## Comportamento
- Altura da área de prévia ajustada responsivamente pela largura do próprio vídeo, na proporção 16:9.
- Limites de 360 a 660 px para acomodar janelas menores e monitores grandes.
- A imagem é escalada mantendo a proporção original, sem esticar nem cortar o conteúdo.
- Timeline, marcação rápida, corte e exportação são preservados; o conteúdo fica mais alto e utiliza a rolagem vertical existente.

## Arquivos
- SUBSTITUIR `src/monitor_noticias/app/composition.py`
- ADICIONAR `src/monitor_noticias/ui/video_preview_layout_patch.py`
- ADICIONAR `tests/unit/test_v112_video_preview_layout.py`

## Workflow
WORKFLOW: NÃO PRECISA ALTERAR.

## Validação
Sintaxe Python dos arquivos do pacote e integridade do ZIP foram verificadas. Os testes unitários específicos foram adicionados; o build completo e a inspeção visual dentro dos portables Windows/Ubuntu ainda precisam ser executados após aplicar a correção.
