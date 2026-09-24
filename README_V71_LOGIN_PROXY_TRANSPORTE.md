# V71 — Login via proxy corporativo no Ubuntu/Windows

## Situação confirmada

O Ubuntu Portable Build 30 já contém a V69 e já mostra:

`Compatibilidade SSL corporativa`

Portanto o erro atual não é mais `CERTIFICATE_VERIFY_FAILED`.

O problema seguinte acontece no transporte do login por POST.

## Correções

### 1. Sessão dedicada

Quando o Proxy Geral está ativo, o cliente de autenticação agora usa:

`requests.Session().trust_env = False`

Assim não herda `HTTP_PROXY`, `HTTPS_PROXY` ou `NO_PROXY` do Ubuntu/Windows.

A única rota usada é o Proxy Geral configurado na Central.

### 2. POST compatível com filtro corporativo

O corpo continua sendo JSON, mas é enviado como:

`Content-Type: text/plain; charset=utf-8`

Isso é compatível com o Apps Script atual porque o servidor faz:

`JSON.parse(e.postData.contents)`

A senha continua no corpo da requisição, nunca na URL.

### 3. Teste real do caminho de login

O botão `Testar` do Proxy Geral agora verifica:

1. conexão com proxy;
2. GET do Apps Script;
3. POST real para `doPost()` sem usar senha real.

O POST de teste envia uma ação inexistente e espera a resposta
`UNKNOWN_ACTION`, provando que o mesmo canal usado pelo login está acessível.

### 4. Diagnóstico HTTP

Agora a interface diferencia:

- HTTP 407: usuário/senha do proxy recusados;
- HTTP 401/403: acesso bloqueado;
- HTTP 429: limite temporário;
- HTTP 5xx: proxy/servidor indisponível;
- timeout;
- ProxyError;
- SSL;
- demais erros de rede.

A senha do proxy é removida dos detalhes antes de exibir erro.

## Substituir

- `src/monitor_noticias/auth/client.py`
- `src/monitor_noticias/ui/login_dialog.py`

## Adicionar

- `tests/unit/test_auth_proxy_transport_v71.py`

## Apps Script

NÃO precisa alterar nem reimplantar o Code.gs para esta V71.

## Windows e Ubuntu

A correção é compartilhada.

## WORKFLOW

NÃO PRECISA ALTERAR.
