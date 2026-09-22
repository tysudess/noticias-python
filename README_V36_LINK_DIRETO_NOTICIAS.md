# V36 — Notícias: link direto do veículo

## Causa encontrada

A tela de Notícias tinha dois comportamentos diferentes:

- Abrir / WhatsApp / Copiar usavam `ui/url_tools.py`, que ainda possuía
  um resolvedor Google News antigo baseado em `requests` direto.
- Extrair matéria emitia `news.link` cru e NÃO resolvia Google News.

Com Proxy Geral ativo, o resolvedor antigo podia falhar e devolvia
`news.google.com`. Essa falha ainda era guardada no cache.

## Correção

### `networking/google_news_resolver.py`
- usa o `HttpClient` do Central;
- tenta decodificação legada, RPC assinada e RPC por ID;
- NÃO guarda falhas no cache;
- mantém somente links de veículo resolvidos com sucesso.

### `ui/url_tools.py`
- usa `ProxySettings` + DPAPI;
- usa o Proxy Geral nas requisições do Google News;
- se a resolução RPC falhar, tenta seguir somente redirects HTTP reais;
- não procura links arbitrários no HTML;
- não mantém um link Google News como falha permanente.

### `ui/news_direct_link_patch.py`
- corrige o botão **Extrair matéria**;
- resolve o Google News antes de enviar a URL para o Extrator.

Agora estes quatro caminhos usam URL resolvida:
1. Abrir matéria
2. WhatsApp
3. Copiar link
4. Extrair matéria

## Arquivos

NOVO:
- `src/monitor_noticias/ui/news_direct_link_patch.py`

SUBSTITUIR:
- `src/monitor_noticias/networking/google_news_resolver.py`
- `src/monitor_noticias/ui/url_tools.py`
- `src/monitor_noticias/app/application.py`

## Workflow

NÃO precisa alterar workflow.
NÃO precisa executar Rebuild Planilhas Runtime.

É uma alteração somente do Python do Central.
Suba os quatro arquivos e gere o portable normal.
