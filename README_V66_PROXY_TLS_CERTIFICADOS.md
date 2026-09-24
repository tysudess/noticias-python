# V66 — Proxy HTTPS / certificados corporativos

## Sintoma

Windows e Ubuntu apresentavam:

`SSL: CERTIFICATE_VERIFY_FAILED`

`unable to get local issuer certificate`

ao testar o Proxy Geral.

## Causa

O `requests` usa por padrão um bundle próprio de certificados.
Em redes corporativas que inspecionam HTTPS, a CA raiz da organização costuma
estar instalada no Windows/Ubuntu, mas não no bundle interno usado pelo Python.

O proxy estava acessível. A falha acontecia na validação do certificado HTTPS.

## Correção

A Central agora usa `truststore` para integrar Python/Requests ao repositório
nativo de certificados confiáveis do sistema.

Windows:
- Windows Certificate Store.

Ubuntu/Linux:
- trust store/OpenSSL do sistema.

A ativação ocorre duas vezes de forma idempotente:

1. runtime hook do PyInstaller, antes dos imports normais;
2. inicialização de `Application`, também para execução via Python-fonte.

## Segurança

NÃO foi usado `verify=False`.

A validação HTTPS continua ativa.

Se o teste continuar falhando depois desta V66, isso significa que a CA raiz
corporativa não está instalada/confiável no próprio sistema operacional.
Nesse caso a mensagem da Central passa a explicar isso claramente.

## Arquivos NOVOS

- `src/monitor_noticias/platform/tls.py`
- `scripts/pyi_runtime_system_trust.py`
- `tests/unit/test_system_trust_v66.py`

## SUBSTITUIR

- `src/monitor_noticias/networking/proxy.py`
- `src/monitor_noticias/app/application.py`
- `requirements.txt`
- `pyproject.toml`
- `MonitorDeNoticias.spec`
- `MonitorDeNoticias-Linux.spec`
- `scripts/pyi_runtime_linux_validation.py`

## Windows e Ubuntu

A correção é compartilhada e foi preparada para os dois builds.

## WORKFLOW

NÃO PRECISA ALTERAR.

Os workflows existentes já:
- instalam `requirements.txt`;
- compilam os respectivos `.spec`;
- são acionados por alterações em `src/**`, requirements/spec/scripts.
