# V38.1 — Correção do Rebuild Planilhas Runtime

## Erro corrigido

O workflow Windows falhava em:

`Patch do motor incompatível: trecho não encontrado (group id normalization)`

O trecho existe no `engine/index.js`, mas o runner Windows pode entregar o
arquivo com finais de linha CRLF (`\r\n`). O script de patch procurava blocos
literais com LF (`\n`), então `engine.includes(oldText)` retornava falso.

## Correção

`patch-whatsapp-web.js` agora normaliza finais de linha para LF antes de todas
as substituições, tanto no:

- `node_modules/whatsapp-web.js/src/Client.js`
- `tools/planilhas_runtime_source/engine/index.js`

Também normaliza os textos usados por `replaceOnce()` e
`replaceEngineOnce()`, deixando o hotfix resistente a LF/CRLF.

## Arquivo a substituir

- `tools/planilhas_runtime_source/scripts/patch-whatsapp-web.js`

## Workflow

NÃO altere `rebuild-planilhas-runtime.yml`.

Depois de subir este arquivo, execute novamente o workflow existente:

`Rebuild Planilhas Runtime`

O passo `Aplicar hotfix de navegação do WhatsApp Web` deve passar pelo ponto
`group id normalization` e continuar aplicando as correções V37/V38.
