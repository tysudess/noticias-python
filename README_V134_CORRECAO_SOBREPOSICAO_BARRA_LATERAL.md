# V134 — Correção da sobreposição na barra lateral

Base: `tysudess/noticias-python`, branch `main`, commit `b5dc77fcc3b0b3d7cef470cc027ca33641ec50c2` (V133).

## Diagnóstico

A V133 reorganizou as páginas listadas em `MainWindow.nav_buttons`, mas duas integrações adicionam itens fora desse dicionário:

- `screen_recorder_integration.py` cria `window.screen_recorder_nav` (Gravador de Tela);
- `admin_users_integration.py` cria `window._admin_users_button` (Administração).

A rotina V133 retirava os itens antigos do layout e recolocava somente as páginas do dicionário principal. Os dois botões adicionais continuavam como filhos soltos da barra, conservando a geometria antiga e aparecendo por cima dos novos itens. É a sobreposição mostrada na captura enviada.

## Correção V134

O `sidebar_widgets.py` atualizado agora recolhe os dois botões de integração antes de montar a navegação e os insere nos grupos apropriados:

- **Ferramentas:** Gravador de Tela;
- **Sistema:** Administração, antes de Configurações.

Os botões continuam sendo as mesmas instâncias criadas pelas integrações, portanto seus sinais, destinos e permissões são preservados. A regra de Capas no Ubuntu continua dependente de `SECTION_ORDER` e não foi alterada.

## Arquivos

- **SUBSTITUIR** `src/monitor_noticias/ui/sidebar_widgets.py`
- **ADICIONAR** `tests/unit/test_sidebar_layout_v134.py`

Nenhum workflow ou arquivo de negócio foi alterado.

## Validação

Sintaxe Python e integridade do ZIP foram verificadas localmente. O ambiente local desta sessão não tem PySide6 instalado, então os testes Qt não puderam ser executados aqui; o novo teste automatizado cobre explicitamente a presença dos dois itens extras e a reparentalização para dentro da área rolável. A confirmação visual deve ocorrer no próximo build Windows/Ubuntu.

Não houve commit nem push.
