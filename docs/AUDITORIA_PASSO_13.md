# PASSO 13 — Auditoria geral Kotlin x Python

## Escopo congelado

- Kotlin / fonte da verdade: `tysudess/noticias-monitor` @ `df1701ba5427a04954093e8ebed63f26abb2b2b7` + transformações do workflow V8.
- Python auditado: `tysudess/MONITOR-DE-NOTICAS-PYTHON` @ `6419ee336f3015bd466afa8c2ac4e961ca7c6ff3`.
- Branch Python: `migration/python-foundation`.
- O runtime Python entre o commit de código testado `d244779b1a0d582090b15d072437f6c2f0e51f78` e o commit congelado acima é idêntico; os quatro commits posteriores ao runtime alteraram apenas documentação.

## Resultado executivo

A migração **não está pronta para portable** e **não é funcionalmente equivalente de ponta a ponta**.

A regressão principal é estrutural: `NewsRepository` e `VideoRepository` ativos no Kotlin não possuem implementação equivalente no Python. O `Application` Python cria `MainWindow()` sem instanciar `AutomationService`; `MainUiController.create_default()` usa `automation=None`. Consequentemente, ações de busca de notícias, vídeos e demandas da aplicação real permanecem indisponíveis. O `AutomationService` existe e sua lógica isolada é testável, mas não está ligado ao produto real.

Além disso:

- o catálogo base `VideoSourceCatalog.kt` não foi migrado; somente os extras `youtube-g1` e `youtube-domingo-espetacular` estão disponíveis;
- `VideoTermStore` independente não foi migrado;
- a busca individual de demanda não está ligada;
- o resolvedor de URL Google News do `DesktopControllerV5` não possui equivalente na UI Python;
- as telas de Notícias/Vídeos/Demandas/Termos/Fontes existem visualmente, mas não podem ser aprovadas como equivalentes enquanto os motores de negócio não estiverem ligados;
- build/portable final continua deliberadamente pendente.

## Inventário ativo resumido

| Componente Kotlin | Arquivo Kotlin | Componente Python | Arquivo Python | Status | Observação |
|---|---|---|---|---|---|
| Entrada Desktop | `DashboardV5Main.kt` + `DesktopControllerV5.kt` | `Application` + `MainWindow` | `app/application.py`, `ui/main_window.py` | DIVERGENTE | Python não constrói repositories/AutomationService reais |
| News DB | `DesktopNewsDb.kt` | `NewsDb` | `database/news_db.py` | EQUIVALENTE | schema/migrations/CRUD/upsert comparados |
| Video DB | `DesktopVideoDb.kt` | `VideoDb` | `database/video_db.py` | EQUIVALENTE | schema/sem migration/reparo comparados por testes |
| NewsRepository | `NewsRepository.kt` | — | — | AUSENTE | FUNCIONALIDADE AUSENTE NA MIGRAÇÃO |
| VideoRepository | `VideoRepository.kt` | — | — | AUSENTE | FUNCIONALIDADE AUSENTE NA MIGRAÇÃO |
| News collector direto | `NewsLatestCollector.kt` | collector Python | `collectors/news/*` | EQUIVALENTE por escopo | contratos determinísticos testados |
| Video matching | `VideoMatchPolicy.kt` | matching Python | `matching/video.py` | EQUIVALENTE por escopo | golden cases |
| Video source catalog | `VideoSourceCatalog.kt` | parcial | `ui/catalog.py` | AUSENTE/PARCIAL | só dois extras Desktop |
| VideoTermStore | `VideoTermStore.kt` | — | — | AUSENTE | MIG-024 |
| Automação | loop em `DesktopControllerV5` | `AutomationService` | `automation/service.py` | DIVERGENTE INTEGRADO | motor isolado existe; runtime não inicia |
| Proxy | `DesktopControllerV5` | `ProxySettings` | `networking/proxy.py` | DIVERGÊNCIA DELIBERADA | senha migrada para DPAPI; segurança superior, sem plaintext |
| UI principal | `DashboardV5Main.kt` | `MainWindow` | `ui/main_window.py` | EM TESTE | navegação/tray existem, negócio incompleto |
| Extrator | Kotlin pós-patches | Python extractor | `extractor/*`, `ui/extractor_page.py` | EM TESTE | contratos presentes; integração real/binários ainda pendentes |
| PDF | `PdfEditorScreenV2.kt` pós-patches | PySide/PDF libs | `pdf_editor/*`, `ui/pdf_editor_page.py` | EM TESTE no workspace | motor determinístico amplamente validado |
| Editor vídeo | `video_editor_pyside/main.py` + launcher Kotlin | PySide QtMultimedia | `video_editor/*`, `ui/video_editor_page.py` | EM TESTE | mesmo motor; validação humana/binários pendente |

## Banco e models

`NewsDb` Python reproduz tabelas `news`, `terms`, `demands`, WAL, `busy_timeout=5000`, migrations runtime, seed, transação de lote, UPSERT lógico, CRUD de termos/demandas e limpeza. Os testes de equivalência constroem banco antigo e verificam `captured_at=date`, colunas acrescentadas, rollback, Unicode e preservação de captura.

`VideoDb` possui testes de schema exato, ausência deliberada de migration automática de colunas, duplicata, limpeza de listings inválidos e reparo de matches. Por isso `MIG-005` a `MIG-013` foram promovidos a `APROVADO`.

`News` e `Demand` Python mantêm campos/defaults do Kotlin. Modelos de resultados/progresso estão distribuídos em `automation/models.py`; não substituem a ausência dos repositories.

## Configurações principais

| Chave | Kotlin default | Python default | Kotlin storage | Python storage | Status |
|---|---:|---:|---|---|---|
| `desktop_news_all_sources` | true | true | prefs properties | prefs properties | EQUIVALENTE |
| `desktop_news_source_ids` | vazio | vazio | prefs | prefs | EQUIVALENTE |
| `desktop_video_source_ids` | defaultIds completos | catálogo Python disponível | prefs | prefs | DIVERGENTE devido catálogo incompleto |
| `desktop_automatic_monitoring` | true | true | prefs | prefs | EQUIVALENTE como setting |
| `desktop_news_automatic` | true | true | prefs | prefs | EQUIVALENTE como setting |
| `desktop_demand_automatic` | true | true | prefs | prefs | EQUIVALENTE como setting |
| `desktop_video_automatic` | true | true | prefs | prefs | EQUIVALENTE como setting |
| `desktop_news_interval` | 30, mínimo 15 | 30, mínimo 15 | prefs | prefs | EQUIVALENTE |
| `desktop_demand_interval` | 60, mínimo 15 | 60, mínimo 15 | prefs | prefs | EQUIVALENTE |
| `desktop_video_schedule_times` | 08:00,12:00,15:00,19:00,21:00 | mesmos | prefs | prefs | EQUIVALENTE |
| `desktop_auto_news_at` | 0 | 0 | prefs | prefs | EQUIVALENTE |
| `desktop_auto_demands_at` | 0 | 0 | prefs | prefs | EQUIVALENTE |
| `desktop_auto_video_at` | 0 | 0 | prefs | prefs | EQUIVALENTE |
| `desktop_start_with_windows` | false | false | prefs + HKCU Run | prefs + StartupManager | EM TESTE |
| `desktop_proxy_enabled` | false | false | prefs | prefs | EQUIVALENTE |
| `desktop_proxy_host` | `proxy-7dn.mb` | mesmo | prefs | prefs | EQUIVALENTE |
| `desktop_proxy_port` | 6060 | 6060 | prefs | prefs | EQUIVALENTE |
| `desktop_proxy_username` | vazio | vazio | prefs | prefs | EQUIVALENTE |
| `desktop_proxy_password` | plaintext prefs | DPAPI CurrentUser | prefs | DPAPI | DIVERGÊNCIA DELIBERADA DE SEGURANÇA |
| `video_terms_v400*` | presente | ausente | prefs | — | AUSENTE |

## Automação, concorrência, retry e timeout

O `AutomationService` Python preserva dois lanes: notícias/demandas compartilhando executor único e vídeos em executor independente, loop de 30 s, notícia antes de demanda via `elif`, slots locais para vídeos, tokens de cancelamento e status/duração. Isso sustenta `MIG-088` e `MIG-089` como contratos isolados.

Porém a aplicação real não instancia o serviço. Assim `MIG-035` a `MIG-038` foram rebaixados para `BLOQUEADO`. Configuração existente sem execução não é automação funcional.

Retries/timeouts dos coletores/extrator permanecem registrados nos MIGs específicos; nenhum foi promovido apenas por existir código.

## UI e navegação

A navegação PySide contém as 12 seções esperadas e as ferramentas. Entretanto botões de busca são habilitados somente quando `controller.search_available` é verdadeiro; no runtime padrão é falso. A suíte possui um teste que explicitamente confirma essa indisponibilidade.

`SourcesPage` usa `controller.video_sources`; como o catálogo Python tem somente dois extras, a tab Vídeos é funcionalmente incompleta.

A UI de Notícias abre/copia/compartilha diretamente `n.link`; o Kotlin possui `resolveVehicleUrl()` para desembrulhar links Google News antes de abrir/copiar/compartilhar. Essa função gerou `MIG-114`.

## Extrator, PDF e Editor de Vídeo

A auditoria do Passo 13 não encontrou evidência nova que invalide as classificações conservadoras dos Passos 10–12. Componentes determinísticos e testes continuam válidos; integrações que exigem binários, rede ou desktop humano permanecem `EM TESTE`.

Motor de preview do editor de vídeo na release: PySide6 `QMediaPlayer` + `QVideoWidget` + `QAudioOutput`. Motor Python: o mesmo. Não foi aceita a implementação Kotlin alternativa de frames como fonte do editor distribuído.

Comando FFprobe do editor ativo continua `-v error -print_format json -show_format -show_streams <arquivo>`, timeout 60 s. O comando FFmpeg de exportação preserva ordem `-i` antes de `-ss/-t`, H.264/AAC, CRF 20, preset veryfast, `yuv420p`, áudio 160k e `+faststart`. Não houve nova divergência de comando descoberta no Passo 13.

## Paths, temporários e logs

`AppPaths` Python centraliza `resources/`, `data/`, `bin/`, `logs/`, `temp/`, `news.db`, `videos.db`, `ffmpeg.exe` e `ffprobe.exe`. Em modo frozen usa a pasta do executável e não depende do CWD; o portable final ainda precisa validar a estrutura completa.

O Python adicionou logging próprio em `logs/monitor-noticias.log`, rotativo em 2 MB com três backups. Isso não é função de negócio do Kotlin; é infraestrutura operacional adicionada durante a migração. A configuração de proxy mascara senha em erro HTTP e usa DPAPI. Nenhuma evidência encontrada autoriza logar senha/token/cookie.

## Dependências Python

| Dependência | Versão | Uso | Necessária no estado atual | Licença/observação | Impacto portable |
|---|---|---|---|---|---|
| PySide6 | 6.9.1 | UI, multimedia | sim | LGPL/comercial com componentes Qt | alto |
| pytest | >=8,<10 | testes | não em runtime | MIT | deveria ser tratado como dependência de desenvolvimento no portable futuro |
| requests | >=2.32,<3 | HTTP/proxy/coletores | sim | Apache-2.0 | baixo/médio |
| beautifulsoup4 | >=4.12,<5 | parsing HTML | sim | MIT | baixo |
| lxml | >=5,<7 | XML/HTML | sim | BSD-3-Clause | médio/binário |
| pypdf | 6.18.0 | PDF vetorial | sim | BSD-3-Clause | baixo |
| pypdfium2 | 5.13.0 | render PDF/PDFium | sim | Apache/BSD + PDFium notices | alto/binário |
| Pillow | 12.3.0 | imagens/raster | sim | MIT-CMU | médio/binário |

`pytest` está no `requirements.txt` geral embora seja apenas de teste. Não foi removido neste passo.

## Binários/recursos externos

Kotlin portable aprovado usa `yt-dlp.exe`, `yt-dlp-stable.exe`, `deno.exe`, `ffmpeg.exe`, `ffprobe.exe` e o editor PyInstaller. O projeto Python conhece/usa esses motores em módulos correspondentes, mas o bundle portable final ainda não foi montado. O asset `pdf-default-cover.b64` foi preservado no passo do PDF.

## Testes

A árvore de testes possui diretórios `unit`, `integration`, `equivalence` e fixtures. A última execução completa sobre o mesmo runtime Python foi GitHub Actions run `34726977912`: Windows e Ubuntu `success`, 132 testes no Windows.

Resultado observado:

- TOTAL: 132
- PASS: 132
- FAIL: 0
- SKIP: 0 observado na saída pytest
- XFAIL: 0 observado na saída pytest
- duração do pytest Windows: aproximadamente 23 s entre início e conclusão; instalação de dependências não incluída.

Limitação essencial: essa suíte não prova o runtime principal, pois contém testes que esperam deliberadamente a ausência de repositories e o catálogo incompleto. O Passo 13 não alterou testes para fazê-los verdes.

Não foi possível clonar/executar localmente uma segunda suíte nesta sessão porque o ambiente de execução não possui resolução de rede para GitHub. O commit auditado difere do commit de runtime testado apenas em documentação, comprovado por comparação de commits.

## E2E e cenários operacionais

### Fluxo end-to-end solicitado

`ABRIR → BANCO` é suportado. O fluxo falha/bloqueia em `NOTÍCIAS/COLETA`, pois o controller padrão não possui `AutomationService`/repositories. Portanto:

**RESULTADO E2E: FALHA FUNCIONAL / BLOQUEADO EM BUSCA DE NOTÍCIAS.**

Não é legítimo alegar E2E aprovado usando fake runners, porque isso não reproduz a aplicação real.

### Reabertura / primeira execução

Criação de diretórios, prefs e SQLite possuem implementação/testes. Persistência básica é exercitada pela suíte. Reabertura completa com repositories reais: BLOQUEADA pela mesma lacuna estrutural.

### Sem internet / fonte indisponível

Coletores possuem tratamento isolado e testes controlados; comportamento global do Monitor real não pode ser aprovado enquanto repositories não estiverem ligados.

### ffmpeg/ffprobe ausentes

Extrator/editor possuem mensagens e guardas específicas. Integração portable real permanece `EM TESTE`.

### Paths com espaços/Unicode

Uso de `Path` e argumentos subprocess em lista reduz riscos; teste real do executável final em `C:\Teste Monitor de Noticias\` e path Unicode não foi realizado. `NÃO DETERMINADO PELO CÓDIGO ANALISADO` quanto ao bundle final.

### Encerramento

`MainUiController.close()` fecha automation quando existente e fecha bancos; `MainWindow` esconde no tray e `Sair` efetua close. Entretanto, como o runtime padrão não instancia automação de negócio, não houve teste de encerramento da topologia real completa. Extrator/editor possuem lifecycle próprio em seus módulos. Portable final deve verificar processos órfãos.

## Placeholders, código morto e funções adicionais

### Placeholders/ausências de produção relevantes

- `repositories/__init__.py`: declaração explícita de que business repositories não foram migrados.
- UI desabilita busca real quando `automation=None`.
- busca individual de demanda retorna mensagem de espera pelo NewsRepository.
- catálogo de vídeo declara `VIDEO_CATALOG_COMPLETE = False`.
- `PlaceholderPage` existe como classe genérica; as ferramentas migradas nos Passos 10–12 já não dependem do placeholder principal, mas a classe permanece disponível.

### Scaffolding sem função operacional relevante

Pacotes vazios/scaffolding como `extraction`, `pdf`, `utils` e `video` permanecem na árvore enquanto implementações reais vivem em outros pacotes. Não foram removidos neste passo.

### Funcionalidades Python sem origem direta Kotlin de negócio

- logging rotativo Python;
- DPAPI para senha do proxy (substitui armazenamento plaintext por decisão de segurança);
- arquitetura de ports/ThreadPoolExecutor para portar concorrência Kotlin sem expor coroutines à UI.

Não são apresentadas como novas funções de usuário.

## Regressões funcionais

### CRÍTICO

1. Runtime principal sem `NewsRepository`/`VideoRepository` e sem wiring do `AutomationService`: buscas normais, demandas e vídeos não funcionam na aplicação real.

### ALTO

1. Catálogo base de vídeos ausente; apenas dois extras Desktop aparecem.
2. `VideoTermStore` independente ausente.
3. Fluxos automáticos de notícias/demandas/vídeos não executam no runtime padrão.
4. Telas Notícias/Vídeos/Demandas/Termos/Fontes não podem ser consideradas funcionalmente equivalentes enquanto o motor central estiver bloqueado.

### MÉDIO

1. Resolver de URL Google News ausente; UI Python abre/copia o wrapper bruto.
2. Validações reais de Windows/startup/tray/processos/extrator/preview/PDF/vídeo ainda pendentes.

### BAIXO

1. `pytest` permanece em requirements de runtime.
2. scaffolding/pacotes vazios e classe PlaceholderPage permanecem no source.

## Fontes externas alteradas

Nenhuma mudança externa específica foi diagnosticada neste Passo 13 como causa das lacunas centrais. Os bloqueios acima são **erros/lacunas de migração**, não mudanças dos sites externos. Coletores que dependem da web continuam sujeitos a revalidação futura, mas isso não explica a ausência de repositories/wiring.

## Bloqueadores para gerar a versão portable

1. Implementar e validar `MIG-113` — repositories de negócio + wiring real.
2. Implementar `MIG-112` — catálogo completo de vídeos.
3. Resolver `MIG-024` — VideoTermStore independente.
4. Restabelecer os fluxos bloqueados `MIG-014/016/022/023/026/033/035–038`.
5. Revalidar telas `MIG-096–100` com motores reais.
6. Resolver login helper Globoplay `MIG-050` ou documentar condição final comprovada.
7. Tratar `MIG-079–083`: entry/build/workflow/binários/BUILD-SHA/hash.
8. Completar validações Windows reais dos itens ainda `EM TESTE`.
9. Rodar E2E real completo e reabertura/primeira execução/sem internet/fontes quebradas.
10. Testar paths com espaços e Unicode no executável final.
11. Verificar shutdown sem processos/threads órfãos.
12. Fazer exportações reais PDF/vídeo e downloads controlados com os binários do bundle.
13. Revisar licenças/notices de Qt/PDFium e dependências no pacote.

## Itens não bloqueadores / melhorias futuras

- separar `pytest` em requirements/dev tooling;
- remover scaffolding morto depois que a equivalência estiver fechada;
- limpeza estética/refactor que não altere comportamento;
- melhorias de logging/diagnóstico além do necessário.

Esses itens não devem ser confundidos com os bugs/lacunas acima.

## Correções realizadas no Passo 13

Nenhum código funcional foi alterado. A auditoria apenas corrigiu o **estado documental** e adicionou MIGs esquecidos. Não seria seguro implementar os repositories/catálogo/wiring como alteração incidental sem um passo próprio, pois isso modifica grande parte do motor de negócio.

## Estado final dos MIGs

- Total: 114
- APROVADO: 51
- EM TESTE: 36
- PENDENTE: 8
- BLOQUEADO: 19
- Rebaixados de APROVADO: `MIG-035`, `MIG-036`, `MIG-037`, `MIG-038`.
- Novos: `MIG-112`, `MIG-113`, `MIG-114`.

## Confirmação

`tysudess/noticias-monitor` permaneceu somente leitura e **NÃO FOI ALTERADO**.
