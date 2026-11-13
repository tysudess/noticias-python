# V142 — correção do teste de validação do runtime

**Base verificada:** `main` em `225630074beafd5505a61d442b081f75f811d7a4` (13/11/2026).

## Causa da falha

Os builds de Windows (run 316) e Ubuntu Portable (run 117) chegaram à etapa de testes unitários e falharam no teste `test_runtime_alias_points_to_v12520`, em `tests/unit/test_v92_uol_completeness.py`.

Esse teste exigia que o alias `extrator-materia-v1.25.10-runtime.js` apontasse especificamente para `extrator-materia-v1.25.20-runtime.js`. A correção V141 atualizou o alias para `extrator-materia-v1.25.22-runtime.js`, portanto a expectativa fixa ficou desatualizada.

## Correção

O teste foi ajustado para validar o contrato real do alias: ele deve conter um `require` versionado válido e o arquivo apontado deve existir. Os testes de integridade específicos do runtime UOL v1.25.20 foram preservados sem alteração.

## Arquivo incluído

- `tests/unit/test_v92_uol_completeness.py`

O pacote contém somente o arquivo de teste que precisa ser atualizado, mantendo o caminho original do repositório. Nenhum arquivo foi alterado diretamente no GitHub.

## Aplicação

Extraia o ZIP na raiz do repositório, mantendo a estrutura de diretórios, e envie apenas o arquivo indicado acima para o GitHub. Depois execute novamente os workflows Windows Portable e Ubuntu Portable.

## Validação local realizada

- Verificação sintática Python (`py_compile`).
- Teste isolado do novo contrato do alias com o alias V141 e o runtime V1.25.22.
- Integridade do ZIP (`unzip -t`).

A execução completa dos workflows oficiais ainda depende do novo commit no GitHub.
