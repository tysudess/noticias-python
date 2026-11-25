# V151 — Estúdio de Artes

Base: `b94109f328bf399d329d7e9a999942b6d5c297d3` (`main`, com V150).

## Evoluções desta versão

- Alinhamento de múltiplos objetos pela esquerda, centro horizontal, direita, topo, centro vertical e base, usando os limites da seleção.
- Distribuição horizontal e vertical com espaçamento uniforme entre três ou mais objetos.
- Movimentação em coordenadas do canvas, preservando a posição de itens que pertencem a grupos transformados.
- Selecionar tudo, inverter seleção e limpar seleção na página atual.
- Avançar ou recuar uma camada por vez, inclusive com seleção múltipla, sem alterar a ordem interna dos filhos de grupos.
- Proteção: objetos bloqueados e ocultos são ignorados nas operações de composição; o painel informa quantos objetos estão editáveis.
- Atalhos de teclado para alinhamento, distribuição e ordenação de camadas.
- Painel próprio de composição, integrado à área rolável de camadas já existente.

## Arquivos do pacote

- `run.py` — instala V151 depois de V150.
- `src/monitor_noticias/ui/art_studio_v151.py` — camada incremental da V151.
- `tests/unit/test_art_studio_v151.py` — testes estruturais e de regressão da V151.

## Aplicação

Copie os três arquivos do pacote para os caminhos correspondentes no repositório. Preserve todos os demais arquivos. Não altere workflows, dependências, executáveis ou os módulos V148–V150.

## Validação e observações

A camada usa apenas PySide6 e recursos do Estúdio já instalados. Os projetos `.centralart` não recebem novos campos e mantêm compatibilidade com as versões anteriores. Os testes automatizados deste pacote verificam integração, operações, proteção de camadas, atalhos e ausência de dependências novas.

A interface gráfica deve receber um smoke test em Windows e Ubuntu para conferir seleção por Ctrl+clique/área, alinhamento em objetos agrupados, distribuição com itens de diferentes dimensões, undo/redo após operações e comportamento dos atalhos durante a edição de texto.
