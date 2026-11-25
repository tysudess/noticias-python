# V150 — Estúdio de Artes

Base verificada: `90606bd70c1a33a3919f1e750a2e4aa8abde7e17` (main, com V149).

## Evoluções desta versão

- Documento com até 30 páginas: adicionar, duplicar, renomear, excluir, reorganizar por arrastar e exportar todas em PDF.
- Compatibilidade com projetos `.centralart` antigos de página única.
- Fundos sólidos, degradês direcionais e imagens incorporadas ao projeto.
- Biblioteca inicial de elementos reutilizáveis: etiqueta, faixa de título, selo, botão, chamada e número destacado.
- Grade visual e guias inteligentes que encaixam bordas e centros de objetos próximos e do canvas.
- Histórico independente por página: desfazer/refazer em uma página não apaga as edições realizadas nas demais.
- Tipografia avançada: espaçamento entre caracteres e entre linhas.
- Histórico V145 integrado ao fundo V150: desfazer/refazer restaura também cores, degradês e imagens de fundo, preservando a seleção do objeto quando possível.
- Salvamento atômico e validações de segurança: até 30 páginas, 500 objetos por página, 20 MB por imagem de fundo e limite de 80 milhões de pixels por exportação PDF multipágina.

## Arquivos do pacote

- `run.py` — instala V150 depois das camadas V148 e V149.
- `src/monitor_noticias/ui/art_studio_v150.py` — nova camada do Estúdio.
- `tests/unit/test_art_studio_v150.py` — testes da evolução e regressão.

## Aplicação

Copie os três arquivos do ZIP para os caminhos correspondentes no repositório. Preserve todos os demais arquivos. Não altere workflows nem dependências.

## Validação e limitações

A validação deste pacote inclui compilação sintática, testes estruturais locais e integridade do ZIP. A interface Qt precisa ser executada em Windows e Ubuntu para validar o comportamento interativo real, em especial: mudança/reordenação de páginas, histórico separado por página, edição dos elementos agrupados, guias durante arraste, recuperação de documento multipágina e exportação de PDF com páginas de dimensões diferentes. A exportação multipágina usa Pillow já presente nas dependências da Central. A interface Qt ainda precisa de smoke test interativo em Windows e Ubuntu.
