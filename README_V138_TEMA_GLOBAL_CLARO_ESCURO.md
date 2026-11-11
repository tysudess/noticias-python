# V138 — Tema global Claro e Escuro

## Objetivo

Acrescenta à aba **Configurações** a opção de alternar entre **Claro** e **Escuro**. A alteração é imediata, persiste após fechar e reabrir o programa e vale para o aplicativo Windows Portable e Ubuntu Portable.

O tema Escuro preserva a identidade azul-marinho com detalhes dourados aprovada na V136. O tema Claro usa superfícies claras e detalhes azuis.

## Arquivos do pacote

| Ação | Caminho |
|---|---|
| ADICIONAR | `src/monitor_noticias/ui/theme_engine.py` |
| ADICIONAR (ou SUBSTITUIR caso a V137 já tenha sido aplicada) | `src/monitor_noticias/ui/theme_store.py` |
| ADICIONAR (ou SUBSTITUIR caso a V137 já tenha sido aplicada) | `src/monitor_noticias/ui/theme_preferences.py` |
| SUBSTITUIR | `src/monitor_noticias/ui/gold_borders_patch.py` |
| ADICIONAR | `tests/unit/test_theme_engine_v138.py` |
| ADICIONAR | `tests/unit/test_theme_store_v138.py` |
| ADICIONAR | `tests/unit/test_theme_preferences_v138.py` |
| ADICIONAR | `README_V138_TEMA_GLOBAL_CLARO_ESCURO.md` |

## Aplicação global

O mecanismo adapta tanto a folha de estilo principal quanto as folhas locais já definidas pelos módulos. Também acompanha mudanças de estilo em controles criados dinamicamente durante o uso. Isso inclui barra lateral, páginas, cartões, botões, abas, campos de entrada, tabelas, menus e barras de rolagem.

As áreas que exibem conteúdo original — como pré-visualizações de PDF, imagens e vídeos — mantêm as cores do próprio material, para não alterar o conteúdo visualizado.

## Persistência e compatibilidade

A escolha é salva em:

`data/preferences/appearance.json`

O padrão para instalações sem preferência salva é **Escuro**. Preferências antigas com o valor `marinho` são reconhecidas automaticamente como `escuro`.

## Limites de alteração

O pacote não altera login, autenticação, proxy, automação, coletores, banco de dados, regras de monitoramento, exportação ou edição de arquivos. Não muda a ordem nem a navegação das abas.

## Instalação

1. Use este pacote V138 no lugar do pacote V137 de temas; não combine versões diferentes.
2. Faça upload dos arquivos mantendo exatamente os caminhos da tabela.
3. Se a V137 já tiver sido enviada, substitua os dois módulos de tema e `gold_borders_patch.py` pelos arquivos V138. Se não, adicione os módulos de tema e o mecanismo global.
4. Faça o commit na branch `main`.
5. Aguarde os workflows Windows e Ubuntu concluírem. Este pacote não substitui nem altera os workflows.

## Validação realizada antes do upload

- Compilação sintática dos módulos e testes Python.
- Testes unitários do armazenamento e transformação das folhas QSS.
- Verificação de integridade do ZIP e SHA-256.

O teste visual com Qt depende da instalação do PySide6. Caso o ambiente de validação não tenha PySide6, esse teste é marcado como ignorado; a validação visual definitiva deve ocorrer nos builds Windows e Ubuntu após o commit.
