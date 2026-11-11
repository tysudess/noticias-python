# V139 — Correção do tema escuro nas abas

## Objetivo

Corrige as superfícies claras que permaneciam visíveis com o tema **Escuro** nas abas **Notícias, Demandas, Vídeos, Histórico e Capas**. Mantém a opção Claro, a persistência da preferência e a identidade azul-marinho com detalhes dourados aprovada para o tema Escuro.

## O que foi corrigido

- **Notícias e Demandas:** o delegate de notícias usado nas listas desenha cartões, etiquetas e botões diretamente com `QPainter`. A camada global agora adapta essas cores ao tema Escuro, sem substituir o delegate original nem alterar seus eventos.
- **Histórico:** o mesmo tratamento é aplicado ao delegate próprio do Histórico, mantendo os botões de abrir, copiar e compartilhar e todas as ações existentes.
- **Vídeos:** as folhas de estilo dos cartões, filtros, controles, áreas de progresso e listas continuam sendo convertidas pelo mecanismo global; a cobertura de testes foi ampliada para incluir essas superfícies.
- **Capas:** o QSS da janela auxiliar agora é reaplicado ao conteúdo central depois que ele é transferido para a página embutida. Os estilos dos controles e dos itens criados dinamicamente também são convertidos quando a aba é exibida e ao alternar o tema.
- **Conteúdo de mídia:** as imagens reais das capas e as pré-visualizações continuam sendo conteúdo original; a correção altera apenas a interface ao redor delas.

## Arquivos do pacote

| Ação | Caminho |
|---|---|
| SUBSTITUIR | `src/monitor_noticias/ui/theme_engine.py` |
| SUBSTITUIR | `src/monitor_noticias/ui/theme_preferences.py` |
| ADICIONAR | `tests/unit/test_theme_engine_v139.py` |
| ADICIONAR | `README_V139_CORRECAO_TEMA_ESCURO_ABAS.md` |

## Instalação

1. Use os arquivos deste pacote sobre a versão atual da `main` que contém a V138.
2. Mantenha exatamente os caminhos indicados na tabela.
3. Faça o commit na branch `main`.
4. Aguarde os workflows de Windows e Ubuntu finalizarem e valide as cinco abas nos dois sistemas.

Não combine estes arquivos com versões anteriores de `theme_engine.py` ou `theme_preferences.py`.

## Escopo preservado

O pacote não altera a lógica de pesquisa, coleta, atualização, histórico, abertura/cópia de links, geração de PDF, autenticação, proxy, banco de dados, nem o conteúdo das capas. Também não modifica a barra lateral aprovada na V136.

## Validação realizada neste pacote

- Compilação sintática dos dois módulos Python alterados.
- Testes unitários de conversão de cores QSS e de cores desenhadas por `QPainter`.
- Verificação de integridade do ZIP e SHA-256.

O ambiente de empacotamento não possui PySide6, portanto não foi possível executar um teste visual Qt nem uma inicialização real da interface. A validação visual final deve ser feita nos builds Windows e Ubuntu após o commit.
