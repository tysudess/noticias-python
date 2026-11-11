# V135 — Refinamento visual da barra lateral

Base: `tysudess/noticias-python`, branch `main`, commit `d6c66c9560d4e0d9be2cc0420d101e60934df807` (V134).

## Objetivo

A organização e as posições da V134 foram mantidas. Esta versão trabalha somente a apresentação visual para a barra lateral deixar de parecer uma lista simples de botões, sem alterar a navegação que já está funcionando.

## Alterações

- Fundo azul-marinho com gradiente mais profundo e acabamento dourado discreto.
- Cabeçalho da Central com cartão de identidade, logotipo CM em destaque e contraste melhor entre título e subtítulo.
- Títulos dos grupos com filete dourado lateral e linha divisória.
- Cada opção recebe um pequeno bloco visual para o ícone, com acabamento próprio.
- Estado selecionado mais evidente: fundo azul mais claro, ícone com fundo dourado e marcador de posição atual.
- Hover e foco de teclado com realce próprio, preservando legibilidade.
- Cartão inferior de status mais destacado e alinhado ao restante da identidade visual.
- Itens de navegação com altura de 44 px; a área continua com rolagem própria para não sobrepor opções em telas menores.

## O que foi preservado

- Mesmas páginas, ações, permissões e conexões da V134.
- Mesma largura da barra (236 px), agrupamento, ordem e comportamento de rolagem.
- Gravador de Tela e Administração permanecem nos grupos corretos.
- A regra de Capas no Ubuntu continua sendo controlada por `SECTION_ORDER`.
- Nenhum ajuste em proxy, autenticação, páginas internas ou workflows.

## Arquivos

- **SUBSTITUIR** `src/monitor_noticias/ui/sidebar_widgets.py`
- **ADICIONAR** `tests/unit/test_sidebar_visual_v135.py`

## Validação

A sintaxe Python foi conferida e o ZIP será verificado quanto à integridade e aos caminhos. O ambiente desta preparação não possui PySide6; portanto, o teste de widgets Qt não pode ser executado aqui. Ele será executado nos workflows Windows e Ubuntu, que instalam as dependências da aplicação.

Não houve commit nem push para o GitHub.
