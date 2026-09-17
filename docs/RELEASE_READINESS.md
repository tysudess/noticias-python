# RELEASE READINESS — PASSO 26

## Estado técnico

O portable do Passo 24 continua sendo o último portable tecnicamente validado:

- commit da build: `2c52d9b00e06cb6becb7265371c5d35ab45492f8`
- run: `34794644131`
- SHA-256: `36e161e4ce27103b6668a4471fe381b03ec28c1b6231a9fd137fa2672cfd9ede`

Nenhum novo portable foi gerado no Passo 26.

## PUB-001 — LICENÇAS

**STATUS: PRONTO PARA REVALIDAÇÃO**

A cadeia FFmpeg/FFprobe foi congelada:

- binários de referência preservados sem alteração;
- origem BtbN comprovada;
- build recipe commit `3e6685eda92f9288c15ac320139622dcedca09a4`;
- FFmpeg source commit `ad500d59cb6e0126add4fcb95afb4e2557c4292c`;
- x264 commit `0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee`;
- x265 commit `116b87573ed0cec20b75ccacd5641bf06f6e57bd`;
- Corresponding Source final: `MONITOR-DE-NOTICIAS-FFMPEG-CORRESPONDING-SOURCE-n9.0.1-29-gad500d59cb-20260913.zip`;
- tamanho: `4466155388` bytes;
- SHA-256: `54a2b6472bfa13b7bdb35ee25f0793461d890e774074eab350e6e9eb812f35eb`;
- reextração/integridade: PASS;
- segredos reais classificados no source: 0.

O source será anexado à mesma futura GitHub Release que o portable Windows. A URL final ainda não existe e não foi inventada.

O próximo passo deverá gerar um novo portable contendo os materiais de compliance atualizados e executar novamente a validação completa. Portanto **PRONTO PARA REVALIDAÇÃO não significa PRONTO PARA MERGE/RELEASE**.

## PUB-002 — SEGREDOS

**STATUS: RESOLVIDO**

Segredos reais não tratados: `0`.

## Alterações funcionais

- `src/`: NÃO
- `ffmpeg.exe`: NÃO
- `ffprobe.exe`: NÃO
- comandos FFmpeg: NÃO
- requirements: NÃO
- recompilação de FFmpeg: NÃO
- nova build do Monitor: NÃO

## Fonte histórica Kotlin

`tysudess/noticias-monitor` permaneceu inalterado.

## Decisão

**PUB-001 PRONTO PARA REVALIDAÇÃO**

Ainda não executar merge, tag ou release.
