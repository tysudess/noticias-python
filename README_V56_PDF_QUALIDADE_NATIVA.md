# V56 — PDF com qualidade nativa da imagem

## Objetivo

O PDF gerado não deve parecer uma cópia da prévia da tela.

A exportação passa a trabalhar diretamente com a imagem fonte.

## Regras

### JPEG sem edição

- bytes JPEG originais;
- mesma largura em pixels;
- mesma altura em pixels;
- nenhuma recompressão;
- `/Interpolate false` no PDF.

### PNG / WebP / BMP / TIFF

- todos os pixels originais;
- nenhum resize/downsample;
- compressão Flate lossless;
- `/Interpolate false`.

### PDF original

Se não houver crop/rotação/flip:
- continua vetorial;
- não passa pela prévia;
- não é rasterizado.

### Imagem cortada/girada

Usa a imagem fonte original para a transformação.
A exportação mantém todos os pixels resultantes do corte/rotação.

## DPI

O PDF passa a respeitar o DPI gravado no arquivo quando ele é válido.

Se o arquivo não tiver DPI confiável, usa 300 DPI como densidade física
padrão, SEM alterar a quantidade de pixels.

Isso evita espalhar uma imagem pequena por uma página A4 inteira e reduzir
a densidade aparente.

## Interpolação

A imagem XObject recebe:

`/Interpolate false`

Isso pede ao visualizador PDF para não aplicar suavização que pode deixar
screenshots e textos pequenos aparentemente borrados.

## Log de qualidade

Depois de gerar um PDF, o programa grava:

`data/pdf_export_quality.log`

Exemplo:

`JPEG ORIGINAL | imagem.jpg | 3000x2000 px -> 3000x2000 px | sem recompressao`

Assim conseguimos confirmar objetivamente se houve ou não redução.

## Arquivo a substituir

`src/monitor_noticias/ui/pdf_export_quality_fix.py`

## Workflow

NÃO PRECISA ALTERAR.

A alteração vale para Windows e Ubuntu porque o módulo é compartilhado.
