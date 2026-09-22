# V31 — Extrator de Matérias usando o Proxy Geral

## Causa encontrada
O Central abria o Extrator de Matérias com `MONITOR_HEADLESS=1`, mas não
repassava o Proxy Geral. Além disso, `tools/news_extractor/monitor-main.js`
forçava `ATIVADO: false` antes da extração.

## Correção
1. Novo patch `news_extractor_proxy_patch.py` lê o Proxy Geral usando a mesma
   `ProxySettings`/DPAPI do Central.
2. As credenciais são passadas somente por variáveis de ambiente ao QProcess.
3. `monitor-main.js` honra `CENTRAL_PROXY_ENABLED/HOST/PORT/USERNAME/PASSWORD`.
4. O motor existente continua usando `undici.ProxyAgent`.
5. A senha não é gravada em `config-proxy.json`.

## Arquivos
NOVO:
- `src/monitor_noticias/ui/news_extractor_proxy_patch.py`

SUBSTITUIR:
- `src/monitor_noticias/app/application.py`
- `tools/news_extractor/monitor-main.js`

## Workflow
NÃO é necessário alterar workflow.

O workflow `build-portable.yml` já observa:
- `src/**`
- `tools/news_extractor/**`

e já executa `npm run dist` em `tools/news_extractor`, portanto o novo
`ExtratorMateriasPortable-V1.25.19.exe` será reconstruído automaticamente
quando esses arquivos forem enviados à `main`.

## Log esperado com Proxy Geral ativo
REDE: configuração recebida do Proxy Geral do Central
PROXY ATIVO: proxy-7dn.mb:6060
PROXY COM AUTENTICAÇÃO CONFIGURADA
