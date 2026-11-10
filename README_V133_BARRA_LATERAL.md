# V133 — Modernização da barra lateral

Base: `tysudess/noticias-python`, branch `main`, commit `84409d90de7709f34e17e9e4fa100413c6bbc562`.

## Arquivos

- **SUBSTITUIR** `src/monitor_noticias/ui/sidebar_widgets.py`
- **ADICIONAR** `tests/unit/test_sidebar_layout_v133.py`

## O que foi revisto

A barra anterior tinha 184 px de largura, itens de 34 px e textos de 7–9 px no stylesheet, além de ícones com cores variadas e setas repetidas. Isso deixava a navegação apertada e visualmente irregular.

A V133:

- amplia a lateral para 236 px;
- organiza os itens em `PAINEL`, `MONITORAMENTO`, `FERRAMENTAS` e `SISTEMA`;
- coloca a navegação em uma área com rolagem própria, mantendo a identificação e o status fixos;
- aumenta o tamanho dos itens para 40 px e melhora a legibilidade dos textos;
- padroniza os ícones, reduz os elementos decorativos e destaca a página ativa com azul-marinho e dourado;
- inclui foco por teclado e nomes acessíveis, sem mudar os destinos ou ações dos botões;
- respeita a lista `SECTION_ORDER` existente, portanto a aba Capas continua fora da navegação Linux e permanece no Windows.

A reorganização é aplicada quando a janela é exibida, depois que a `MainWindow` já criou todos os itens e conexões. Nenhuma página, regra de negócio, workflow ou configuração de proxy foi alterada.

## Verificação da base

Na revisão da `main`, o Windows Portable #301, commit `84409d90`, concluiu com sucesso as etapas de testes, PyInstaller, validação do ZIP e publicação da Release. O build Ubuntu mais recente disponível nesta revisão é o #108, do commit anterior `328c927b`.

## Testes

O novo teste verifica largura, grupos, preservação dos itens, comportamento ativo e respeito à lista de seções disponível no sistema. Os testes de interface usam `QT_QPA_PLATFORM=offscreen`.

A validação final dos módulos e testes completos precisa ocorrer nos workflows Windows e Ubuntu após o envio à `main`. Não houve commit nem push nesta preparação.
