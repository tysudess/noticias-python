# V145 — Estúdio de Artes: recorte, camadas e histórico

## Base confirmada

- Repositório: `tysudess/noticias-python`
- Branch: `main`
- Commit verificado antes desta evolução: `a8818865dc5b3783afa4a7a60fbb4022f3286203`
- Base funcional: V144 do Estúdio de Artes

## O que esta versão acrescenta

1. **Recorte interativo de imagens** — selecione a imagem e marque com o mouse a região que deseja manter. O recorte é realizado em pixels da imagem, preservando a posição visual do elemento no canvas, inclusive quando ele já estiver girado ou ampliado.
2. **Visibilidade de camadas** — ocultar e mostrar objetos sem removê-los do projeto ou da exportação futura.
3. **Bloqueio de camadas** — impedir movimentação e edição acidental. O item continua acessível na lista para ser desbloqueado. A proteção também impede exclusão e alinhamento enquanto estiver bloqueado.
4. **Alinhamento ao canvas** — alinhar as camadas selecionadas ao centro horizontal, esquerda, direita, topo, centro vertical ou base.
5. **Desfazer e refazer** — botões na barra superior e atalhos `Ctrl+Z`, `Ctrl+Y` e `Ctrl+Shift+Z`. As alterações no canvas são agrupadas por uma pequena janela de inatividade, para que o movimento com o mouse não gere centenas de passos.
6. **Persistência** — os estados de visibilidade e bloqueio, além dos identificadores internos das camadas, são salvos no próprio `.centralart`. Projetos anteriores continuam sendo aceitos; camadas antigas são abertas visíveis e desbloqueadas.

## Arquivos incluídos

- `src/monitor_noticias/ui/art_studio_v145.py` — novas ferramentas, recorte e histórico.
- `src/monitor_noticias/ui/art_studio_integration.py` — ativa a evolução quando a página do Estúdio é criada.
- `tests/unit/test_art_studio_integration.py` — preserva os sete testes existentes da V144 e acrescenta seis verificações da V145.

## Instalação

1. Extraia o ZIP na raiz do repositório, mantendo as pastas e os caminhos originais.
2. Confirme que os três arquivos foram atualizados/criados.
3. Envie os arquivos para a branch `main` pelo procedimento habitual.
4. Execute os workflows `Build e Release Windows Portable` e `Build e Release Ubuntu Portable`.

Nenhum workflow, arquivo `.spec`, dependência ou recurso existente precisa ser alterado nesta entrega. A evolução usa PySide6 e o `QGraphicsScene` já utilizados pelo Estúdio; não adiciona pacotes de terceiros.

## Validação realizada nesta preparação

- `py_compile` nos dois módulos e no arquivo de testes: aprovado.
- Seis testes estruturais específicos da V145: aprovados.
- Integridade do ZIP: verificada.

## Limitações da validação

O ambiente de preparação não possui PySide6 instalado, então não foi possível abrir a janela, executar os gestos de recorte com mouse ou realizar um teste gráfico real. Os builds oficiais Windows e Ubuntu devem confirmar a integração final. Na verificação do GitHub feita nesta preparação, o Ubuntu da V144 estava aprovado e o Windows ainda estava em execução.

## Compatibilidade e preservação

- O Estúdio continua integrado como uma ferramenta independente da navegação principal.
- Não altera o Editor de Vídeo, Editor de PDF, Capas, Gravador de Tela ou monitoramento.
- Não altera o formato de saída PNG/JPG/PDF.
- Não altera os arquivos de workflow, os nomes de executáveis nem as configurações de build.
