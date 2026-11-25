# Central V147 — Estúdio de Artes: texto inline e painel organizado

## Base verificada
- Repositório: `tysudess/noticias-python`
- Branch: `main`
- Commit-base conferido antes das alterações: `5965e04d2c1fc7ce1161ada9d6451bfe231243aa`
- A V146.2 e a compatibilidade de inicialização V145 foram preservadas.

## O que muda
1. A adição de texto não abre mais caixas de diálogo. Um objeto editável é inserido no próprio canvas, com o texto inicial selecionado.
2. Duplo clique em um texto permite editar diretamente no canvas. O botão antigo passa a se chamar **Editar no canvas**.
3. Uma barra de texto aparece acima da área de desenho quando um texto está selecionado, com fonte, tamanho, negrito, itálico, sublinhado, cor e alinhamento.
4. Textos carregados de projetos `.centralart` antigos são promovidos para o novo comportamento de edição, mantendo posição, fonte, cor, largura e metadados dos itens.
5. O painel direito **Camadas e Objetos** passa a ter rolagem vertical. A lista de camadas tem altura limitada e os botões recebem altura mínima para não ficarem comprimidos ou sobrepostos.
6. A largura do painel direito foi ajustada para 300 px, mantendo o canvas central expansível.

## Arquivos no pacote
- `src/monitor_noticias/ui/art_studio_v147.py` — nova camada da interface.
- `src/monitor_noticias/ui/art_studio_integration.py` — instala V147 depois de V145 e V146; mantém os reparos de inicialização e QFrame.
- `tests/unit/test_art_studio_v147.py` — seis testes estruturais de regressão.

## Aplicação
Extraia o ZIP na raiz do repositório, preservando os caminhos. Não é necessário substituir `art_studio_page.py`, requirements, arquivos `.spec` ou workflows.

## Validação e limitações
- `py_compile` passou nos dois módulos e no teste.
- `pytest tests/unit/test_art_studio_v147.py`: 6 testes aprovados.
- O ZIP foi testado com `unzip -t`.
- O ambiente de preparação não possui PySide6; portanto, não foi possível executar a interface real nem fazer teste visual interativo.
- Os builds oficiais Windows e Ubuntu desta V147 ainda precisam ser executados depois do envio ao GitHub.
