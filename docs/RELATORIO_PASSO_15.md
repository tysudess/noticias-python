# Relatório final — Passo 15 — Gate de equivalência

## 1. COMMIT KOTLIN DE REFERÊNCIA

`df1701ba5427a04954093e8ebed63f26abb2b2b7` — `tysudess/noticias-monitor` — 2026-09-12T20:11:33Z — mais as transformações do workflow V8 válido.

## 2. COMMIT PYTHON FINAL DESTE PASSO

O commit final documental será o head da branch após a criação deste relatório. O código efetivamente testado/corrigido antes dos documentos chegou a `c6754c558b6e620899e6d18672b5e3da867c8df4`. O gate começou em `fb6773a534853645253c8641f2dace631333a8f8`.

## 3. BRANCH

`migration/python-foundation`.

Branches auxiliares `audit-step13-temp` e `migration-python-foundation-audit-record` não foram usadas e não interferiram no gate.

## 4. BLOQUEADORES DO PASSO 14 RECEBIDOS

- `MIG-050`: login interno Globoplay/helper — BLOQUEADO.
- `MIG-079`–`MIG-083`: build/portable — PENDENTE por regra.
- `MIG-114`: consumo do GoogleNewsUrlResolver — PENDENTE, sem evidência de wiring no Dashboard V5 ativo.
- diversos itens `EM TESTE` de Windows, Extrator, PDF, Editor de Vídeo e UI.

## 5. BLOQUEADORES CORRIGIDOS

Foi encontrada e corrigida uma falha CRÍTICA nova no entry point: `ExtractorPage` emitia o sinal de qualidade durante a própria construção e `_quality_changed()` acessava `cancel_button` antes de sua criação. `python run.py` podia cair com `AttributeError`. A correção apenas protege a ordem de inicialização; motor/presets/download não mudaram.

Foram também corrigidos dois testes não determinísticos cujas fixtures criavam notícias poucos milissegundos depois do `to_ms` já congelado pelo repository. O comportamento de produção estava correto; somente os timestamps das fixtures foram fixados explicitamente dentro da janela.

## 6. BLOQUEADORES RESTANTES

- `MIG-050` — ALTO — helper/login interno Globoplay sem cadeia comprovada na release válida.
- `MIG-116` — ALTO — lifecycle/shutdown de ferramentas integradas não prova cleanup de QThreads, helper e janelas top-level.
- validação real do Editor de Vídeo com FFmpeg/FFprobe que acompanharão a futura build — ALTO para liberação; o runner Windows do gate não possuía esses binários no PATH.

## 7. MIG APROVADOS

**63**. Nenhum MIG antigo foi promovido apenas porque a suíte passou. Banco, matching, coletores determinísticos, automação central e composition root continuam aprovados dentro de seus escopos já estabelecidos.

## 8. MIG EM TESTE

**43**. Relação completa e justificativas em `docs/MIGRACAO_PASSO_15.md`.

## 9. MIG PENDENTES

**8**: `MIG-002`, `MIG-061`, `MIG-079`, `MIG-080`, `MIG-081`, `MIG-082`, `MIG-083`, `MIG-114`.

## 10. MIG BLOQUEADOS

**2**: `MIG-050` e o novo `MIG-116`. Total oficial após o gate: **116 MIGs**.

## 11. RESULTADO DO PIPELINE DE NOTÍCIAS

**OK para o core.** Fluxo controlado real: controller/runtime → collector de borda controlada → parsing/modelo → matching → NewsRepository → SQLite → refresh da UI. Persistência foi verificada diretamente no banco. O Passo 14 ainda fornece evidência live externa: Google News → repository → matching → SQLite, `found=22`, `new=22`, `stored=22`.

Matching cobre correspondência positiva/negativa, case, acento, frase/tokens, identidade storyKey e preservação da primeira captura.

## 12. RESULTADO DO PIPELINE DE VÍDEOS

**OK para o core.** RuntimeVideoRunner → collector controlado → matching → VideoRepository → VideoDb → UI foi exercitado. O Passo 14 fornece smoke live adicional de coletor g1 com 15 itens.

## 13. RESULTADO DE DEMANDAS

**OK dentro do baseline ativo.** Criar, remover, persistir, buscar todas e refletir resultados possuem cobertura. Busca individual foi conectada no runtime no Passo 14 e permanece `EM TESTE` conservadoramente. A ação dedicada `Editar` solicitada pelo roteiro é **NÃO APLICÁVEL**: ela não existe no `DashboardV5Main.kt` ativo do baseline; não foi inventada.

## 14. RESULTADO DE TERMOS

**OK.** Termos de notícias e VideoTermStore são independentes. Criar/salvar/reabrir e uso em matching estão cobertos. O VideoTermStore foi reaberto com nova instância de preferências e manteve o termo salvo. Não existe recurso ativo separado de `Editar termo`; alteração funcional no baseline é realizada pela combinação das ações existentes, e nenhum botão novo foi criado.

## 15. RESULTADO DE FONTES

**OK.** Seleção de fontes chega aos runners reais. Fonte/vídeo selecionado é processado; seleção vazia de vídeo permanece vazia e nenhum collector é chamado. Não há substituição automática por todas as fontes.

## 16. RESULTADO DO HISTÓRICO

**OK para persistência/leitura.** Histórico de notícias/vídeos usa SQLite real; leitura/limpeza estão cobertas. Histórico/qualidade portable do Extrator também tem persistência testada.

## 17. RESULTADO DA AUTOMAÇÃO

**OK para o core.** Relógio controlado comprova configuração → agendamento → disparo → runner/repository → matching → persistência → estado/UI. Execução manual e automática chegam aos mesmos métodos de busca. Proteção contra dupla execução foi testada. Notícias e vídeos podem ocupar lanes independentes conforme o motor.

## 18. RESULTADO DO PROXY

**OK para wiring/configuração; integração externa autenticada não foi exercitada.** ProxySettings migra `7db→7dn`, HttpClient é construído com a configuração e os collectors usam o cliente. Proxy desativado e configuração salva possuem cobertura. Não foi necessário inventar servidor proxy externo.

## 19. RESULTADO DAS CREDENCIAIS

**OK no mecanismo.** DPAPI CurrentUser real passou no Windows e o teste de compatibilidade com .NET ProtectedData também passou. Campo de senha na UI é mascarado e a senha protegida não é armazenada como texto puro pelo componente migrado.

## 20. RESULTADO DAS INTEGRAÇÕES WINDOWS

**PARCIALMENTE OK.** DPAPI e Registry reais passaram no runner Windows. Startup é construído conforme HKCU Run e o teste não deixa entrada deliberada de teste. Tray/notificação possui wiring; a exibição visual humana de toast/tray não foi observada neste gate. Processo oculto/árvore permanece `EM TESTE` em seu MIG amplo.

## 21. RESULTADO DO EXTRATOR

**BLOQUEADO para liberação.** O workspace passou a abrir pelo entry point após correção do bug de inicialização e os comandos/presets/retry/fallbacks têm regressão automatizada. Porém o fluxo real completo com os cinco binários exatos não foi executado neste gate, `MIG-050` permanece bloqueado, e lifecycle de QThreads/helper no fechamento não está comprovado.

## 22. RESULTADO DO EDITOR PDF

**OK para o motor; workspace ainda conservadoramente EM TESTE.** Import PDF/imagens, página em branco, crop, reorder, undo/redo, capa, exportação vetorial/raster e qualidades possuem testes. `MIG-061` continua PENDENTE porque rotação/flip visual ativa equivalente não está comprovada. Fechamento/retorno humano não foi tratado como testado quando não foi observado.

## 23. RESULTADO DO EDITOR DE VÍDEO

**BLOQUEADO para liberação real de mídia.** Importação/modelo/timeline/comandos/controles têm testes. Exclusão e reordenação de clipes solicitadas pelo roteiro são **NÃO APLICÁVEL ao motor ativo**: o editor PySide6 empacotado pela release de referência não implementa essas funções. Não foram adicionadas.

## 24. RESULTADO DO PREVIEW DE VÍDEO

Motor Kotlin distribuído efetivamente: launcher Kotlin → **Editor PySide6**. Motor Python migrado: **QMediaPlayer + QVideoWidget + QAudioOutput**, igual ao source ativo `video_editor_pyside/main.py` da release. Estrutura e volume 0,85 estão cobertos, mas reprodução real do arquivo sintético no Windows não chegou a executar porque FFmpeg/FFprobe não estavam disponíveis no runner para gerar/probar a mídia. Permanece `EM TESTE`/bloqueado para liberação.

## 25. RESULTADO DA EXPORTAÇÃO DE VÍDEO

Comando literal do motor foi revalidado e os argumentos permanecem equivalentes (`libx264`, `veryfast`, CRF 20, yuv420p, AAC 160k, faststart, áudio opcional). A execução real do smoke foi impedida pela ausência dos binários no runner; portanto não é marcado OK de execução.

## 26. RESULTADO FFPROBE

Parser e comando são testados por fixture/equivalência. FFprobe real do arquivo exportado não foi executado no gate porque o runner Windows não disponibilizou `ffprobe`. **BLOQUEADO PARA A LIBERAÇÃO**, não mascarado como sucesso.

## 27. RESULTADO DOS TESTES DE PATH

**OK em source mode.** `run.py` iniciou:

- Windows em cópia `Teste Edição Monitor` (espaço + acento), a partir de outro CWD;
- Ubuntu a partir de outro CWD.

Foram resolvidos/criados `data/news.db`, `data/videos.db`, `logs/monitor-noticias.log` e resource de ícone na raiz correta. Busca estática não encontrou caminho absoluto do desenvolvedor, usuário específico, `.venv`, `site-packages` ou dependência de CWD em `src/`/`run.py`. `MIG-002` permanece PENDENTE porque o ramo `sys.frozen` exige a build futura.

## 28. RESULTADO DO SHUTDOWN

**BLOQUEADO.** AutomationService possui cancelamento/close próprio, mas `MainWindow.exit_application()` não coordena explicitamente os QThreads do Extrator, eventual processo do helper Globoplay e janelas top-level do Editor de Vídeo abertas no mesmo processo. Não foi aplicada terminação forçada de thread Python.

## 29. PROCESSOS ÓRFÃOS ENCONTRADOS

Nenhum processo órfão foi observado nos jobs concluídos. Entretanto, o teste essencial “fechar durante operação de ferramenta ativa” não está provado; portanto ausência de órfão nessa situação é **NÃO DETERMINADO PELO CÓDIGO ANALISADO.** e compõe `MIG-116`.

## 30. TEMPORÁRIOS RESIDUAIS

Rollback/cleanup de arquivos temporários em vários módulos possui testes e blocos `finally`. Não há evidência de resíduo relevante nos testes concluídos. Cleanup após fechamento forçado durante operação ativa é **NÃO DETERMINADO PELO CÓDIGO ANALISADO.** enquanto `MIG-116` estiver bloqueado.

## 31. PLACEHOLDERS DE PRODUÇÃO

Nenhum placeholder indevido foi identificado no fluxo central. A busca global encontrou `pass` em classes de exceção, tolerância de parse/config, fechamento/cleanup e callbacks deliberadamente no-op. Os placeholders do Editor de Vídeo permanecem deliberados e aprovados por `MIG-077`, porque o motor ativo também não implementa essas funções. Resíduos de classes legadas não usadas pela MainWindow não foram tratados como wiring de produção.

## 32. SKIPS

Ubuntu: **3 skips**, todos Windows-only:

1. DPAPI real requer Windows;
2. compatibilidade .NET DPAPI requer Windows;
3. Registry real requer Windows.

Os três executaram e passaram no Windows. Windows: **0 skips**.

## 33. XFAIL

**0 XFAIL** e **0 XPASS**. Nenhuma declaração xfail encontrada.

## 34. RESULTADO COMPLETO DA SUÍTE

Plataforma alvo Windows, commit de código `c6754c558b6e620899e6d18672b5e3da867c8df4`:

- TOTAL: 141
- PASS: 141
- FAIL: 0
- ERROR: 0
- SKIP: 0
- XFAIL: 0
- XPASS: 0
- DURAÇÃO: 10.77 s

Ubuntu:

- TOTAL: 141
- PASS: 138
- FAIL: 0
- ERROR: 0
- SKIP: 3 Windows-only
- XFAIL: 0
- XPASS: 0
- DURAÇÃO: 3.22 s

## 35. RESULTADO END-TO-END

**Core do Monitor: OK. Gate global: BLOQUEADO.** Notícias, vídeos, bancos, matching, repositories, automação e refresh de UI têm prova ponta a ponta com bordas externas controladas, complementadas por smoke live do Passo 14. O programa, contudo, não satisfaz o critério global porque as ferramentas integradas ainda têm bloqueadores altos.

## 36. DEPENDÊNCIAS DO FUTURO PORTABLE

Python 3.12 runtime; PySide6 6.9.1 + Shiboken/Qt plugins; requests; BeautifulSoup; lxml; pypdf 6.18.0; pypdfium2/PDFium 5.13.0; Pillow 12.3.0; dependências transitivas do HTTP; CA/certifi; resources de ícone/capa; cinco binários externos do workflow (`yt-dlp.exe`, `yt-dlp-stable.exe`, `deno.exe`, `ffmpeg.exe`, `ffprobe.exe`); APIs Windows DPAPI/Registry fornecidas pelo SO. Helper Globoplay somente depois de comprovada sua cadeia.

## 37. DLLS/BINÁRIOS NECESSÁRIOS

- DLLs e plugins Qt requeridos por QApplication, tray e QtMultimedia;
- backend de multimídia efetivamente selecionado no Windows: **NÃO DETERMINADO PELO CÓDIGO ANALISADO.**;
- bibliotecas nativas PDFium;
- `yt-dlp.exe` nightly;
- `yt-dlp-stable.exe`;
- `deno.exe` x64;
- `ffmpeg.exe`;
- `ffprobe.exe`;
- runtime Python congelado.

## 38. RISCOS RESIDUAIS

- lifecycle/shutdown das ferramentas;
- helper interno Globoplay não comprovado;
- mídia real com binários exatos ainda não executada;
- dependências QtMultimedia/DLLs somente serão observáveis na montagem real;
- possíveis falsos positivos de antivírus por executável congelado, yt-dlp, FFmpeg, Deno, subprocessos ocultos, taskkill, DPAPI e Registry;
- tamanho estimado do futuro ZIP ~0,8–1,0 GB e ~1–1,4 GB descompactado, mas o valor real é **NÃO DETERMINADO PELO CÓDIGO ANALISADO.** até o build.

## 39. BLOQUEADORES PARA PORTABLE

| ID | MIG | Severidade | Estado |
|---|---|---|---|
| B14-01 | MIG-050 | ALTO | BLOQUEADO |
| B15-02 | MIG-116 | ALTO | BLOQUEADO |
| B15-03 | MIG-070/071/072/074/075/076 | ALTO para liberação | validação real com binários do pacote ausente |

Como existem bloqueadores ALTOS, o critério de liberação não é atendido.

## 40. CONCLUSÃO FINAL OBRIGATÓRIA

# NÃO APTO PARA PORTABLE

### Justificativa

O gate comprovou que o Monitor central não é mais um conjunto de módulos isolados: o entry point real inicia, bancos/repositories/matching/coletores controlados/automação/persistência/refresh de UI funcionam, o código passa 141/141 testes no Windows e o caminho com espaço/acento e CWD externo funciona. Também encontrou e corrigiu uma falha real de inicialização do Extrator.

Mesmo assim, a regra do Passo 15 é objetiva: nenhum bloqueador CRÍTICO ou ALTO pode restar. Restam `MIG-050`, `MIG-116` e a validação real de mídia com os binários que deverão acompanhar a build. Portanto, declarar `APTO PARA PORTABLE` agora seria uma promoção sem evidência.

### Confirmação do repositório original

`tysudess/noticias-monitor` não foi alterado por este Passo 15. Todas as alterações foram feitas somente em `tysudess/MONITOR-DE-NOTICAS-PYTHON`, branch `migration/python-foundation`.

Nenhum portable, instalador, merge ou release foi criado.
