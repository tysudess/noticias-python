# V34 — Padrões da Automação + scroll + proxy removido da interface

## Alterações

1. Apps Script padrão:
https://script.google.com/macros/s/AKfycbz9zWPX0OgVa7obrmqm5WSu1fImaTiyWz0pR3wuc13xl-uCS5KYTF4rhbRitrv26PBh/exec

2. Grupos padrão:
- 556191047689-1555547406@g.us
- 120363025807487932@g.us
- 556192528699-1447447254@g.us

3. Se o `config.json` existente vier com `appsScriptUrl` vazio ou `grupos: []`,
   a própria interface restaura e SALVA automaticamente os valores padrão.

4. A seção de Proxy foi removida da Automação de Planilhas.
   O proxy continua funcionando por trás através de `CENTRAL_PROXY_*`,
   fornecido pelo Proxy Geral da Central.

5. O item "Proxy" também foi retirado do Resumo Geral do painel.

6. A aba Configurações recebeu um scroll vertical dedicado e sempre visível.

## Arquivos a substituir
- tools/planilhas_runtime_source/renderer/renderer.js
- tools/planilhas_runtime_source/renderer/index.html
- tools/planilhas_runtime_source/renderer/style.css
- tools/planilhas_runtime_source/config.json

## Workflow
NÃO precisa alterar o workflow.

Mas esta alteração é no runtime Electron, portanto depois de subir os arquivos
é necessário executar o workflow existente:

`Rebuild Planilhas Runtime`

Ele atualizará:
`AutomacaoPlanilhas-Windows-Portable-v1.0.4.exe`

na tag:
`planilhas-runtime-v1.0.4`

Depois disso, gere novamente o portable normal do Central para ele baixar o
runtime atualizado.
