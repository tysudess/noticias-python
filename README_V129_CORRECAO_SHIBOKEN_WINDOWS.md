# V129 — Correção do runtime Shiboken no Windows Portable

Base: `tysudess/noticias-python`, branch `main`, commit `328c927b762a8444df3fe32eeb534cf0b208ad94` (V128).

## Arquivo

**SUBSTITUIR** `MonitorDeNoticias.spec` na raiz do repositório.

## Correção

A versão portátil falha ao abrir porque o inicializador do PySide6 não encontra `shiboken6/libshiboken6`. O `.spec` atual não coleta explicitamente todos os arquivos do pacote `shiboken6` e o build não valida essa pasta.

A V129 adiciona `collect_all("shiboken6")` às bibliotecas, dados e imports ocultos do PyInstaller. Após a etapa `COLLECT`, o próprio `.spec` exige que `shiboken6/libshiboken6` exista e contenha arquivos. Se a pasta estiver ausente ou vazia, o build Windows falha e não publica outro ZIP inválido.

A alteração fica restrita ao empacotamento Windows. Nenhum workflow é alterado; o trigger de `MonitorDeNoticias.spec` já inicia o build Windows automaticamente.

## Validação

A sintaxe do `.spec` será validada localmente. A confirmação final do empacotamento depende do workflow Windows após o envio para `main`. Não houve commit nem push nesta preparação.
