# MIGRAÇÃO — PASSO 19

## Objetivo

Corrigir exclusivamente os bloqueadores descobertos na tentativa de validação portable do Passo 18, sem alterar regras de negócio, sem redesign, sem merge e sem release.

## Resultado herdado do Passo 18

O Passo 18 falhou tecnicamente no smoke local do Extrator empacotado. O processo ficava no estado inicial até timeout e, por isso, o ciclo externo não podia ser considerado concluído.

## Bloqueadores tratados

### PORT-001 — lifetime do `_DownloadWorker`

Causa: `ExtractorPage.start_download()` criava o `_DownloadWorker` apenas em variável local enquanto a `QThread` era mantida em atributo. O worker assíncrono não possuía referência Python forte equivalente durante a vida da thread.

Correção: manter referência ao worker até a conclusão da thread e limpar a referência no encerramento.

Evidência: regressão assíncrona adicionada; depois da correção o smoke local do Extrator passou no runtime PyInstaller.

Commit da correção/regressão: `15003c10d95ac00669d71676fb0aa0de01e7aec2`.

### PORT-002 — workflow não refazia portable para mudanças de source

Causa: os filtros do workflow portable não observavam `src/**`, `tests/**`, `run.py` e demais entradas relevantes.

Correção: ampliar apenas o gatilho da workflow para que uma alteração funcional relevante force nova build portable.

Commit: `e8032840f84af2972dfa1b1578622875c06642de`.

### PORT-003 — parser PowerShell no segundo runner

Causa: interpolação `"... $dir: ..."` era sintaticamente inválida em PowerShell.

Correção: usar `${dir}:`.

Commit: `73a029fac3f312e649d76d35d75a5ad944658fd2`.

A correção não alterou o programa; alterou apenas o harness de validação.

### PORT-004 — fixture do Extrator reutilizada no segundo smoke

Causa: o primeiro smoke deixava o download artificial `extractor_fixture` em `Videos/`. Depois de mover a mesma pasta, o segundo smoke entregava novamente a mesma fixture. O motor, corretamente, não considerava um arquivo já existente como novo download e o gate falhava.

Correção: antes de cada smoke, remover somente `*extractor_fixture*` em `Videos/`.

Não há limpeza geral de downloads nem mudança no `ExtractorEngine`.

Commit/candidato resultante: `186a28e4a5f53296178fd9d0ee74637a8a5149bf`.

## Estado ao encerrar o Passo 19

- PORT-001: CORRIGIDO
- PORT-002: CORRIGIDO
- PORT-003: CORRIGIDO
- PORT-004: CORRIGIDO NO GATE
- candidato correto: `186a28e4a5f53296178fd9d0ee74637a8a5149bf`
- run iniciado: `34768584764`
- estado conhecido no encerramento: build clean portable em execução

O Passo 19 não declarou o portable validado porque a validação externa desse candidato ainda não havia terminado.

## Restrições preservadas

- repositório Kotlin não foi modificado;
- nenhum merge;
- nenhum release;
- nenhum instalador;
- nenhuma alteração de regra de negócio;
- cada correção invalidou o ZIP anterior e exigiu novo candidato/hash.

## Conclusão do Passo 19

**PORTABLE NÃO VALIDADO — VALIDAÇÃO EXTERNA PENDENTE**
