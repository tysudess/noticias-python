# V132 — Validação isolada do Shiboken no Windows Portable

Base: `tysudess/noticias-python`, branch `main`, commit `c51946dd3c6ff73c5469acba8d43280e0d276c2c` (V131).

## Arquivo

**SUBSTITUIR** `MonitorDeNoticias.spec` na raiz do repositório.

## Diagnóstico da execução #299

O PyInstaller concluiu a etapa `COLLECT`. O teste adicional da V131 importou o Shiboken do portable, mas depois importou o pacote Python PySide6 do `site-packages` do runner. O pacote Python PySide6 é congelado no PYZ do PyInstaller; por isso, não deve ser validado tentando importá-lo como um pacote externo na pasta `_internal`.

## Correção V132

- Mantém a coleta completa de `shiboken6` com `collect_all`.
- Confere a presença do pacote físico `_internal/shiboken6`, módulos nativos `.pyd` e DLLs.
- Confere separadamente a presença de pelo menos um módulo nativo `QtCore*.pyd` na pasta física `PySide6`.
- Executa o teste de importação com `python -S`, sem carregar os pacotes do `site-packages` do runner. O teste importa exclusivamente o Shiboken presente na pasta coletada e confirma que o módulo veio do diretório do portable.
- Não tenta importar o pacote Python PySide6 fora do ambiente congelado pelo PyInstaller.
- Mantém a checagem do executável e do CArchive.

## Escopo

Somente `MonitorDeNoticias.spec`. Não altera workflow nem Ubuntu.

## Validação

A sintaxe do arquivo e a integridade do ZIP foram verificadas na preparação. O teste de importação isolado será executado no runner Windows do GitHub Actions. Não houve commit nem push por esta preparação.
