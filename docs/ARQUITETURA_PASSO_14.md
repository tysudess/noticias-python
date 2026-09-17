# Arquitetura — Passo 14: composição e runtime real

## Escopo

Este documento registra apenas a composição introduzida/fechada no Passo 14. Ele não substitui os contratos de motor já documentados em `ARQUITETURA.md`; serve como adendo da arquitetura de execução do Monitor principal.

Fonte da verdade Kotlin: `tysudess/noticias-monitor@df1701ba5427a04954093e8ebed63f26abb2b2b7` mais as transformações do workflow V8 da release aprovada.

Regra permanente: não completar lacunas por hipótese. Quando algo não é comprovado: **NÃO DETERMINADO PELO CÓDIGO ANALISADO.**

## Composition root

O runtime de produção é montado por `AppContainer.build()`:

```text
run.py
  └─ monitor_noticias.app.application.main
      └─ Application
          └─ AppContainer.build
              ├─ AppPaths
              ├─ SharedPreferences
              ├─ NewsDb
              ├─ VideoDb
              ├─ ProxySettings
              ├─ HttpClient
              ├─ GoogleNewsCollector
              ├─ NewsLatestCollector
              ├─ YouTubeCollector
              ├─ WebsiteVideoCollector
              ├─ DirectVideoPageResolver
              ├─ GloboplayEditionCollector
              ├─ GloboplayTrechosCollector
              ├─ GloboplayJarvisCollector
              ├─ NewsRepository
              ├─ VideoTermStore
              ├─ VideoRepository
              ├─ RuntimeNewsRunner
              ├─ RuntimeVideoRunner
              ├─ AutomationSettings
              ├─ AutomationService
              ├─ StartupManager
              └─ RuntimeUiController
                  └─ MainWindow
```

`AppContainer` não executa matching, scraping nem SQL de negócio. Ele somente instancia os componentes existentes e entrega dependências concretas.

## Pipeline de notícias

```text
MainWindow / NewsPage
  → RuntimeUiController.search_news()
  → AutomationService.search_news()
  → RuntimeNewsRunner.search_news()
  → NewsRepository.search()
      → planejamento de queries
      → GoogleNewsCollector / NewsLatestCollector
      → matching existente
      → deduplicação/storyKey
      → NewsDb.insertNews()
  → AutomationState
  → RuntimeUiController.sync_automation_state()
  → NewsDb.listRecent()
  → UI
```

O proxy é lido pelo `HttpClient` ligado aos collectors; não existe segundo motor HTTP criado na UI.

## Pipeline de demandas

```text
UI
  → RuntimeUiController
  → AutomationService
  → RuntimeNewsRunner
  → NewsRepository.search_demand / search_all_demands
  → collectors e matching existentes
  → NewsDb + status da demanda
  → estado de automação
  → UI
```

A busca individual deixou de depender do fallback de `MainUiController`: em produção o objeto usado é `RuntimeUiController`.

## Pipeline de vídeos

```text
VideosPage
  → RuntimeUiController.search_videos()
  → AutomationService.search_videos()
  → RuntimeVideoRunner.search_videos()
  → VideoRepository.search()
      → VideoTermStore
      → catálogo completo VideoSourceCatalog portado
      → source-scan x term-query
      → YouTube / portal / Globoplay Edições / Trechos / Jarvis
      → direct-page enrichment
      → VideoMatchPolicy / matching existente
      → canonicalização / merge
      → VideoDb.insert()
  → AutomationState
  → RuntimeUiController
  → VideoDb.listRecent()
  → UI
```

Os extras Desktop g1 e Domingo Espetacular continuam extras; não substituem o catálogo base.

## Termos independentes de vídeo

`VideoTermStore` permanece separado dos termos de notícias e usa as chaves/migração portadas do Kotlin. A tela Termos chama o store real através do `RuntimeUiController`; não há mais bloqueio de produção para a edição dessa lista.

## Automação

O `AutomationService` é criado pelo composition root e iniciado por `automation.start()`. As lanes de notícias, demandas e vídeos recebem runners concretos.

Contratos de intervalo/agendamento continuam no módulo de automação; o composition root não replica essas regras.

## Atualização da UI

`RuntimeUiController.sync_automation_state()` espelha progresso, busy/status, duração, fontes instáveis e links novos. Quando uma lane transita de ocupada para concluída, o controller relê bancos e listas de termos/demandas para que a UI represente o estado persistido.

## Notificação e tray

`MainWindow` entrega o notifier do tray ao controller runtime. O controller troca o callback de notificação do `AutomationService`; a lógica de disparo continua no serviço de automação.

## Resolver Google News

`networking/google_news_resolver.py` porta o mecanismo de `GoogleNewsUrlResolver.kt`. No entanto, a auditoria do `DashboardV5Main.kt` do baseline não encontrou uso direto comprovado do resolver nas ações do dashboard. Por isso ele não foi forçado artificialmente nas ações Abrir/Copiar/WhatsApp da UI Python e `MIG-114` permanece `PENDENTE`.

## Placeholders deliberados

Os controles deliberadamente não funcionais do editor de vídeo permanecem assim, conforme o motor ativo e `MIG-077`. Eles não são dívida de wiring do Monitor principal e não devem ser implementados por inferência.

`MainUiController` conserva fallback para construção sem automação, útil para injeção/testes. O caminho normal de produção não usa esse fallback: recebe `RuntimeUiController` do `AppContainer`.

## Evidência automatizada

Run determinístico `34729628580`:

- Windows: compile + pytest completo — sucesso;
- Ubuntu: compile + pytest completo — sucesso;
- 141 testes na suíte completa.

Run live `34729671873`:

```text
LIVE NEWS OK found=22 new=22 stored=22
LIVE VIDEO COLLECTOR OK items=15
```

O teste live é evidência adicional de borda externa; os testes determinísticos continuam sendo a proteção primária contra regressão.

## Limites do Passo 14

- nenhum portable foi gerado;
- nenhum instalador foi criado;
- `MIG-079`–`MIG-083` continuam pendentes;
- validação humana integral das telas continua fora da aprovação automática;
- itens já marcados `EM TESTE` em Windows/DPAPI, mídia, extrator, PDF e editor de vídeo permanecem em seus próprios estados;
- o repositório Kotlin é somente referência e não foi alterado.
