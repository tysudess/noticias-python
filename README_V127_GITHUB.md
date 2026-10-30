# V127 — Bordas douradas nos cards e abas da Central Windows

Base verificada: repositório `tysudess/noticias-python`, branch `main`, commit `9058443b879225ffe254340beb0ce7535b7a3b0b`.

## Arquivos no pacote

**SUBSTITUIR** os arquivos existentes:
- `src/monitor_noticias/app/application.py`

**ADICIONAR** os arquivos:
- `src/monitor_noticias/ui/gold_borders_patch.py`
- `tests/unit/test_v127_gold_borders_patch.py`

O ZIP preserva os caminhos relativos do repositório. O workflow existente já observa `src/**`, portanto não é necessário alterar workflows.

## Alteração visual

- Adiciona contorno dourado `#C6A15B` de 1 px ao perímetro completo dos cards e painéis identificados nas telas.
- Aplica o mesmo contorno aos itens de navegação lateral, abas Qt, abas customizadas de Fontes e Histórico e ao painel de cada conjunto de abas.
- Mantém os fundos, cores semânticas internas, textos, dimensões, cantos arredondados, espaçamentos e ações existentes.
- Atua também sobre cards criados dinamicamente após a abertura da Central.
- Não modifica a versão Android nem altera autenticação, proxy, TLS, coletores ou lógica funcional.

## Verificações locais da preparação

- O pacote contém os arquivos completos de código-fonte (não é um `.diff` ou script de aplicação local).
- A alteração central é instalada depois de as páginas e abas opcionais serem montadas.
- Os testes do workflow Windows/Ubuntu precisam ser conferidos depois de publicar a mudança na `main`; esta preparação não fez commit ou push.
