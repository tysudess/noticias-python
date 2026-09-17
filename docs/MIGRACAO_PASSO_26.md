# MIGRAÇÃO — PASSO 26 — CORRESPONDING SOURCE FFMPEG

## Objetivo

Materializar e congelar o Corresponding Source exato da build BtbN já comprovada, sem alterar binários, comandos ou código funcional.

## Referências congeladas

- `ffmpeg.exe` SHA-256: `828bef350665c78b76e4bc3597b1714c66d3bd79a642948243e59754dab1878d`
- `ffprobe.exe` SHA-256: `897cabca3eb2a16be9bf111a9955277ec93a17527aa6c6b108fd07ab182927f6`
- versão: `n9.0.1-29-gad500d59cb-20260913`
- BtbN build recipe: `3e6685eda92f9288c15ac320139622dcedca09a4`
- tag histórica BtbN: `autobuild-2026-09-13-14-50`
- FFmpeg source commit: `ad500d59cb6e0126add4fcb95afb4e2557c4292c`
- x264: `0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee`
- x265: `116b87573ed0cec20b75ccacd5641bf06f6e57bd`

## Materialização anterior reaproveitada

Run Passo 25: `34796686400`.

Inner source ZIP conferido novamente:

- SHA-256: `3b9701a0fbcfb5a3270a1a305ee60d14ab3b03ee023eab931f2e4b7a6f22b4e7`
- tamanho: `4430881089` bytes.

A árvore continha `ffmpeg-source/`, `build-recipe/`, `dependency-sources/` e `SOURCE-PROVENANCE.txt`. Os commits FFmpeg/BtbN/x264/x265 foram conferidos antes do congelamento final.

## Gate Passo 26

Primeiro gate: falha operacional por caminho relativo usado com `git -C ... archive -o`; nenhum source/binário divergiu e nenhum resultado parcial foi aceito.

Gate corrigido:

- workflow: `Passo 26 - Freeze FFmpeg Corresponding Source v2`
- run: `34799419049`
- commit do gate: `59289721f987570c062cdc0bcbbecfebba3c4fc3`
- resultado: SUCCESS

Resultados:

- identidades de referência: PASS
- árvore: `10950` arquivos, `4462017668` bytes
- integridade pré-pacote: PASS
- archive FFmpeg SHA-256: `02b4a070afde52755156d3011508bc54e02adf03da0b51d264735ee5efea4a1c`
- archive BtbN scripts SHA-256: `95eb040c960fc4636c1e9505fee7659d41902380a0fa4ca8aaa5458f40166c21`
- cache x264 SHA-256: `20aa4369ccaa99e0bab9208f611c3d633ff3c87654d7a673c840510e64777b97`
- cache x265 SHA-256: `a0ab07b667e4f65243b1b9d0a2b8d6009a709284a4324b193b93c1b1e9e273e9`

## Pacote final

- arquivo: `MONITOR-DE-NOTICIAS-FFMPEG-CORRESPONDING-SOURCE-n9.0.1-29-gad500d59cb-20260913.zip`
- tamanho: `4466155388` bytes
- SHA-256: `54a2b6472bfa13b7bdb35ee25f0793461d890e774074eab350e6e9eb812f35eb`
- reextração + hashes internos: PASS
- artifact de trabalho: `PASS26-FFMPEG-CORRESPONDING-SOURCE-FROZEN`, id `10331186435`

O digest do wrapper Actions (`47adf144...`) não é o SHA-256 do ZIP interno e não o substitui.

## Scan de segredos

Gitleaks `8.30.1`:

- findings: 2
- regra: `generic-api-key`
- arquivos: `ffmpeg-source/libavfilter/vf_hsvkey.c`, `ffmpeg-source/libavformat/tls_gnutls.c`
- classificação: falsos positivos de código-fonte upstream; segredos reais = 0.
- marcador `BEGIN PRIVATE KEY`: texto exemplificativo de PEM em comentário de `libavformat/tls_openssl.c`; chave real = 0.
- paths locais do workspace: 0.

## Alterações funcionais

- `src/`: NÃO
- `ffmpeg.exe`: NÃO
- `ffprobe.exe`: NÃO
- comandos FFmpeg: NÃO
- requirements: NÃO
- recompilação do FFmpeg: NÃO
- nova build do Monitor: NÃO

## Estratégia futura

Anexar à mesma futura GitHub Release:

1. portable Windows revalidado;
2. Corresponding Source FFmpeg congelado neste passo;
3. checksums.

A URL final não existe e não foi inventada.

## Resultado

**PUB-001 PRONTO PARA REVALIDAÇÃO**

PUB-002 permanece RESOLVIDO; segredos reais não tratados = 0.

Isso não autoriza merge, tag, release ou geração automática de novo portable neste passo.
