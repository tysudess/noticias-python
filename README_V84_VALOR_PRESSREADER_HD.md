# V84 - Valor Econômico via PressReader HD

## Base confirmada

Patch preparado sobre a `main` atual:

`6dcccf869c469baeb5b8e490c84366705e6c4860`

Essa base já contém a V83.

## Objetivo

Substituir **somente o adaptador do Valor Econômico** que tentava localizar um PDF/exportação genérica por um fluxo específico baseado na estratégia já comprovada no repositório `tysudess/aplicativo-extrair-valor`.

O Correio Braziliense e os demais jornais não tiveram seu método alterado nesta versão.

## Fluxo V84 do Valor

1. Abre a edição autorizada do Valor no PressReader:
   `https://valoreconomico.pressreader.com/valor-economico/AAAAMMDD/page/N`
2. Mantém a sessão/cookies protegidos da Central.
3. Percorre as páginas sequencialmente a partir da página 1.
4. Lê somente os recursos que o viewer oficial já carregou.
5. Identifica imagens de página em `*.prcdn.co/.../img` com parâmetros `page` e `file`.
6. Para cada página, tenta as variantes HD já usadas pelo APK:
   - `scale`: 416, 390, 364, 338, 312, 286, 260, 234, 208, 182, 156, 130, 104;
   - `width`: 3200, 3000, 2800, 2600, 2400, 2200, 2000, 1800, 1600.
7. A resolução alvo é 2200 px de largura e o mínimo aceito é 1800 px.
8. Quando chega ao fim da edição, baixa todas as páginas HD e monta um único PDF.
9. JPEG é incorporado no PDF por passthrough `DCTDecode`, sem recompressão.
10. PNG/WebP/outros formatos são convertidos para RGB e armazenados com Flate (compressão sem perdas), sem reduzir pixels.
11. Todas as páginas do PDF recebem a mesma largura física e altura proporcional.

## Segurança

- Não exporta senha, cookies ou tokens para o GitHub.
- URLs temporárias do CDN ficam somente em memória durante a execução.
- A sessão continua usando o cofre seguro existente da Central.
- Proxy Geral é reutilizado pelo download das páginas.
- Não há quebra de DRM, CAPTCHA ou paywall.

## Interface

O Valor passa a aparecer com método **Páginas HD**.

No Histórico, PDFs gerados por esse método são marcados como:

`HD / pixels preservados`

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/digital_newspapers/providers.py`
- `src/monitor_noticias/digital_newspapers/browser.py`
- `src/monitor_noticias/ui/digital_newspapers_page.py`
- `tests/unit/test_digital_newspapers_v80.py`

### ADICIONAR
- `src/monitor_noticias/digital_newspapers/pressreader_hd.py`
- `tests/unit/test_digital_newspapers_v84.py`
- `README_V84_VALOR_PRESSREADER_HD.md`

## Validação local

- `py_compile`: OK
- testes V79 + V80 + V81 + V83 + V84: **24 passed**
- teste específico V84: **5 passed**
- PDF sintético de 3 páginas foi gerado, lido pelo `pypdf` e renderizado pelo PDFium com 3 páginas válidas.
- teste confirma que JPEG original aparece literalmente no stream do PDF final, sem recompressão.

## Workflow

**WORKFLOW: NÃO PRECISA ALTERAR**

As dependências utilizadas (`requests`, `Pillow`, `pypdf`, `PySide6`) já existem no projeto.
