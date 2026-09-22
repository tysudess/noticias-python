# V35 — Capas: Valor Gmail primeiro + FrontPages + Proxy Geral

## Ordem do Valor preservada
1. Gmail / Apps Script (`valor_manifest` / `valor_pdf`)
2. Somente se Gmail não fornecer a Página 1: FrontPages
3. Se necessário: navegador interno / PressReader

A V35 NÃO pula o Gmail.

## Problema encontrado no FrontPages
A interface mostrou URLs como:

`...valor-economico-....webp.jpg`
`...the-washington-post-....webp.jpg`

Esse endereço inválido termina em HTTP 404.

A V35:
- normaliza `.webp.jpg` para `.webp`;
- tenta `.webp`, `.jpg`, `.jpeg` e `.png` da mesma capa;
- mantém rejeição da edição SPORTS do Washington Post;
- continua usando o Proxy Geral para os downloads.

## Diagnóstico do Proxy
Se a consulta do Gmail retornar 407, agora o programa NÃO trata isso como
"PDF ausente". Ele mostra claramente que o Proxy Geral recusou autenticação.

Se o Gmail retornar HTTP 404, o programa informa que a implantação do Apps
Script não possui o endpoint de PDF do Valor e só então usa o fallback web.

## Arquivo a substituir
- `src/monitor_noticias/ui/covers_web_proxy_patch.py`

## Workflow
NÃO precisa alterar workflow.
NÃO precisa executar Rebuild Planilhas Runtime.

É alteração do Python do Central. Basta subir o arquivo e gerar novamente
o portable normal do Central.
