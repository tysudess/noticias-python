# MIGRAÇÃO — PASSO 16

## Escopo

Eliminar exclusivamente os bloqueadores CRÍTICOS e ALTOS registrados no Passo 15, sem criar portable, instalador, release, merge, redesign ou funcionalidade nova.

- Kotlin/fonte da verdade: `tysudess/noticias-monitor@df1701ba5427a04954093e8ebed63f26abb2b2b7` + transformações comprovadas do workflow V8.
- Python inicial: `tysudess/MONITOR-DE-NOTICAS-PYTHON@5a4fd44f4fc69ee22e82f1cec283d62366d99a48`.
- Branch: `migration/python-foundation`.
- Commit de código do gate final: `c8a53b600faa49105937b194dc74455c0eb13d3a`.

## Tabela inicial dos bloqueadores recebidos

| ID | MIG | Severidade | Módulo | Problema | Comportamento Kotlin | Python antes | Evidência | Correção necessária | Status inicial |
|---|---|---|---|---|---|---|---|---|---|
| B14-01 | MIG-050 | ALTO | Extrator/Globoplay | cadeia do helper/login interno não comprovada | `GloboplayLoginWindow` extrai helper empacotado do resource para runtime e o executa | `ExtractorPage` procurava diretamente o `.exe` no runtime | source Kotlin + helper/build scripts do commit congelado | reproduzir resource→runtime→processo→cookies | BLOQUEADO |
| B15-02 | MIG-116 | ALTO | Lifecycle/Shutdown | ferramentas não participavam do encerramento coordenado | editor distribuído era processo separado; encerrar liberava player/handles | editor é top-level no mesmo processo; Extrator tinha QThreads/processo helper próprios | `MainWindow.exit_application`, `ExtractorPage`, `VideoEditorPage` | coordenar cleanup sem `QThread.terminate()` | BLOQUEADO |
| B15-03 | MIG-070/071/072/074/075/076 | ALTO | Editor de Vídeo/Mídia | execução real não havia sido concluída | motor PySide6 distribuído usa QMediaPlayer e FFmpeg/FFprobe | contratos existiam, porém sem prova real no gate | Passo 15 não tinha FFmpeg/FFprobe no runner | executar o motor existente com ferramentas equivalentes às do workflow | BLOQUEADO |

## B14-01 / MIG-050

**ID:** B14-01  
**SEVERIDADE ORIGINAL:** ALTO  
**MIG:** MIG-050  
**PROBLEMA:** login interno Globoplay sem cadeia de helper comprovada.  
**CAUSA RAIZ:** o Python pulava a materialização que existe em `GloboplayLoginWindow.kt`; procurava diretamente `data/extractor/runtime/GloboplayLoginHelper.exe`.  
**KOTLIN:** carrega `/globoplay-login-helper/GloboplayLoginHelper.exe`, valida tamanho, copia para `data/extractor/runtime/`, executa com `--output` e `--profile-dir`, recebe Netscape cookies e os entrega ao store protegido.  
**PYTHON ANTES:** esperava que o helper já existisse no runtime.  
**CORREÇÃO:** criado `extractor/login_helper.py` com a materialização resource→runtime; `ExtractorPage` passou a chamar esse resolver, rastrear processo/waiter/temp e consumir os cookies retornados. `tools/globoplay-login-helper.py` foi migrado sem alteração.  
**PYTHON DEPOIS:** reproduz a mesma cadeia funcional interna do Kotlin sem fallback para executável externo da máquina.  
**TESTE CRIADO:** materialização; ausência de fallback externo; integração da UI com processo controlado retornando Netscape cookies.  
**RESULTADO:** PASS. O blob do helper Python é `de8839c232e1857bb7b04cd079a5e7eafb755453`, idêntico ao blob no commit Kotlin.  
**STATUS:** RESOLVIDO / MIG-050 APROVADO.

Observação: autenticação humana contra o site do Globoplay não é fabricada em teste. O pipeline interno foi comprovado e o helper source é byte a byte igual ao original. A geração física do `.exe` é uma dependência da futura etapa de build.

## B15-02 / MIG-116

**ID:** B15-02  
**SEVERIDADE ORIGINAL:** ALTO  
**MIG:** MIG-116  
**PROBLEMA:** `Sair` não coordenava QThreads/processos auxiliares/janelas top-level.  
**CAUSA RAIZ:** diferença arquitetural deliberada do Passo 12: o editor Kotlin/release era processo separado; no Python passou a ser janela top-level no processo do Monitor. O Extrator também tinha workers/processo de login que `MainWindow` não conhecia.  
**KOTLIN:** término do processo separado do editor liberava player/handles; Extrator utilizava lifecycle da tela/coroutine e processo auxiliar conhecido.  
**PYTHON ANTES:** `MainWindow.exit_application()` fechava controller/tray sem chamar cleanup das páginas de ferramentas.  
**CORREÇÃO:** `ExtractorPage.shutdown()` cancela motor/process tree, destrói helper rastreado, espera QThreads e recusa saída se não terminarem; `VideoEditorPage.shutdown()` para `QMediaPlayer`, limpa a source, fecha a janela com `WA_DeleteOnClose`; `MainWindow` chama ambos antes de `controller.close()`.  
**PYTHON DEPOIS:** a aplicação não se declara encerrada enquanto os workers conhecidos não estiverem limpos. Não é usado `QThread.terminate()`.  
**TESTE CRIADO:** janela real do editor é aberta e fechada; processo filho real de 30 s é rastreado pelo Extrator e comprovadamente terminado; contrato da ordem de shutdown da MainWindow.  
**RESULTADO:** PASS. O primeiro smoke real ainda detectou handle do vídeo preso após `player.stop()`; essa reprodução levou à correção adicional `player.setSource(QUrl())`, e o smoke final remove o temporário normalmente.  
**STATUS:** RESOLVIDO / MIG-116 APROVADO.

## B15-03 / mídia real

**ID:** B15-03  
**SEVERIDADE ORIGINAL:** ALTO  
**MIG:** MIG-070, MIG-071, MIG-072, MIG-074, MIG-075, MIG-076  
**PROBLEMA:** FFprobe, preview, áudio, seek, play/pause e exportação não tinham execução real no Passo 15.  
**CAUSA RAIZ:** o runner Windows usado inicialmente não possuía FFmpeg/FFprobe no PATH; não era falha do motor.  
**KOTLIN:** `video_editor_pyside/main.py` usa QMediaPlayer/QVideoWidget/QAudioOutput e o comando FFmpeg exato da release.  
**PYTHON ANTES:** o mesmo motor/comando já existia, mas somente contratos/testes determinísticos tinham sido executados.  
**CORREÇÃO:** nenhuma reescrita do motor. O workflow do gate prepara FFmpeg/FFprobe usando as mesmas fontes/família previstas pelo workflow Kotlin (BtbN n9.0 com fallback Gyan), somente no workspace de teste. O smoke gera um MP4 real e usa as funções de produção.  
**PYTHON DEPOIS:** motor inalterado, agora comprovado em execução real.  
**TESTE CRIADO:** `pass15_media_smoke.py` executa probe, player, pause, seek, volume, comando real de exportação e FFprobe final.  
**RESULTADO:** `MEDIA SMOKE OK player_position=301ms seek=1000ms codec=h264 duration=2.000s resolution=320x240 fps=25/1 audio=aac sample_rate=44100 channels=1`.  
**STATUS:** RESOLVIDO / MIG-070,071,072,074,075,076 APROVADOS.

## Comando FFmpeg

Nenhuma otimização foi feita. O comando Python permanece na mesma ordem do `video_editor_pyside/main.py` ativo da fonte da verdade:

```text
-y -i <input> -ss <start> -t <duration> -map 0:v:0 -map 0:a? -vf scale=trunc(iw/2)*2:trunc(ih/2)*2 -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart <output>
```

## Gate completo após as correções

Commit de código testado: `c8a53b600faa49105937b194dc74455c0eb13d3a`.

Windows:

- TOTAL 147
- PASS 147
- FAIL 0
- ERROR 0
- SKIP 0
- XFAIL 0
- XPASS 0
- pytest 15.07 s

Ubuntu:

- TOTAL 147
- PASS 144
- FAIL 0
- ERROR 0
- SKIP 3 — somente DPAPI real, compatibilidade .NET DPAPI e Registry, todos PASS no Windows
- XFAIL 0
- XPASS 0
- pytest 2.26 s

Os quatro checks do commit testado — suíte principal e release-readiness em Windows e Ubuntu — concluíram `success`.

O entry point real continuou iniciando em CWD externo; no Windows foi usado caminho com espaço e acento (`Teste Edição Monitor`).

## E2E / automação

Os testes de composição que já exercitam controller/runtime → collectors controlados → matching → repository → SQLite → UI permanecem verdes. O pipeline automático com relógio controlado também permanece verde. Como Passo 16 não alterou collectors de notícias/vídeos, os smokes live externos do Passo 14 continuam apenas como evidência de disponibilidade daquela execução e não foram usados para mascarar indisponibilidade externa.

## Segurança e logs

DPAPI real, compatibilidade .NET e Registry continuam PASS no Windows. Não foi introduzida persistência de senha, token, cookie ou credential blob em log. O teste de helper trabalha com cookie fixture explícito e não com credencial real.

## Placeholders

Nenhum placeholder crítico do fluxo normal foi identificado. Os controles não funcionais deliberados do Editor de Vídeo permanecem exatamente conforme `MIG-077`; não foram implementadas funções sem motor no Kotlin.

## Contagem final de bloqueadores

- CRÍTICOS: **0**
- ALTOS: **0**
- MÉDIOS: **0**
- BAIXOS: **0**

`MIG-061`, `MIG-114`, `MIG-079`–`083` e demais MIGs ainda `EM TESTE`/`PENDENTE` não foram promovidos por associação. Eles não integravam a matriz de bloqueadores CRÍTICOS/ALTOS do Passo 15.

## Conclusão do Passo 16

**APTO PARA PORTABLE**

Isso autoriza somente o próximo passo de build quando solicitado. Neste passo não foi criado portable, instalador, release ou merge.
