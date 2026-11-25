# V148 — Estúdio de Artes

Base de trabalho conferida: `main` no commit `9c7969bf2f50789c8100a75db0a40c755f830c82`.

## O que foi acrescentado

- Redimensionamento de imagens por alças nos quatro cantos, preservando a proporção durante o arraste.
- Redimensionamento da caixa de texto pelas laterais no canvas.
- Campos numéricos de largura/altura para imagens e largura para textos.
- Opção de manter proporção da imagem ou ajustar largura e altura independentemente.
- Espelhamento horizontal e vertical de imagens.
- Persistência da transformação livre no formato `.centralart`.
- Proteção de inclusão: antes de criar uma nova imagem, texto ou forma, a ferramenta registra as camadas existentes e restaura qualquer camada que tenha sido removida durante a operação. Os elementos novos não substituem os anteriores.
- A barra de texto inline e o painel rolável da V147 permanecem ativos.

## Arquivos do pacote

- `run.py` — instala a V148 depois das camadas anteriores e antes da inicialização da aplicação.
- `src/monitor_noticias/ui/art_studio_v148.py` — nova camada de edição.
- `tests/unit/test_art_studio_v148.py` — testes estruturais e de regressão.

## Instalação

Extrair o ZIP na raiz do repositório, preservando os caminhos, e substituir os arquivos correspondentes. Não precisa alterar requirements ou workflows. Não enviar arquivos de cache ou temporários.

## Compatibilidade e validação

- Mantém a leitura de projetos V143–V147.
- Não acrescenta dependências externas.
- Testes estruturais e compilação sintática devem ser executados antes do commit.
- A validação visual do canvas, alças e campos de dimensão e os builds Windows/Ubuntu devem ser confirmados nos workflows oficiais após o envio ao GitHub.
