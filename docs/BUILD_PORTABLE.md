# BUILD PORTABLE — WINDOWS x64 — PASSO 24

## Fonte do novo candidato

- repositório: `tysudess/MONITOR-DE-NOTICAS-PYTHON`
- branch: `migration/python-foundation`
- commit da build: `2c52d9b00e06cb6becb7265371c5d35ab45492f8`
- run: `34794644131`
- workflow: `.github/workflows/pass17-build-portable.yml`
- PyInstaller: onedir
- entry point: `run.py`

## Alteração de empacotamento

O Passo 24 não alterou `src/` nem comportamento funcional.

O `MonitorDeNoticias.spec` deixou de usar `collect_all("PySide6")` no aplicativo principal. Os hooks do PyInstaller agora coletam os módulos Qt alcançados pelos imports reais da aplicação. `pypdfium2` continua com coleta explícita necessária ao motor PDF.

O build log do aplicativo principal confirmou QtCore, QtGui, QtWidgets, QtNetwork, QtMultimedia e QtMultimediaWidgets. O helper Globoplay é construído separadamente e continua coletando seus imports reais de QtWebEngine.

## Processo efetivamente usado

`scripts/build_portable.ps1`:

1. limpa build/dist/staging relevantes;
2. instala dependências declaradas;
3. gera `GloboplayLoginHelper.exe`;
4. executa PyInstaller onedir;
5. prepara resources e diretórios graváveis;
6. baixa yt-dlp nightly/stable, Deno, FFmpeg e FFprobe;
7. executa `scripts/collect_portable_licenses.py`;
8. copia/coleta textos oficiais de licenças das distribuições Python instaladas;
9. inclui textos oficiais externos declarados para FFmpeg, yt-dlp e Deno;
10. grava `licenses/` e `LICENSES-MANIFEST.json`;
11. grava BUILD-INFO/BUILD-SHA;
12. valida estrutura Qt/compliance;
13. executa smoke local completo;
14. limpa estado artificial;
15. cria ZIP e SHA-256.

## Estrutura de compliance

```text
MonitorDeNoticias/
├── MonitorDeNoticias.exe
├── _internal/
├── bin/
├── resources/
├── licenses/
│   ├── python-runtime/
│   ├── python/
│   ├── ffmpeg/
│   ├── yt-dlp-stable/
│   ├── yt-dlp-nightly/
│   └── deno/
├── LICENSES-MANIFEST.json
├── THIRD_PARTY_NOTICES.txt
├── BUILD-INFO.json
└── BUILD-SHA.txt
```

A build registrou 45 arquivos em `licenses/`.

## Versões

- Python 3.12.10
- PySide6 6.9.1
- Qt 6.9.1
- PyInstaller 6.15.0
- yt-dlp nightly 2026.08.30.232658
- yt-dlp stable 2026.08.19
- Deno 2.9.6
- FFmpeg/FFprobe n9.0.1-29-gad500d59cb-20260913

## Artefato

- nome: `MONITOR-DE-NOTICIAS-PYTHON-portable-windows-x64.zip`
- tamanho: `477381768` bytes
- descompactado: `830499134` bytes
- SHA-256: `36e161e4ce27103b6668a4471fe381b03ec28c1b6231a9fd137fa2672cfd9ede`
- BUILD-SHA: `2c52d9b00e06cb6becb7265371c5d35ab45492f8`

## Validação

Run `34794644131`: SUCCESS. Suíte 149/149, smoke local PASS e segundo runner completo PASS.

Run de verificação física de compliance `34795191703`: SUCCESS. O mesmo ZIP teve SHA/tamanho confirmados e apresentou THIRD_PARTY_NOTICES, LICENSES-MANIFEST e 45 arquivos legíveis em `licenses/`.

## Estado

O processo de build/compliance está comprovado e o novo ZIP é tecnicamente válido. A aptidão para publicação permanece separada: PUB-001 continua bloqueado pelas obrigações de redistribuição ainda não demonstradas integralmente, conforme `docs/PUBLICATION_COMPLIANCE.md`.
