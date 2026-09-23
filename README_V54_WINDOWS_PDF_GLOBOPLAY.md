# V54 Windows - PDF em qualidade original + login Globoplay

## PDF

- Remove o popup modal de sucesso que estava ficando branco e aparentando
  congelamento.
- JPEG sem corte/rotação é inserido no PDF com os bytes JPEG originais,
  sem recompressão.
- PNG/WebP/BMP/TIFF continuam lossless e sem redução de resolução.
- Imagens transformadas continuam usando todos os pixels do arquivo.
- PDF original sem transformação continua vetorial.
- PDF que precise de rasterização continua em 450 DPI na qualidade HIGH.
- Capa personalizada passa a ser copiada no formato original, sem resize.

A compressão lossless de imagens não-JPEG usa zlib level=1. Isso muda o
tempo/tamanho do arquivo, mas NÃO reduz qualidade.

## Globoplay

O problema da tela era real: o workflow Windows não estava gerando
`resources/globoplay-login-helper/GloboplayLoginHelper.exe`.

Agora o workflow:
1. executa tools/build-globoplay-login-helper.py;
2. exige helper >= 20 MB;
3. testa o EXE com --help;
4. copia explicitamente para o portable;
5. abre o ZIP final e confirma que o helper está dentro dele;
6. falha a build se o arquivo estiver ausente ou incompleto.

## NOVO

- src/monitor_noticias/ui/pdf_export_quality_fix.py

## SUBSTITUIR

- src/monitor_noticias/app/application.py
- .github/workflows/build-portable.yml

## WORKFLOW

PRECISA ALTERAR.

Substituir somente o workflow Windows `build-portable.yml`.
Não alterar o workflow Ubuntu.
