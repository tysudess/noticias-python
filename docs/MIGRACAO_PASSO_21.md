# MIGRAÇÃO — PASSO 21

## Objetivo

Corrigir exclusivamente o `PORT-005`, reproduzir a falha e repetir o ciclo oficial até obter um portable integralmente validado, sem alterar regras de negócio, repositories, matching, deduplicação, `AutomationService`, UI funcional ou repositório Kotlin.

## Estado inicial

- candidato anterior: `186a28e4a5f53296178fd9d0ee74637a8a5149bf`
- run anterior: `34768584764`
- falha: segundo smoke externo exigia callback de “notícia nova” para uma notícia já persistida
- classificação: **FALHA DO GATE**

## PORT-001

**CAUSA:** `_DownloadWorker` do Extrator era mantido apenas em variável local durante a `QThread`.  
**CORREÇÃO:** referência forte ao worker durante a operação e limpeza no encerramento.  
**TESTE:** regressão assíncrona + smoke real do Extrator no PyInstaller.  
**STATUS: RESOLVIDO**

## PORT-002

**CAUSA:** workflow portable não observava todas as entradas relevantes de source/test/build.  
**CORREÇÃO:** ampliar os filtros do workflow para mudanças funcionais relevantes.  
**TESTE:** pushes funcionais posteriores dispararam novas builds; `docs/**` permanece fora do gatilho.  
**STATUS: RESOLVIDO**

## PORT-003

**CAUSA:** interpolação PowerShell inválida com `$dir:` no segundo runner.  
**CORREÇÃO:** `${dir}:`.  
**TESTE:** segundo runner final executou o script integralmente.  
**STATUS: RESOLVIDO**

## PORT-004

**CAUSA:** download artificial `extractor_fixture` do primeiro smoke permanecia em `Videos/` e era reapresentado depois da movimentação.  
**CORREÇÃO:** remover somente `*extractor_fixture*` antes de cada smoke, sem limpeza geral e sem alterar `ExtractorEngine`.  
**TESTE:** segundo smoke final ultrapassou o Extrator e concluiu.  
**STATUS: RESOLVIDO**

## PORT-005

**CAUSA:** `temp/pipeline-smoke/news.db` persistia entre primeiro e segundo smoke. O gate recriava `notification_events=[]` e exigia nova notificação para uma história já conhecida. A deduplicação real usa identidade por link **ou** `storyKey`, sendo `storyKey = source normalizada | título normalizado`.

**PRIMEIRA CORREÇÃO:** commit `4616210925670baa746ee6a96bbd154ffb517f2b` variou somente o link artificial.  
**RESULTADO:** run `34775684247` falhou antes da build com `1 failed, 148 passed`, provando que URL distinta com o mesmo `source + title` continua sendo a mesma história.

**CORREÇÃO FINAL:** commit `0f9ec957b3e9f3fdf9b02f5dbe9bb0836310d60d` variou deterministicamente link e título artificiais entre `local`, `original` e `moved`, preservando o termo `MARINHA`. A alteração ficou somente no runtime hook de validação e no teste de regressão; nenhum arquivo em `src/` foi modificado.

**TESTE:** contrato `nova → notifica; repetida → não notifica; história distinta → notifica`, seguido de regressão completa e dois smokes do runtime congelado.

**STATUS: RESOLVIDO**

## Run final

- run: `34776048157`
- workflow: `Passo 17 - Windows Portable`
- commit: `0f9ec957b3e9f3fdf9b02f5dbe9bb0836310d60d`
- conclusão: `success`
- suíte: `149 passed`
- ZIP: `MONITOR-DE-NOTICIAS-PYTHON-portable-windows-x64.zip`
- tamanho: `651329315` bytes
- descompactado: `1262862742` bytes
- SHA-256: `259739899fe044157d350ab077d877ef8dd9e024cd33939266e026e8df3563f4`

## Segundo runner

- Windows Server 2025 / NT 10.0.26100 / AMD64
- sem checkout de desenvolvimento
- FFmpeg/FFprobe globais ausentes
- hash interno idêntico
- reextração PASS
- primeiro smoke PASS
- reabertura PASS
- movimentação PASS
- path com espaços/acento PASS
- segundo smoke PASS
- shutdown PASS
- processos órfãos 0
- temporários PASS
- segredos reais no artefato 0
- dados pessoais no ZIP 0

## Conclusão

**PORTABLE VALIDADO**
