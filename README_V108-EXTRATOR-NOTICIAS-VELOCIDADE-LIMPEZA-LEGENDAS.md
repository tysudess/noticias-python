# Central V108 — Velocidade do Extrator e remoção de legendas de fotos

## Base confirmada

Repositório: `tysudess/noticias-python`  
Branch: `main`  
Commit-base conferido: `a2e065f848949080bceab893b5bbc81fa45578d5` (20/10/2026).

Este pacote é incremental sobre essa `main`. Não contém novamente os arquivos da correção V107 (VEJA nas buscas de notícias) nem alterações do Android.

## Objetivo

Reduzir trabalho de rede redundante no modo rápido do Extrator de Matérias e impedir que legendas/créditos de fotografias sejam incluídos como parágrafos do texto extraído.

## Alterações

- **Legendas antes da extração:** o bootstrap instala um sanitizador no `JSDOM` antes de carregar o motor. O sanitizador remove `figcaption`, elementos sinalizados por classes/atributos de legenda e crédito de foto, e parágrafos curtos dentro de figuras que contêm imagem.
- **Limpeza textual final:** remove blocos identificáveis como `Foto:`, `Legenda da foto:`, `Crédito:`, `Imagem:` e descrições curtas que terminam com crédito de foto entre parênteses. Mantém parágrafos normais e não remove deliberadamente legendas/subtítulos de vídeos.
- **Modo rápido com limite real de tentativas:** o limite de duas tentativas é aplicado no `undici.fetch` usado pelo motor, inclusive à extração principal, e não apenas à função exportada de retry. A espera por requisição continua limitada a 8,5 segundos no modo rápido. Isso evita ciclos longos de tentativas repetidas; em caso de rede persistentemente instável, pode retornar erro mais cedo em vez de insistir.
- **Cache menos oneroso:** deixa de fazer buffering especulativo de HTML para todos os portais. O cache temporário fica restrito à URL do G1 cuja leitura duplicada é conhecida, e só armazena respostas HTML pequenas com tamanho declarado e sem `Set-Cookie`.
- **Proxy e compatibilidade:** preserva o Proxy Geral, o fluxo one-shot do Electron e os nomes atuais dos executáveis usados nos builds Windows/Ubuntu.

## Arquivos

### SUBSTITUIR

- `tools/news_extractor/monitor-bootstrap.js`
- `tools/news_extractor/package.json`
- `tests/unit/test_v104_news_extractor_fast_quality.py`

### ADICIONAR

- `tools/news_extractor/article-quality.js`
- `tests/unit/test_v108_news_extractor_speed_caption_cleanup.py`
- `README_V108-EXTRATOR-NOTICIAS-VELOCIDADE-LIMPEZA-LEGENDAS.md`

## Workflows

**WORKFLOW: NÃO PRECISA ALTERAR.** Os workflows Windows e Ubuntu já incluem `tools/news_extractor/**` nos gatilhos e executam os testes de `tests/unit`.

## Validação e limites

Os testes focados da correção passaram localmente (12 testes), assim como `node --check` dos dois arquivos JavaScript e a leitura do JSON do pacote. O pacote não foi enviado ao GitHub. Não foi executado aqui o build completo dos portables nem uma medição ao vivo contra todos os portais; portanto não se promete um ganho percentual fixo de velocidade. O efeito real deve ser conferido após reconstruir o Extrator/portables e testar os sites que estavam lentos ou incluindo legendas.
