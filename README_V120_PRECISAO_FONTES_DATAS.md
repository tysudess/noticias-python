# V120 — Precisão das fontes e das datas

Base de referência: `main` do repositório `tysudess/noticias-python`, commit `c678e4f80a3c27205ae139248faaee51c55ff007` (V119 aplicada pelo usuário; builds Windows e Ubuntu ainda estavam em execução quando esta versão foi preparada).

## O que muda

- O RSS do Google Notícias não recebe mais uma data de publicação inventada quando `pubDate` está ausente ou inválido. O valor passa a ser `0` (data desconhecida), evitando que o horário da execução transforme um item sem data em notícia aparentemente recente.
- Datas RSS sem fuso explícito passam a ser interpretadas como UTC, para que Windows e Ubuntu não atribuam horas diferentes ao mesmo registro.
- A coleta direta de últimas notícias deixa de usar o horário de captura como substituto da data de publicação. Quando a página do artigo não oferece data confiável ou não pôde ser aberta, o item é omitido da busca limitada por período, em vez de ser apresentado como publicado agora.
- Os testes exercitam a filtragem efetiva dos resultados pela fonte selecionada, além dos casos de data desconhecida.

A V120 não adiciona dependências, não faz novas requisições de rede para resolver URLs, não altera o proxy nem o processo de autenticação. O tratamento de links do Google Notícias em ações de abrir/copiar/compartilhar permanece no resolvedor já existente.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/collectors/news/google_news.py`
- `src/monitor_noticias/collectors/news/latest.py`

### ADICIONAR
- `tests/unit/test_v120_source_precision.py`
- `README_V120_PRECISAO_FONTES_DATAS.md`

### WORKFLOW
`WORKFLOW: NÃO PRECISA ALTERAR`

## Validação

Os testes nesta versão devem ser executados pela suíte do repositório após aplicar o ZIP. A construção e os testes completos Windows/Ubuntu ainda precisam confirmar esta versão; não inclua a V120 em uma release antes de os workflows passarem.
