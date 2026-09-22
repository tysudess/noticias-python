# V32 — Correção de colar na aba Planilhas

## Problema
Quando o Electron da Automação fica incorporado dentro do PySide6,
o Ctrl+V pode não chegar corretamente ao campo Apps Script URL por causa
do foco de teclado da janela estrangeira.

## Correção
- Mantém Ctrl+V nativo.
- Adiciona botão "COLAR DA ÁREA DE TRANSFERÊNCIA".
- O preload usa `electron.clipboard.readText()` e entrega o texto ao renderer.
- Não mexe em proxy, WhatsApp, grupos ou lógica da planilha.

## Arquivos a substituir
- tools/planilhas_runtime_source/preload.js
- tools/planilhas_runtime_source/renderer/renderer.js
- tools/planilhas_runtime_source/renderer/index.html

## Workflow
Não precisa alterar workflow.

Depois de enviar estes arquivos ao GitHub:
1. Rode `Rebuild Planilhas Runtime`.
2. Confirme a atualização do asset `AutomacaoPlanilhas-Windows-Portable-v1.0.4.exe`.
3. Depois gere o portable normal do Central.

## Uso
Na Automação > Configurações:
1. Copie a URL publicada do Apps Script.
2. Clique em `COLAR DA ÁREA DE TRANSFERÊNCIA`.
3. Clique em `SALVAR CONFIGURAÇÕES`.

Observação: o campo espera a URL publicada do Apps Script, não o código-fonte
completo do script.
