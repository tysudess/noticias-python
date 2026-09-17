# Migração Kotlin → Python

## Fonte da verdade

- Repositório original: `tysudess/noticias-monitor`
- Baseline Kotlin auditada: `df1701ba5427a04954093e8ebed63f26abb2b2b7` + transformações comprovadas do workflow V8.
- Repositório destino: `tysudess/MONITOR-DE-NOTICAS-PYTHON`
- Branch de integração: `migration/python-foundation`.

O comportamento comprovado é a fonte da verdade. Lacunas não são preenchidas por suposição. Quando algo não é comprovado: **NÃO DETERMINADO PELO CÓDIGO ANALISADO.**

## Estados permitidos

`PENDENTE`, `EM MIGRAÇÃO`, `EM TESTE`, `APROVADO`, `BLOQUEADO`.

`APROVADO` significa equivalência objetiva dentro do escopo explícito do MIG.

## Histórico de gates

- Passo 13: auditoria estrutural e reabertura de lacunas de wiring/runtime.
- Passo 14: composition root/runtime real e smokes controlados/live.
- Passo 15: gate encontrou bloqueadores altos de helper/lifecycle/mídia.
- Passo 16: eliminou esses bloqueadores; decisão `APTO PARA PORTABLE`.
- Passos 18–19: build/validação revelou e tratou `PORT-001` a `PORT-004`.
- Passo 20: candidato `186a28e4...` falhou no segundo smoke por `PORT-005`, classificado como falha do gate.
- Passo 21: corrigiu somente o gate, preservou deduplicação/AutomationService e concluiu o ciclo externo integralmente no commit `0f9ec957b3e9f3fdf9b02f5dbe9bb0836310d60d`, run `34776048157`.

## Portable validado

- ZIP: `MONITOR-DE-NOTICIAS-PYTHON-portable-windows-x64.zip`
- tamanho: `651329315` bytes
- descompactado: `1262862742` bytes
- SHA-256: `259739899fe044157d350ab077d877ef8dd9e024cd33939266e026e8df3563f4`
- plataforma: Windows Server 2025 / NT 10.0.26100 / AMD64
- suíte: 149/149
- dois smokes congelados: PASS
- movimentação/path espaço/acento: PASS
- shutdown/órfãos/temp: PASS
- segredos/dados pessoais no artefato: 0

## Promoções objetivas do Passo 22

| MIG | Funcionalidade | Status antes | Evidência final | Status depois |
|---|---|---|---|---|
| MIG-002 | Resolução de raiz portable | PENDENTE | `sys.frozen` real, CWD externo, reextração e movimentação com espaços/acentos | APROVADO |
| MIG-079 | Entrada Desktop original | PENDENTE | EXE real inicia e percorre a aplicação no pacote final | APROVADO |
| MIG-080 | Transformações workflow | PENDENTE | workflow/build final produziu o candidato e passou segundo runner | APROVADO |
| MIG-081 | PyInstaller editor/aplicação | PENDENTE | Editor integrado abre e executa preview/seek/export no runtime congelado | APROVADO |
| MIG-082 | Cinco binários portáteis | PENDENTE | yt-dlp nightly/stable, Deno, FFmpeg e FFprobe presentes; FFmpeg/FFprobe executados sem globais | APROVADO |
| MIG-083 | BUILD-SHA/hash ZIP | PENDENTE | BUILD-SHA aponta para `0f9ec957b3e9f3fdf9b02f5dbe9bb0836310d60d` e hash foi recalculado idêntico no segundo runner | APROVADO |

Nenhum MIG é promovido apenas por associação.

## Contagem consolidada

- Total: **116 MIGs**
- `APROVADO`: **77**
- `EM TESTE`: **37**
- `PENDENTE`: **2** (`MIG-061`, `MIG-114`)
- `BLOQUEADO`: **0**

### MIGs ainda EM TESTE

`MIG-003`, `MIG-004`, `MIG-022`, `MIG-027`, `MIG-028`, `MIG-033`, `MIG-039`, `MIG-040`, `MIG-042`, `MIG-044`, `MIG-047`, `MIG-048`, `MIG-049`, `MIG-051`, `MIG-052`, `MIG-053`, `MIG-054`, `MIG-055`, `MIG-057`, `MIG-068`, `MIG-069`, `MIG-090`, `MIG-091`, `MIG-092`, `MIG-093`, `MIG-094`, `MIG-095`, `MIG-096`, `MIG-097`, `MIG-098`, `MIG-099`, `MIG-100`, `MIG-102`, `MIG-103`, `MIG-106`, `MIG-108`, `MIG-110`.

Esses estados não são promovidos em massa pelo sucesso do portable; seus critérios mais amplos continuam conservadoramente separados.

## PORT-001 a PORT-005

Todos estão **RESOLVIDOS**. Histórico detalhado em `docs/MIGRACAO_PASSO_21.md`.

## Repositório Kotlin

A branch original observada permanece em `e7b5d8eaac68bce6a9785e4da5b8ca5f83c34d2e`. A fonte funcional continua `df1701ba5427a04954093e8ebed63f26abb2b2b7` + workflow V8. O repositório original não foi alterado pelo Passo 22.

## Decisão técnica atual

**PORTABLE VALIDADO**
