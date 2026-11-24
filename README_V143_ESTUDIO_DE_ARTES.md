# V143 — Estúdio de Artes integrado à Central

## Base utilizada

- Repositório: `tysudess/noticias-python`
- Branch: `main`
- Commit conferido antes da alteração: `d87b17c839d4a3729958c1d8d6fa29293a39c235`
- Não foram realizadas alterações diretamente no GitHub.

## Objetivo

Adicionar à navegação da Central uma nova ferramenta independente chamada **Estúdio de Artes**, com fluxo de criação gráfica inspirado em editores visuais como Adobe Express, sem reutilizar marca, código ou serviço proprietário da Adobe.

## Funcionalidades desta primeira versão

- Criar artes nos formatos quadrado, story/reels, paisagem, capa de YouTube, A4 e dimensão personalizada.
- Inserir imagens locais e redimensioná-las proporcionalmente para caber na arte.
- Inserir textos e definir tamanho e cor.
- Adicionar retângulos e elipses com cor configurável.
- Mover objetos diretamente no canvas.
- Selecionar objetos pela lista de camadas.
- Duplicar, excluir, trazer para frente e enviar para trás.
- Alterar o fundo da arte.
- Salvar e reabrir projetos `.centralart`, com as imagens incorporadas no próprio arquivo do projeto.
- Exportar a arte em PNG, JPG e PDF, usando a dimensão em pixels escolhida no canvas.
- Atalhos Ctrl+S, Ctrl+O e Delete.

## Integração e compatibilidade

- A ferramenta entra na seção Ferramentas da navegação lateral.
- Usa PySide6 e APIs já presentes no projeto. Não acrescenta dependências em `requirements.txt`.
- Projetos ficam em `ArtStudioProjects`, dentro da pasta de dados gravável (`state_root`) da Central, preservando o modo Portable.
- As páginas existentes, incluindo Editor de Vídeo, Editor de PDF e Capas, não são substituídas nem editadas.
- O `run.py` instala a integração antes de carregar a aplicação principal, para que a nova navegação já esteja disponível na inicialização.
- A lógica usa widgets e canvas nativos do Qt; não exige navegador embutido, internet, login Adobe ou assinatura.

## Arquivos deste pacote

1. `run.py` — instala a extensão antes de carregar a aplicação.
2. `src/monitor_noticias/ui/art_studio_page.py` — página e editor gráfico.
3. `src/monitor_noticias/ui/art_studio_integration.py` — integração com o menu lateral e a janela principal.
4. `tests/unit/test_art_studio_integration.py` — verificações estruturais da integração e das funções principais.
5. `README_V143_ESTUDIO_DE_ARTES.md` — este documento.

## Aplicação

Copie os arquivos do ZIP para a raiz do repositório, mantendo exatamente a estrutura de pastas. O `run.py` da raiz substitui o atual; os dois módulos `art_studio_*.py` são arquivos novos.

## Validação realizada nesta preparação

- Sintaxe Python/AST validada para os três módulos de aplicação e para o teste.
- `compileall` concluído sem erros.
- Verificação de integração estrutural adicionada para o GitHub Actions executar com pytest (4 testes locais aprovados).
- Teste isolado de geração de PDF com Pillow aprovado.
- Não foi possível executar um teste visual Qt nesta máquina de preparação porque PySide6 não está instalado no ambiente local.
- Os builds oficiais Windows Portable e Ubuntu Portable ainda precisam ser executados pelo GitHub Actions depois do envio dos arquivos.

## Limites conhecidos desta primeira entrega

- A primeira versão é um editor gráfico 2D essencial. Modelos de artes prontos, recorte avançado, filtros, remoção de fundo, gradientes, SVG, alinhamento magnético, desfazer/refazer e recursos de geração por IA ficam para etapas posteriores.
- O texto é inserido e editado por diálogo; a movimentação é feita diretamente no canvas.
- Arquivos de imagem importados são incorporados ao projeto ao salvar, então o projeto pode crescer conforme a resolução e quantidade de imagens.
