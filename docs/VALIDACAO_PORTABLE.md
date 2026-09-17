# VALIDAÇÃO PORTABLE — PASSO 24

## Novo candidato

- commit: `2c52d9b00e06cb6becb7265371c5d35ab45492f8`
- workflow: `Passo 17 - Windows Portable`
- run: `34794644131`
- conclusão: `success`
- ZIP: `MONITOR-DE-NOTICIAS-PYTHON-portable-windows-x64.zip`
- tamanho ZIP: `477381768` bytes
- tamanho descompactado: `830499134` bytes
- SHA-256 build: `36e161e4ce27103b6668a4471fe381b03ec28c1b6231a9fd137fa2672cfd9ede`
- SHA-256 segundo runner: `36e161e4ce27103b6668a4471fe381b03ec28c1b6231a9fd137fa2672cfd9ede`
- hashes idênticos: SIM

O candidato funcional anterior `0f9ec957...` / SHA `259739899...` permanece histórico e não deve ser confundido com este novo ZIP.

## Suíte pré-build

- TOTAL: 149
- PASS: 149
- FAIL: 0
- ERROR: 0
- SKIP: 0
- XFAIL: 0

## Build limpa

Worktree limpa e commit congelado foram comprovados antes do build. O processo foi executado do zero no Windows Server 2025 com Python 3.12.10, PySide6/Qt 6.9.1 e PyInstaller 6.15.0.

O novo build adicionou 45 arquivos de licença/notice, `LICENSES-MANIFEST.json` e THIRD_PARTY_NOTICES rastreável antes da criação do ZIP.

Smoke local: PASS.

## Segundo runner independente

O job `validate-zip-without-repository` recebeu somente o novo ZIP, sem checkout de desenvolvimento.

- Windows: Microsoft Windows NT 10.0.26100.0
- AMD64
- FFmpeg global: ausente
- FFprobe global: ausente
- hash: idêntico
- reextração: PASS
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
- segredos reais: 0
- dados pessoais evidentes no ZIP: 0

Primeiro smoke:
`PORTABLE_RUNTIME_SMOKE_OK label=original player=325 codec=h264 audio=aac resolution=320x240 fps=25 duration=1.28 sample_rate=44100 channels=1`

Segundo smoke após movimentação:
`PORTABLE_RUNTIME_SMOKE_OK label=moved player=325 codec=h264 audio=aac resolution=320x240 fps=25 duration=1.28 sample_rate=44100 channels=1`

Os smokes confirmaram páginas do Monitor, banco/persistência, notícias, deduplicação, vídeos, automação, Extrator, PDF, Editor de Vídeo, preview/play-pause, seek, FFmpeg, FFprobe, exportação, DPAPI, proxy, startup e notificação/wiring.

PORT-001, PORT-002, PORT-003, PORT-004 e PORT-005 permanecem RESOLVIDOS.

## Verificação independente do compliance físico

Workflow `Passo 24 - Verify Portable Compliance`, run `34795191703`: PASS.

Esse Windows recebeu o artifact exato do run `34794644131`, confirmou SHA/tamanho, extraiu o ZIP e verificou:

- THIRD_PARTY_NOTICES: PASS
- `licenses/`: PASS
- LICENSES-MANIFEST: PASS
- arquivos de licença/notice: 45
- legibilidade: PASS
- paths/dados locais nos textos adicionados: 0

## Estado de publicação

A validação técnica do novo ZIP e a presença dos textos/notices não equivalem, por si só, à conclusão jurídica de redistribuição. `docs/PUBLICATION_COMPLIANCE.md` registra o bloqueador restante do PUB-001 relacionado ao código-fonte correspondente da build GPL do FFmpeg e à correspondência exata de alguns agregados de terceiros.

## Conclusão

**NOVO ZIP TÉCNICO VALIDADO**

**PUBLICAÇÃO: BLOQUEADA POR PUB-001**
