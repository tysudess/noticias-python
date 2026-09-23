# V42 — Capas Valor Econômico / Washington Post por captura do navegador

## Diagnóstico

Em 23/09/2026 o FrontPages continua publicando:

- Valor Econômico
- The Washington Post

O problema observado no Central ocorre depois que a página é aberta:
o Qt WebEngine consegue carregar a página/capa, mas o programa pega a URL
encontrada e tenta fazer um SEGUNDO download com `requests`.

Nesse segundo request algumas URLs do FrontPages retornam HTTP 404.

## Estratégia V42

Para somente:
- VALOR ECONÔMICO
- THE WASHINGTON POST

o fallback FrontPages passa a funcionar assim:

1. Abre FrontPages no Qt WebEngine com o Proxy Geral.
2. Localiza a imagem real que já está renderizada no DOM.
3. Rejeita Washington Post SPORTS.
4. Tenta copiar os pixels em resolução natural via canvas.
5. Se canvas não estiver disponível, recorta a própria QWebEngineView.
6. Salva a captura localmente.
7. Executa o mesmo OCR/score já usado pelo Central.
8. NÃO faz um segundo download HTTP da URL do CDN.

## Valor continua Gmail primeiro

A ordem NÃO foi alterada:

1. Gmail / Apps Script / PDFs do Valor.
2. Se Página 1 não vier do Gmail: FrontPages via navegador interno.
3. Se o FrontPages não produzir uma capa válida: PressReader.

A V42 só substitui o passo 2.

## Washington Post

O Post usa diretamente:
FrontPages → Qt WebEngine → captura da imagem carregada → OCR.

A edição SPORTS continua rejeitada.

## Arquivos

NOVO:
- `src/monitor_noticias/ui/covers_frontpages_browser_capture_patch.py`

SUBSTITUIR:
- `src/monitor_noticias/app/application.py`

## Workflow

NÃO precisa alterar workflow.
NÃO precisa executar `Rebuild Planilhas Runtime`.

A V42 é somente Python/PySide6.
Depois de subir os dois arquivos, execute o build normal do Central.
