# Decisões de migração

## Decisões anteriores preservadas

As decisões `DEC-001` a `DEC-041` permanecem válidas, permanentes e não são renumeradas. O histórico detalhado permanece rastreável nos commits dos Passos 1 a 9. Resumo:

| DEC | Escopo | Decisão preservada |
|---|---|---|
| DEC-001 | Runtime | Python 3.12.x |
| DEC-002 | UI | PySide6 6.9.1 |
| DEC-003 | Paths | raiz portable centralizada em AppPaths |
| DEC-004 | Binários | não substituir binários externos antes do passo próprio |
| DEC-005 | Git | branch `migration/python-foundation` |
| DEC-006 | SQLite | sqlite3/SQL explícito, sem ORM |
| DEC-007–015 | Dados/matching | preservar contratos, sem repositories/score inventados |
| DEC-016–018 | HTTP/Globoplay | requests/parsing e proxy injetável, fluxos parciais explicitados |
| DEC-019–024 | Automação | scheduler/lanes/clock/ports/cancelamento equivalentes |
| DEC-025–032 | Windows/segurança | proxy, DPAPI, startup, tray, subprocessos e CI Windows |
| DEC-033–041 | UI Passo 9 | QMainWindow/stack, controller fino, catálogo, placeholders, senha segura, QThread, tray, CI Qt e aprovação conservadora |

As decisões dos Passos 10 e 11 permanecem válidas; o Passo 12 não as revoga.

## DEC-042
ID DA DECISÃO: DEC-042  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-043 a MIG-057, MIG-106, MIG-107  
COMPONENTE: Fonte da verdade do Extrator  
COMPORTAMENTO ORIGINAL: o arquivo estático `ExtractorVideoEngine.kt` no Build SHA ainda é transformado pelo workflow antes da compilação. `integrate-v8-extractor-tab.py`, `patch-extractor-generic-html.py`, seus patches encadeados e `patch-extractor-hidden-process.py` alteram roteamento, live, persistência, retry, R7, paths, cancelamento e subprocessos.  
DECISÃO: portar o **resultado efetivo do Build SHA `df1701...` + patches executados pela workflow**, e não o HEAD atual do branch nem o source Kotlin estático isolado.  
JUSTIFICATIVA: somente essa composição corresponde à release aprovada.  
EVIDÊNCIA: workflow V8 e Build SHA.  
IMPACTO: evita regressão para motor intermediário.  
REVERSÍVEL: Não sem mudar a baseline.

## DEC-043
ID DA DECISÃO: DEC-043  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-043 a MIG-054  
COMPONENTE: Motor de download  
COMPORTAMENTO ORIGINAL: o Extrator combina yt-dlp nightly, yt-dlp stable, FFmpeg, FFprobe, Deno, fallbacks HTML próprios e lógica própria de HLS/live.  
DECISÃO: manter essa composição; não substituir tudo por biblioteca Python ou serviço alternativo.  
JUSTIFICATIVA: equivalência do motor funcional.  
EVIDÊNCIA: fontes do Extrator + workflow.  
IMPACTO: cinco binários continuam dependências externas.  
REVERSÍVEL: Não sem alterar comportamento.

## DEC-044
ID DA DECISÃO: DEC-044  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-043, MIG-044, MIG-045  
COMPONENTE: Presets e retry  
COMPORTAMENTO ORIGINAL: cinco qualidades possuem selector primário e compatível; retry só para falhas específicas.  
DECISÃO: copiar labels/selectors/limits literalmente e restringir retry às mesmas mensagens.  
JUSTIFICATIVA: ampliar retry mudaria tentativas/tráfego.  
REVERSÍVEL: Não sem mudar equivalência.

## DEC-045
ID DA DECISÃO: DEC-045  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-046, MIG-047, MIG-048  
COMPONENTE: Roteamento e fallback HTML  
COMPORTAMENTO ORIGINAL: YouTube, Globoplay, R7/Record e genérico têm caminhos distintos; HTML fallback testa até 15 candidatos.  
DECISÃO: manter as quatro rotas e limites/filtros específicos.  
REVERSÍVEL: Somente com prova de equivalência.

## DEC-046
ID DA DECISÃO: DEC-046  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-051, MIG-052, MIG-053, MIG-054  
COMPONENTE: YouTube Live  
COMPORTAMENTO ORIGINAL: live ativa usa snapshot HLS congelado e fallback temporal limitado.  
DECISÃO: portar o snapshot HLS e proibir fallback ilimitado quando o início não puder ser determinado.  
REVERSÍVEL: Não sem mudar comportamento aprovado.

## DEC-047
ID DA DECISÃO: DEC-047  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-049, MIG-050  
COMPONENTE: Sessão/login Globoplay  
COMPORTAMENTO ORIGINAL: cookies Netscape protegidos por DPAPI CurrentUser; login em helper Chromium/PySide6.  
DECISÃO: reutilizar DPAPI e não inventar outro navegador/login enquanto o helper não estiver empacotado.  
IMPACTO: login real permanece bloqueado até o helper.

## DEC-048
ID DA DECISÃO: DEC-048  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-055, MIG-106  
COMPONENTE: Threading e cancelamento do Extrator  
DECISÃO: `ExtractorPage` usa `QThread`, token de operação e destruição da árvore do subprocesso.  
REVERSÍVEL: Não sem manter os dois níveis de cancelamento.

## DEC-049
ID DA DECISÃO: DEC-049  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-040, MIG-044 a MIG-053  
COMPONENTE: Proxy do Extrator  
DECISÃO: não ligar automaticamente o proxy geral ao Extrator porque a release final chama o engine com proxy vazio.  
REVERSÍVEL: Sim com evidência futura.

## DEC-050
ID DA DECISÃO: DEC-050  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-057  
COMPONENTE: Atualizador yt-dlp  
DECISÃO: preservar temp, backup, validação `--version`, restauração e timeouts do updater original.  
REVERSÍVEL: Não sem segurança equivalente.

## DEC-051
ID DA DECISÃO: DEC-051  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-106, MIG-107  
COMPONENTE: Aprovação/testes do Passo 10  
DECISÃO: CI aprova contratos determinísticos; downloads reais permanecem `EM TESTE` sem bundle final.  
JUSTIFICATIVA: não confundir mocks com mídia real.

## DEC-052
ID DA DECISÃO: DEC-052  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-058 a MIG-067, MIG-108, MIG-109  
COMPONENTE: Fonte da verdade do Editor PDF  
COMPORTAMENTO ORIGINAL: Dashboard usa `PdfEditorScreenV2`; `PdfEditorScreen.kt` é anterior.  
DECISÃO: migrar exclusivamente V2 + patches visuais do workflow.  
REVERSÍVEL: Não sem mudar baseline.

## DEC-053
ID DA DECISÃO: DEC-053  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-058, MIG-060, MIG-064, MIG-066, MIG-067  
COMPONENTE: Bibliotecas PDF Python  
DECISÃO: `pypdf==6.18.0` para montagem/vetorial, `pypdfium2==5.13.0` para renderização e `Pillow==12.3.0` para imagens/crop/raster.  
LICENÇAS: permissivas; avisos PDFium devem acompanhar o portable.  
REVERSÍVEL: somente mediante equivalência comprovada.

## DEC-054
ID DA DECISÃO: DEC-054  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-061  
COMPONENTE: Rotação e espelhamento PDF  
DECISÃO: manter suporte interno, mas não expor botão/menu sem caller ativo comprovado.  
IMPACTO: MIG-061 permanece PENDENTE.

## DEC-055
ID DA DECISÃO: DEC-055  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-065, MIG-066, MIG-067  
COMPONENTE: Exportação vetorial x raster PDF  
DECISÃO: preservar bifurcação; remover `/Annots` no merge vetorial para equivaler a `importPageAsForm`; raster RGB lossless/Flate.  
REVERSÍVEL: Não sem mudar resultado estrutural.

## DEC-056
ID DA DECISÃO: DEC-056  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-058, MIG-060, MIG-062, MIG-108  
COMPONENTE: Preview, miniaturas e zoom PDF  
DECISÃO: preview 120 dpi, miniatura 58 dpi max 56×84, zoom 50–300% passo 15%, Ajustar=100%, Redimensionar visual 75/90/100/110/125%; não criar navegação inexistente.  
REVERSÍVEL: Não sem mudar UX comprovada.

## DEC-057
ID DA DECISÃO: DEC-057  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-064  
COMPONENTE: Capa PDF  
DECISÃO: copiar literalmente `pdf-default-cover.b64`, preservar ordem de resolução e capa custom PNG.  
REVERSÍVEL: Não sem perder equivalência.

## DEC-058
ID DA DECISÃO: DEC-058  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-063, MIG-108  
COMPONENTE: Estado/undo/threads PDF  
DECISÃO: snapshots integrais máximo 30; `QThread` preview/export e `QThreadPool` apenas para miniaturas independentes.  
REVERSÍVEL: Não sem semântica equivalente.

## DEC-059
ID DA DECISÃO: DEC-059  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-066, MIG-067  
COMPONENTE: Salvamento/proteção do original PDF  
DECISÃO: Save As equivalente, nunca modificar entradas; política custom de overwrite: **NÃO DETERMINADO PELO CÓDIGO ANALISADO**.  
REVERSÍVEL: Não sem mudar segurança do original.

## DEC-060
ID DA DECISÃO: DEC-060  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-108, MIG-109  
COMPONENTE: Critério de aprovação do Passo 11  
DECISÃO: CI offscreen aprova contratos determinísticos, não substitui inspeção humana; MIG-108 permanece `EM TESTE`.  
REVERSÍVEL: status avança após teste manual real.

## DEC-061
ID DA DECISÃO: DEC-061  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-068 a MIG-078, MIG-110, MIG-111  
COMPONENTE: Fonte da verdade do Editor de Vídeo  
COMPORTAMENTO ORIGINAL: a release final não abre `VideoEditorEngine.kt`; `VideoEditorScreen.kt` lança `video-editor/VideoEditorPySide/VideoEditorPySide.exe`, construído pelo workflow a partir de `video_editor_pyside/main.py`.  
DECISÃO: considerar `video_editor_pyside/main.py` o **motor ativo**; classificar `VideoEditorEngine.kt`, `VideoEditorPreview.kt` e `VideoEditorProcess.kt` como `LEGADO/ALTERNATIVO` para esta baseline.  
JUSTIFICATIVA: somente o executável PySide6 é empacotado e aberto pelo launcher final.  
EVIDÊNCIA: `VideoEditorScreen.kt`, `integrate-video-editor-tab.py`, workflow V8 e comando PyInstaller.  
IMPACTO: recursos mais ricos do motor Kotlin alternativo não podem ser misturados à migração.  
REVERSÍVEL: Não sem mudar a baseline.

## DEC-062
ID DA DECISÃO: DEC-062  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-071, MIG-072, MIG-074, MIG-075  
COMPONENTE: Motor de preview  
COMPORTAMENTO ORIGINAL: `QMediaPlayer` + `QVideoWidget` + `QAudioOutput`, PySide6 6.9.1, volume 0,85.  
DECISÃO: manter exatamente o mesmo motor no Monitor Python; não avaliar VLC/mpv/GStreamer/FFplay/OpenCV porque não há necessidade de troca.  
JUSTIFICATIVA: o motor original já é Python e está disponível no runtime alvo.  
EVIDÊNCIA: `video_editor_pyside/main.py` e validações do workflow.  
IMPACTO: não existe “troca de motor”; apenas integração/modularização. Backend interno QtMultimedia: **NÃO DETERMINADO PELO CÓDIGO ANALISADO**.  
REVERSÍVEL: somente mediante nova baseline/necessidade comprovada.

## DEC-063
ID DA DECISÃO: DEC-063  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-077, MIG-078  
COMPONENTE: Recursos ausentes  
COMPORTAMENTO ORIGINAL: o editor ativo não implementa split, delete, duplicate, reorder, drag-and-drop, thumbnails, zoom funcional, IN/OUT manual, undo/redo, compactação, target-size, codec/resolution/FPS chooser, concat, progresso ou cancelamento. Muitos nomes aparecem apenas como placeholders.  
DECISÃO: **não implementar** esses recursos no Passo 12 e criar testes que impeçam sua introdução silenciosa.  
JUSTIFICATIVA: copiar recursos do motor Kotlin alternativo produziria um editor que não corresponde à release.  
IMPACTO: MIG-077 pode ser aprovado; MIG-078 é aprovado como ausência comprovada de edição manual IN/OUT.  
REVERSÍVEL: somente se uma baseline futura provar recurso ativo.

## DEC-064
ID DA DECISÃO: DEC-064  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-073, MIG-074  
COMPONENTE: Modelo temporal/timeline  
COMPORTAMENTO ORIGINAL: unidade em ms; global é soma de durações; global→local usa `global_ms <= next_cursor`, mantendo o limite exato no clipe anterior. Timeline calcula posição proporcional pela largura.  
DECISÃO: centralizar e testar essas conversões sem corrigir a regra de fronteira.  
JUSTIFICATIVA: alterar `<=' para `<` mudaria seek e troca de clipe no limite.  
IMPACTO: matemática determinística pode ser aprovada independentemente do backend real de seek.  
REVERSÍVEL: Não sem mudar comportamento.

## DEC-065
ID DA DECISÃO: DEC-065  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-070, MIG-076  
COMPONENTE: FFprobe/FFmpeg  
COMPORTAMENTO ORIGINAL: FFprobe usa JSON `-show_format -show_streams`; exportação é `subprocess.run` síncrona, timeout 3600, `-ss/-t` depois de `-i`, libx264 veryfast CRF20 yuv420p, AAC160k, `+faststart`; não usa `-progress`.  
DECISÃO: preservar comandos, ordem e execução síncrona; **não adicionar worker/progresso/cancelamento** por conveniência durante a migração.  
JUSTIFICATIVA: background/progresso seria melhoria funcional que o motor ativo não possui.  
IMPACTO: exportação permanece `EM TESTE` até execução real com binários da release.  
REVERSÍVEL: melhorias futuras exigem decisão separada após equivalência.

## DEC-066
ID DA DECISÃO: DEC-066  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-068, MIG-110  
COMPONENTE: Fronteira de processo  
COMPORTAMENTO ORIGINAL: o Monitor Kotlin inicia `VideoEditorPySide.exe` em processo separado.  
DECISÃO: antes do passo de portable final, `VideoEditorPage` abre `VideoEditorWindow` como janela top-level no mesmo processo Python, preservando o mesmo código/motor de editor. A separação em segundo EXE fica para o passo de empacotamento, onde será validada contra o contrato original.  
JUSTIFICATIVA: gerar PyInstaller agora anteciparia explicitamente o passo de portable proibido pelo escopo do Passo 12.  
IMPACTO: `MIG-068` e `MIG-110` permanecem `EM TESTE`; essa diferença arquitetural não é escondida.  
REVERSÍVEL: Sim, no passo de build/portable.

## DEC-067
ID DA DECISÃO: DEC-067  
DATA: 2026-09-12  
MIG RELACIONADO: MIG-069 a MIG-076, MIG-110, MIG-111  
COMPONENTE: Critério de aprovação do Passo 12  
COMPORTAMENTO ORIGINAL: preview/áudio/seek/exportação dependem de backend multimídia Windows e binários reais.  
DECISÃO: CI Windows/Ubuntu Qt offscreen pode aprovar contratos determinísticos, timeline e regressão, mas **não** aprova play/áudio/seek real nem exportação FFmpeg sem mídia e binários reais.  
JUSTIFICATIVA: o pedido proíbe aprovar preview/exportação por mera abertura ou mocks.  
EVIDÊNCIA: run `34726977912`, 132 testes no Windows, ambos os jobs `success`.  
IMPACTO: MIG-073, MIG-077, MIG-078 e MIG-111 aprovados; MIG-068/069/070/071/072/074/075/076/110 continuam `EM TESTE`.  
REVERSÍVEL: status avança após teste real controlado.

## Regra de segurança

Nenhuma decisão autoriza logar senha, token, cookie, blob DPAPI, plaintext descriptografado ou conteúdo sensível. Fixtures de vídeo/PDF devem ser artificiais e não pessoais. O portable final não é iniciado no Passo 12.
