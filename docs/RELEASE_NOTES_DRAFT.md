# RELEASE NOTES — DRAFT

## Monitor de Notícias Python 0.0.1 — Windows Portable x64

Candidato técnico de migração controlada do Monitor de Notícias de Kotlin para Python/PySide6, preservando os motores e contratos comprovados da baseline histórica.

## Principais componentes

- interface desktop PySide6;
- monitoramento de notícias, vídeos, demandas, termos, fontes e histórico;
- automação residente;
- proxy e credenciais protegidas por DPAPI no Windows;
- integração de startup e tray/notificações;
- Extrator de Vídeos com yt-dlp nightly/stable, Deno, FFmpeg e FFprobe do próprio portable;
- Editor PDF;
- Editor de Vídeo PySide6/QtMultimedia;
- preview com `QMediaPlayer`, `QVideoWidget` e `QAudioOutput`;
- exportação H.264/AAC via FFmpeg.

## Artefato validado

- commit: `0f9ec957b3e9f3fdf9b02f5dbe9bb0836310d60d`
- run: `34776048157`
- arquivo: `MONITOR-DE-NOTICIAS-PYTHON-portable-windows-x64.zip`
- SHA-256: `259739899fe044157d350ab077d877ef8dd9e024cd33939266e026e8df3563f4`
- Windows Server 2025 / x64
- suíte anterior à build: 149/149
- segundo runner independente: PASS
- reextração, reabertura, movimentação, paths com espaços/acentos e segundo smoke: PASS
- processos órfãos finais: 0

## Histórico de correções do portable

`PORT-001` a `PORT-005` foram resolvidos. O `PORT-005` era uma falha de idempotência do harness de notificação, não do `AutomationService`; a correção final variou a identidade lógica da notícia artificial sem alterar regras de negócio.

## Limitações conhecidas

O Editor de Vídeo ativo preserva as funções ausentes da baseline, incluindo split, delete/reorder, IN/OUT manual, undo/redo, compactação e concatenação. O gate não substitui inspeção visual humana integral e não usou um proxy autenticado real externo.

`MIG-061` e `MIG-114` permanecem pendentes por falta de evidência explícita da baseline/caller ativo, não como bugs comprovados.

## Publicação

O ZIP técnico está validado, mas a publicação pública deve aguardar fechamento da revisão de licenças redistribuídas e uma auditoria dedicada de segredos sobre todo o histórico Git.

Tag sugerida: `v0.0.1`. Nenhuma tag/release foi criada no Passo 22.
