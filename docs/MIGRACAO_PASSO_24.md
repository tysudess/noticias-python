# MIGRAÇÃO — PASSO 24

## Objetivo

Fechar PUB-001 exclusivamente por mudanças de empacotamento/compliance, gerar novo candidato e repetir o ciclo técnico integral sem alterar código funcional.

## Referência anterior

- commit portable funcional: `0f9ec957b3e9f3fdf9b02f5dbe9bb0836310d60d`
- run: `34776048157`
- ZIP: `MONITOR-DE-NOTICIAS-PYTHON-portable-windows-x64.zip`
- SHA-256: `259739899fe044157d350ab077d877ef8dd9e024cd33939266e026e8df3563f4`

## Mudanças do Passo 24

Código funcional alterado: **NÃO**.

Arquivos de build/compliance criados ou alterados no candidato:

- `MonitorDeNoticias.spec`
- `scripts/build_portable.ps1`
- `scripts/collect_portable_licenses.py`
- `scripts/build_portable_compliance.ps1` (helper de build/compliance não utilizado pelo workflow final)
- `portable/THIRD_PARTY_NOTICES.txt`

Após a build, foi adicionado o workflow independente `.github/workflows/pass24-compliance-verify.yml` somente para verificar fisicamente os arquivos de compliance do artifact já produzido. Ele não entra no ZIP e não muda o commit de origem do artifact.

O aplicativo principal deixou de coletar todo PySide6 indiscriminadamente. PyInstaller passou a seguir os imports reais; o smoke completo foi usado como prova de preservação funcional.

## Novo candidato

- commit da build: `2c52d9b00e06cb6becb7265371c5d35ab45492f8`
- run: `34794644131`
- conclusão: SUCCESS
- ZIP: `MONITOR-DE-NOTICIAS-PYTHON-portable-windows-x64.zip`
- tamanho ZIP: `477381768` bytes
- tamanho descompactado: `830499134` bytes
- SHA build: `36e161e4ce27103b6668a4471fe381b03ec28c1b6231a9fd137fa2672cfd9ede`
- SHA segundo runner: `36e161e4ce27103b6668a4471fe381b03ec28c1b6231a9fd137fa2672cfd9ede`
- hashes idênticos: SIM

## Suíte

149 passed; 0 fail; 0 error; 0 skip; 0 xfail.

## Compliance material incluído

A build gerou 45 arquivos sob `licenses/`, além de `LICENSES-MANIFEST.json` e `THIRD_PARTY_NOTICES.txt`.

Run independente de comprovação física: `34795191703` — SUCCESS.

Esse runner recebeu o artifact exato do run `34794644131`, confirmou SHA/tamanho e registrou:

- PASS24_ONLY_ARTIFACT=YES
- PASS24_THIRD_PARTY_NOTICES=PASS
- PASS24_LICENSES_DIRECTORY=PASS
- PASS24_LICENSES_MANIFEST=PASS
- PASS24_LICENSE_FILE_COUNT=45
- PASS24_LICENSE_FILES_READABLE=PASS
- PASS24_LICENSE_FILES_LOCAL_DATA=0

A primeira tentativa desse verificador, run `34795156944`, falhou antes de inspecionar o ZIP por sintaxe incorreta do próprio gate PowerShell. O gate foi corrigido sem alterar o artifact e a segunda execução passou. Essa falha não é PORT funcional e não invalida o run técnico `34794644131`.

## Validação externa funcional

Segundo Windows independente, sem checkout do repositório:

- SHA idêntico: PASS
- reextração: PASS
- FFmpeg/FFprobe globais ausentes: comprovado
- FFmpeg/FFprobe empacotados: PASS
- primeira execução: PASS
- primeiro smoke: PASS
- reabertura: PASS
- movimentação: PASS
- path com espaços: PASS
- path com acentos: PASS
- CWD diferente: PASS
- segundo smoke: PASS
- shutdown/teardown: PASS
- processos órfãos: 0
- temporários: PASS
- logs: PASS
- segredos reais: 0
- dados pessoais evidentes: 0

Primeiro smoke: player 325 ms; seek 500/1000/1500; H.264/AAC; 320x240; 25 fps; export 1.28s; 44100 Hz mono.

Segundo smoke movido: player 325 ms; mesmos codecs/resolução/fps/export e pipelines aprovados.

Banco, notícias, deduplicação, vídeos, automação, Extrator, PDF, Editor de Vídeo, preview/play-pause, seek, FFmpeg, FFprobe e exportação permaneceram aprovados.

PORT-001 a PORT-005: **RESOLVIDOS**.
MIG-079 a MIG-083: permanecem satisfeitos.

## PUB-002

Permanece **RESOLVIDO**. Segredos reais não tratados = 0.

## PUB-001 — resultado objetivo

O novo ZIP corrige o problema de notices/textos ausentes e elimina a coleta indiscriminada de módulos Qt no aplicativo principal. Contudo o segundo runner também confirmou que o FFmpeg distribuído foi compilado com `--enable-gpl --enable-version3`, `--enable-libx264` e `--enable-libx265`.

O artifact contém `COPYING.GPLv3.txt` e `LICENSE.md`, mas não demonstra a disponibilização do código-fonte correspondente exato da build FFmpeg/BtbN e componentes GPL junto ao canal de distribuição. A documentação oficial do FFmpeg inclui como checklist de compliance a distribuição do source correspondente exatamente aos binários e sua hospedagem junto da distribuição.

Também não existe prova no artifact de que o `THIRD_PARTY_LICENSES` de upstream usado para o yt-dlp nightly corresponde exatamente à build nightly `2026.08.30.232658`.

Logo, pelo critério do Passo 24 de não inventar conclusão jurídica quando uma obrigação permanece não demonstrada:

**PUB-001 — BLOQUEADO**

Licenças/obrigações bloqueadoras restantes: > 0.

## Repositório Kotlin

`tysudess/noticias-monitor` não foi alterado no Passo 24. A branch histórica observada permanece em `e7b5d8eaac68bce6a9785e4da5b8ca5f83c34d2e`.

## Decisão

**NÃO PRONTO PARA MERGE/RELEASE**

Nenhum merge, tag, GitHub Release, instalador ou melhoria foi executado.
