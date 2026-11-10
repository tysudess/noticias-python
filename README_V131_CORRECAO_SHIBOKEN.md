# V131 — Correção da validação e teste do Shiboken no Windows Portable

Base: `tysudess/noticias-python`, branch `main`, commit `eb2b2c365f3f5e0b52dd2fcd27c9597a9468405a` (V130).

## Arquivo

**SUBSTITUIR** `MonitorDeNoticias.spec` na raiz do repositório.

## O que foi corrigido

A execução #297 falhou na validação adicionada pela V130. O teste procurava `shiboken6/libshiboken6`, mas o PySide6 6.9.1 procura o pacote `shiboken6` diretamente ao lado da pasta `PySide6` no diretório de conteúdo do aplicativo. A pasta `libshiboken6` não é um requisito do layout padrão de instalação do wheel.

A V131:

- Procura `PySide6` e `shiboken6` no layout onedir do PyInstaller 6.x (`_internal`), mantendo fallback para layout na raiz.
- Confere a existência do pacote `shiboken6`, de módulos Python nativos `.pyd` e de DLLs.
- Executa um teste de importação de `shiboken6` e dos módulos QtCore, QtGui e QtWidgets usando exclusivamente a pasta coletada no portable. Assim, o build não depende de um Shiboken instalado no `site-packages` do runner para passar no teste.
- Mantém a validação existente do executável PyInstaller e do CArchive.

## Escopo

Somente `MonitorDeNoticias.spec` é alterado. Não é necessário modificar o workflow nem o build Ubuntu.

## Validação

A sintaxe do arquivo e o empacotamento ZIP foram verificados localmente. O teste real de importação depende da execução no runner Windows do GitHub Actions. O pacote não foi publicado automaticamente no GitHub.
