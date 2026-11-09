# V130 — Correção da validação do Shiboken no Windows Portable

Base: `tysudess/noticias-python`, branch `main`, commit `da971779f8bb9f817c72ff5c43a768ec2895aba8` (V129).

## Arquivo

**SUBSTITUIR** `MonitorDeNoticias.spec` na raiz do repositório.

## Motivo da falha V129

A execução Windows #295 falhou na etapa **Gerar aplicativo com PyInstaller**. O log mostra que o PyInstaller concluiu a etapa `COLLECT`, mas a verificação acrescentada pela V129 procurou `dist/MonitorDeNoticias/shiboken6/libshiboken6` diretamente na raiz.

O workflow usa PyInstaller 6.15.0. No modo onedir, o PyInstaller 6 coloca o conteúdo da aplicação em `_internal` por padrão. Portanto, a verificação deve aceitar `dist/MonitorDeNoticias/_internal/shiboken6/libshiboken6`. A V130 corrige esse caminho e mantém a busca na raiz como compatibilidade para configurações antigas.

A coleta explícita `collect_all("shiboken6")` da V129 é preservada. O build continuará falhando antes da publicação caso a pasta não seja encontrada em nenhum dos caminhos esperados ou esteja vazia.

## Aplicação

Substituir somente `MonitorDeNoticias.spec` na raiz do repositório e enviar para a branch `main`. O workflow Windows já tem gatilho para esse arquivo. Não é necessário alterar o workflow Ubuntu.

## Validação desta preparação

- Sintaxe Python do `.spec` verificada com `ast.parse`.
- ZIP validado com `zipfile.testzip()`.
- A compilação real do PyInstaller e o teste de inicialização do aplicativo dependem do próximo workflow Windows; não foram executados neste ambiente.
