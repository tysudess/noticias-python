# V69 — SSL compatível somente no proxy corporativo

A validação HTTPS é desativada SOMENTE quando o Proxy Geral estiver:

- ativo;
- host `proxy-7dn.mb`;
- porta `6060`.

Qualquer conexão direta ou outro proxy continua validando certificados.

Também corrige:

`module 'requests' has no attribute 'ProxyError'`

usando `requests.exceptions.ProxyError`.

## Substituir

- `src/monitor_noticias/networking/proxy.py`
- `src/monitor_noticias/auth/client.py`
- `src/monitor_noticias/ui/login_dialog.py`

## Novo teste

- `tests/unit/test_corporate_proxy_tls_v69.py`

## Windows e Ubuntu

A alteração é compartilhada.

## WORKFLOW

NÃO PRECISA ALTERAR.
