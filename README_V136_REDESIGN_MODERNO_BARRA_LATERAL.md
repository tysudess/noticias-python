# V136 — Redesign moderno da barra lateral

Base: `tysudess/noticias-python`, branch `main`, commit `43538a5cda93a7cdf5a5ddd0e9b112563bdb7ccc` (V135).

## Objetivo

A V135 foi considerada excessivamente decorada. A V136 muda a linguagem visual para uma navegação moderna, limpa e mais próxima de aplicações profissionais de monitoramento, mantendo o azul-marinho e o dourado da identidade da Central.

## Alterações visuais

- Remove gradientes, molduras douradas repetidas e cartões em volta de cada item.
- Usa fundo azul-marinho sólido com separador discreto.
- Simplifica o cabeçalho: marca CM em dourado, título claro e subtítulo azul acinzentado, sem moldura em volta do bloco.
- Usa títulos de grupo pequenos, discretos e com divisória fina.
- Mantém ícones em pequenos fundos neutros, com o dourado reservado ao ícone da página selecionada.
- Página ativa ganha fundo azul mais claro e marcador lateral dourado; hover e foco recebem realce discreto.
- Reduz a altura dos itens para 42 px e dos blocos de ícone para 28 px, mantendo a rolagem própria.
- Cartão de status passa a usar borda azul discreta e indicador verde, sem moldura dourada.

## O que permanece igual

- Largura da barra: 236 px.
- Grupos e ordem: Painel, Monitoramento, Ferramentas e Sistema.
- Gravador de Tela e Administração continuam nas posições corrigidas pela V134.
- Mesmas instâncias dos botões, sinais, destinos e permissões.
- Regra de Capas no Ubuntu continua vinculada a `SECTION_ORDER`.
- Nenhuma página, regra de negócio, workflow, autenticação ou proxy foi alterado. O patch global de bordas douradas foi ajustado apenas para deixar de impor molduras na navegação lateral; os contornos dourados dos cards e abas do conteúdo continuam ativos.

## Arquivos

- **SUBSTITUIR** `src/monitor_noticias/ui/sidebar_widgets.py`
- **SUBSTITUIR** `src/monitor_noticias/ui/gold_borders_patch.py`
- **SUBSTITUIR** `tests/unit/test_v127_gold_borders_patch.py`
- **SUBSTITUIR** `tests/unit/test_sidebar_visual_v135.py` (atualiza as dimensões esperadas)
- **ADICIONAR** `tests/unit/test_sidebar_visual_v136.py`

## Validação

Sintaxe Python, caminhos do ZIP e integridade do arquivo foram verificados localmente. O ambiente desta preparação não possui PySide6, portanto os testes Qt foram preparados, mas não executados localmente. A confirmação visual precisa ocorrer após os builds Windows e Ubuntu.

Não houve commit nem push.
