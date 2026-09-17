# PUBLICATION COMPLIANCE — PASSO 26

## Candidato técnico anterior

O portable do Passo 24 permanece o último portable tecnicamente validado:

- commit da build: `2c52d9b00e06cb6becb7265371c5d35ab45492f8`
- run: `34794644131`
- ZIP SHA-256: `36e161e4ce27103b6668a4471fe381b03ec28c1b6231a9fd137fa2672cfd9ede`

Nenhum novo portable foi gerado no Passo 26.

# PUB-001 — LICENÇAS

## FFmpeg / FFprobe GPLv3

### Binary hashes

- `ffmpeg.exe`: `828bef350665c78b76e4bc3597b1714c66d3bd79a642948243e59754dab1878d`
- `ffprobe.exe`: `897cabca3eb2a16be9bf111a9955277ec93a17527aa6c6b108fd07ab182927f6`
- versão: `n9.0.1-29-gad500d59cb-20260913`

### Build

- fornecedor: BtbN/FFmpeg-Builds
- pacote exato: `ffmpeg-n9.0.1-29-gad500d59cb-win64-gpl-9.0.zip`
- pacote histórico SHA-256: `a224a1dbea8b3e4e75ce17e9465a919cc74c9f027021046eaec610e40464bf27`
- build recipe commit: `3e6685eda92f9288c15ac320139622dcedca09a4`
- tag histórica: `autobuild-2026-09-13-14-50`
- configuração efetiva: `--enable-gpl --enable-version3`, sem `--enable-nonfree`, incluindo `libx264` e `libx265`.

A configuração integral está congelada em `compliance/ffmpeg/FFMPEG_BUILD_MANIFEST.md`.

### Source

- FFmpeg source commit: `ad500d59cb6e0126add4fcb95afb4e2557c4292c`
- variante BtbN: branch `release/9.0`
- source tag exata: **NÃO DETERMINADA PELO ARTEFATO/BUILD ANALISADO**
- archive congelado: `FFmpeg-ad500d59cb6e0126add4fcb95afb4e2557c4292c.tar.gz`
- archive SHA-256: `02b4a070afde52755156d3011508bc54e02adf03da0b51d264735ee5efea4a1c`

A ausência de uma tag FFmpeg exata não impede identificar o source, pois o commit completo correspondente foi comprovado e materializado.

### Build scripts e patches

- BtbN scripts commit: `3e6685eda92f9288c15ac320139622dcedca09a4`
- archive SHA-256: `95eb040c960fc4636c1e9505fee7659d41902380a0fa4ca8aaa5458f40166c21`
- scripts históricos preservados integralmente.
- transformação comprovada no recipe x265: inclusão de `<cstdint>` em `json11.cpp` via `sed`.
- patches adicionais comprovados: NENHUM.

### Dependências GPL externas relevantes

- x264 source commit: `0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee`; cache materializado SHA-256 `20aa4369ccaa99e0bab9208f611c3d633ff3c87654d7a673c840510e64777b97`.
- x265 source commit: `116b87573ed0cec20b75ccacd5641bf06f6e57bd`; cache materializado SHA-256 `a0ab07b667e4f65243b1b9d0a2b8d6009a709284a4324b193b93c1b1e9e273e9`.
- demais snapshots obtidos pelo recipe BtbN exato ficam em `dependency-sources/` no pacote; nenhuma versão adicional foi inferida.

### Corresponding Source

- arquivo: `MONITOR-DE-NOTICIAS-FFMPEG-CORRESPONDING-SOURCE-n9.0.1-29-gad500d59cb-20260913.zip`
- tamanho: `4466155388` bytes
- SHA-256: `54a2b6472bfa13b7bdb35ee25f0793461d890e774074eab350e6e9eb812f35eb`
- run de congelamento: `34799419049`
- artifact de trabalho: `PASS26-FFMPEG-CORRESPONDING-SOURCE-FROZEN`, id `10331186435`.
- teste de reextração/integridade: PASS.

### Scan de segredos do source

Gitleaks 8.30.1 registrou 2 findings `generic-api-key`, em `ffmpeg-source/libavfilter/vf_hsvkey.c` e `ffmpeg-source/libavformat/tls_gnutls.c`. Inspeção do source exato classificou ambos como falsos positivos de código-fonte upstream, sem credencial embutida. O marcador `BEGIN PRIVATE KEY` encontrado corresponde a texto exemplificativo do formato PEM em comentário de `libavformat/tls_openssl.c`, não a uma chave privada. Paths locais do workspace encontrados: 0.

**SEGREDOS REAIS NO CORRESPONDING SOURCE = 0**

### Estratégia de distribuição

PUBLICATION TARGET: GitHub Release do projeto.

Na futura publicação serão anexados à mesma GitHub Release:

1. portable Windows;
2. Corresponding Source FFmpeg acima;
3. checksums, conforme o artefato final validado.

Nenhuma URL pública final é inventada antes da Release existir.

## Status PUB-001

A obrigação material pendente identificada no Passo 25 — preparar e congelar o Corresponding Source exato da build BtbN comprovada — foi fechada tecnicamente no Passo 26. O próximo portable ainda precisa incorporar `FFMPEG_SOURCE_INFO.txt`/notices atualizados e passar novamente pela validação completa.

**PUB-001 — PRONTO PARA REVALIDAÇÃO**

Isso NÃO significa pronto para merge/release.

# PUB-002 — SEGREDOS

Permanece **RESOLVIDO**.

- segredos reais não tratados: `0`
- não foi reaberta a auditoria histórica do Passo 23.

# Resultado Passo 26

- código funcional alterado: NÃO
- `src/` alterado: NÃO
- `ffmpeg.exe` alterado: NÃO
- `ffprobe.exe` alterado: NÃO
- comandos FFmpeg alterados: NÃO
- requirements alterados: NÃO
- FFmpeg recompilado: NÃO
- novo portable: NÃO
- merge/tag/release: NÃO

**PUB-001 PRONTO PARA REVALIDAÇÃO**
