# V144 — Evolução do Estúdio de Artes

## Base utilizada

- Repositório: `tysudess/noticias-python`
- Branch: `main`
- Commit conferido antes da alteração: `61d4d86ca726a0aacf4fb65b190eaa41acd47b82`
- A versão V143 foi conferida no GitHub antes da evolução.
- Nenhuma alteração foi feita diretamente no GitHub.

## Objetivo

Dar continuidade ao Estúdio de Artes a partir da tela apresentada após a instalação do V143, mantendo o editor separado das ferramentas existentes.

## Melhorias desta versão

- Corrige os campos de dimensão: painel esquerdo ampliado e campos de largura/altura separados, identificados e em largura total, evitando que números fiquem cortados.
- Acrescenta zoom por botões, atalho e Ctrl + roda do mouse, com indicador percentual, zoom 100% e ajuste à tela.
- Inclui quatro modelos rápidos editáveis: destaque de notícia, comunicado, convite e card informativo.
- Acrescenta transformação do objeto selecionado: rotação, escala e opacidade.
- Adiciona centralização do objeto no canvas.
- Acrescenta escolha de fonte e estilo para textos.
- Preserva opacidade e definição tipográfica completa ao salvar e reabrir projetos existentes.
- Os projetos V143 continuam compatíveis: os novos campos são opcionais na leitura e a versão do formato não foi elevada.

## Arquivos incluídos

1. `src/monitor_noticias/ui/art_studio_page.py` — evolução do editor gráfico.
2. `tests/unit/test_art_studio_integration.py` — testes estruturais para os novos recursos.
3. `README_V144_ESTUDIO_DE_ARTES.md` — este documento.

## Compatibilidade

- Windows Portable e Ubuntu Portable.
- Mantém PySide6 e Pillow já usados pela Central; não altera dependências.
- Não altera `run.py`, `art_studio_integration.py`, `main_window.py`, navegação das demais ferramentas ou workflows.
- Não altera Editor de Vídeo, Editor de PDF, Capas, extratores, proxy, autenticação ou login.
- Os arquivos continuam locais e os projetos seguem gravados na pasta `ArtStudioProjects`.

## Aplicação

Extrair o ZIP na raiz do repositório, preservando os caminhos. Somente o módulo do Estúdio e o arquivo de testes são substituídos/adicionados; o README fica na raiz.

## Validação realizada nesta preparação

- `py_compile` aprovado para o módulo atualizado e arquivo de testes.
- Testes estruturais específicos do Estúdio executados nesta preparação.
- Integridade do ZIP verificada.
- PySide6 não está instalado no ambiente de preparação, portanto não foi possível abrir a janela para validação visual direta.
- Os builds oficiais Windows e Ubuntu ainda precisam ser executados após a aplicação do pacote no GitHub.

## Observações

- Os modelos rápidos são composições iniciais feitas com objetos editáveis, não imagens chapadas.
- O redimensionamento e a rotação são aplicados ao objeto selecionado no painel de propriedades.
- Recorte livre de imagem, máscaras, filtros, alinhamento magnético, desfazer/refazer e geração por IA permanecem como etapas futuras.
