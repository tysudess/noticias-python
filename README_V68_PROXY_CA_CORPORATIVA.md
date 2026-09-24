# V68 — Proxy corporativo com certificado CA personalizado

## Por que a V66 não resolveu neste computador?

A V66 passou a usar o trust store nativo do Windows/Ubuntu.

O erro continuou:

`CERTIFICATE_VERIFY_FAILED`

Isso indica que a CA raiz usada pelo proxy de inspeção HTTPS não está
instalada/confiável no sistema operacional desse computador.

## O que a V68 adiciona

Na janela de configuração do Proxy Geral:

- Mostrar/Ocultar senha;
- status da CA corporativa;
- botão `Importar CA`;
- botão `Remover CA`;
- teste do proxy usando a CA importada.

Formatos aceitos:

- `.cer`
- `.crt`
- `.pem`

O certificado deve ser X.509 PEM ou DER.

## Segurança

A Central NÃO usa `verify=False`.

A validação TLS continua habilitada.

O usuário precisa confirmar explicitamente que deseja confiar no certificado.

Use somente a CA raiz fornecida pela organização/TI.

## Como funciona

A Central normaliza o certificado para PEM e cria um bundle contendo:

1. as CAs públicas padrão do `certifi`;
2. a CA corporativa selecionada.

O bundle é usado explicitamente no teste do Proxy Geral e no cliente de
autenticação do Apps Script.

Também são configuradas:

- `REQUESTS_CA_BUNDLE`
- `SSL_CERT_FILE`

para que outras conexões Python do mesmo processo possam utilizar o mesmo
bundle.

## Arquivos para substituir

- `src/monitor_noticias/platform/tls.py`
- `src/monitor_noticias/networking/proxy.py`
- `src/monitor_noticias/auth/client.py`
- `src/monitor_noticias/ui/login_dialog.py`

## Teste novo

- `tests/unit/test_proxy_custom_ca_v68.py`

## Windows e Ubuntu

A implementação é compartilhada.

## WORKFLOW

NÃO PRECISA ALTERAR.
