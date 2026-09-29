# V83 — Credenciais digitáveis + layout de Jornais Digitais

## Base confirmada
Patch preparado sobre a `main` confirmada em:

`391c922c856f76b758341b9d84c1dfaf23955e87`

Essa base já contém a V82.

## Problema 1 — usuário/senha não permaneciam digitados
A causa estava na atualização de sessão dos jornais.

Ao clicar em um jornal, o navegador oculto começa a receber cookies. Cada cookie
emitia `session_changed`, e a página chamava `_refresh_providers()`. Essa atualização
reconstruía/sincronizava o painel selecionado e chamava novamente o carregamento das
credenciais. Consequência: enquanto o usuário digitava, os campos eram limpos ou
recarregados.

### Correção
`_session_changed()` agora atualiza **somente a célula Sessão** da linha do jornal.
Ele não recarrega mais o painel de credenciais.

Também foi reforçado nos dois campos:
- `setReadOnly(False)`;
- foco `StrongFocus`;
- altura mínima de 38 px;
- destaque visual quando o campo recebe foco.

## Problema 2 — painel direito achatado
O painel "Edição selecionada" recebeu muitos controles nas versões recentes, mas o
espaço vertical continuou sendo dividido quase igualmente com o Histórico. Em telas
menores, o Qt reduzia excessivamente a altura de campos e botões.

### Correção
- painel da edição agora fica dentro de `QScrollArea`;
- controles mantêm alturas mínimas confortáveis;
- painel da edição tem altura interna mínima de 620 px;
- a região superior recebe mais espaço (`4`) e o Histórico menos (`1`);
- se faltar altura, aparece rolagem vertical em vez de achatar os controles.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/ui/digital_newspapers_page.py`

### ADICIONAR
- `tests/unit/test_digital_newspapers_v83.py`
- `README_V83_CREDENCIAIS_LAYOUT.md`

## Workflow
**WORKFLOW: NÃO PRECISA ALTERAR**
