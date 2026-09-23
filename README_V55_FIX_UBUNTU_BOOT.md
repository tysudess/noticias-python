# V55 — Correção do boot Ubuntu Portable

## Erro corrigido

O Ubuntu fechava no teste real com:

`ImportError: cannot import name 'PageObject' from 'pypdf.generic'`

A versão atual do projeto usa `pypdf==6.18.0`, e `PageObject` deve ser importado de:

`from pypdf import PageObject`

O `core.py` já fazia isso corretamente. O erro estava somente no novo
`pdf_export_quality_fix.py`.

## Alteração 1

SUBSTITUIR:

`src/monitor_noticias/ui/pdf_export_quality_fix.py`

Mudança:

Antes:
`PageObject` vinha de `pypdf.generic`.

Agora:
`PageObject` vem de `pypdf`.

Nenhuma lógica de qualidade do PDF foi alterada.

## Alteração 2

SUBSTITUIR:

`scripts/pyi_runtime_linux_validation.py`

O smoke test agora importa também:

`monitor_noticias.ui.pdf_export_quality_fix`

Assim erros de import desse módulo são detectados antes do boot real da interface.

## Workflow

NÃO PRECISA ALTERAR o `build-ubuntu.yml`.

Como os arquivos estão em `src/**` e `scripts/**`, o workflow Ubuntu atual
já será disparado automaticamente ao subir esta correção.
