# Relatório de fechamento técnico — Passo 14

## 1. Repositório trabalhado
`tysudess/MONITOR-DE-NOTICAS-PYTHON`.

## 2. Branch
`migration/python-foundation`.

## 3. Fonte da verdade
`tysudess/noticias-monitor@df1701ba5427a04954093e8ebed63f26abb2b2b7` mais as transformações do workflow V8 da release aprovada.

## 4. Objetivo do passo
Eliminar o bloqueio estrutural do Passo 13 conectando os motores já migrados em um runtime real, sem reescrever seus contratos.

## 5. Composition root
Criado `AppContainer` em `src/monitor_noticias/app/composition.py`.

## 6. Inicialização real
Fluxo: `run.py → Application → AppContainer → RuntimeUiController → MainWindow`.

## 7. Banco de notícias
`NewsDb` real é criado pelo container e usado pelo repository/runtime.

## 8. Banco de vídeos
`VideoDb` real é criado pelo container e usado pelo repository/runtime.

## 9. Preferências
`SharedPreferences` portable é instanciado a partir de `data/prefs/monitor_prefs.properties`.

## 10. Proxy
`ProxySettings` é migrado/carregado no composition root; `HttpClient` é criado a partir das configurações de proxy e entregue aos collectors.

## 11. NewsRepository
Criado/conectado o repository de negócio com Google News, Últimas Notícias, planejamento, matching, dedupe e persistência já portados.

## 12. VideoRepository
Criado/conectado o repository de negócio com os collectors de vídeo já migrados, matching, canonicalização, merge e persistência.

## 13. VideoTermStore
Portado e conectado como armazenamento independente de termos de vídeo, sem fundir a lista com termos de notícias.

## 14. Catálogo de vídeo
O catálogo base completo foi portado do `VideoSourceCatalog.kt`; g1 e Domingo Espetacular permanecem extras Desktop, não substitutos do catálogo.

## 15. RuntimeNewsRunner
Implementado como adaptador entre `AutomationService`, preferências/seleção e `NewsRepository`.

## 16. RuntimeVideoRunner
Implementado como adaptador entre `AutomationService`, seleção de fontes e `VideoRepository`.

## 17. AutomationService
Passou a receber runners reais no caminho de produção e é iniciado por `AppContainer.build()`.

## 18. Busca normal de notícias
O botão/ação de busca chega ao repository real e ao SQLite; comprovado por teste de composição e smoke live.

## 19. Busca por período
O runner encaminha limites de período ao `NewsRepository` existente; nenhum segundo algoritmo de janela foi criado na UI.

## 20. Demandas
Busca de todas as demandas usa runner/repository real. A busca individual foi ligada no `RuntimeUiController`; permanece `EM TESTE` no MIG por falta de validação específica suficiente para promoção conservadora.

## 21. Busca de vídeos
UI → automação → runner → repository → matching → SQLite → UI foi coberto por teste de composição controlado.

## 22. Automação de notícias
Scheduler com relógio controlado foi exercitado com `RuntimeNewsRunner`/`NewsRepository`/SQLite reais.

## 23. Automação de demandas
O bloqueio estrutural foi removido e a lane recebe runner real; os contratos de intervalo já existentes voltam ao estado aprovado conforme a evidência combinada dos testes de automação e composição.

## 24. Automação de vídeos
A lane de vídeo recebe runner real e preserva os horários configurados no módulo de automação.

## 25. Estado da UI
`RuntimeUiController` espelha busy, progresso, status, duração, fontes instáveis e conjuntos de links novos.

## 26. Refresh após busca
Ao detectar conclusão de lane, o controller relê bancos e listas persistidas antes de emitir o estado à UI.

## 27. Tray/notificação
`MainWindow` entrega o notifier real ao controller runtime; o callback do `AutomationService` passa a utilizar o tray.

## 28. run.py
O entrypoint foi corrigido para o layout `src/` do checkout, sem depender de `PYTHONPATH` externo para localizar o pacote.

## 29. Resiliência
Testes cobrem fonte com erro seguida de fonte com sucesso, cancelamento e seleção vazia de fontes sem trocar o repository real por fake.

## 30. Testes determinísticos
Workflow `Python migration tests`, run `34729628580`, SHA `b5f287b058031ae4b6ee7cb77e705a58a330dab4`: Windows e Ubuntu aprovados em compile e pytest completo. A suíte possui 141 testes.

## 31. Falha Windows encontrada durante o passo
Um teste de scheduler era não determinístico: o fake criava notícia alguns milissegundos depois do `to_ms` calculado pelo repository. O dado era corretamente filtrado no Windows. O teste foi corrigido para timestamp fixo; produção não foi alterada.

## 32. Smoke live de notícias
Run `34729671873`, SHA `0c5a691c6cd1eb59bbabaa1dd4b57570cb9d735c`: `LIVE NEWS OK found=22 new=22 stored=22`.

## 33. Smoke live de vídeo
Mesmo run: `LIVE VIDEO COLLECTOR OK items=15` usando o coletor real configurado para g1.

## 34. Google News URL resolver
O equivalente Python existe, mas a auditoria do `DashboardV5Main.kt` do baseline não comprovou chamada direta ao resolver nas ações do dashboard. Por isso não foi inventado wiring visual; `MIG-114` permanece `PENDENTE`.

## 35. Placeholders
Placeholders deliberados do editor de vídeo permanecem deliberadamente sem função conforme `MIG-077`. O fallback sem automação do controller-base não é o caminho de produção.

## 36. Atualização MIG
Criado `MIG-115` para composition root/inicialização real. `MIG-112`, `MIG-113` e `MIG-115` estão aprovados. Os bloqueios de runtime dos MIGs 014/016/023/024/026/035–038 foram removidos com evidência; telas 096–100 foram apenas para `EM TESTE`.

## 37. Totais MIG após o passo
Total 115: `APROVADO=63`, `EM TESTE=43`, `PENDENTE=8`, `BLOQUEADO=1`.

## 38. O que não foi feito
Não foi gerado portable, instalador, release ou alteração do motor por melhoria. `MIG-079`–`MIG-083` permanecem pendentes. Não foi declarada validação manual humana inexistente.

## 39. Estado de fechamento
O bloqueio estrutural central do Passo 13 está resolvido e provado por integração determinística e smoke live. O Passo 14 pode ser fechado para o seu escopo de composição/runtime. Isso **não** significa que a migração inteira está concluída: os MIGs `EM TESTE`, `PENDENTE` e `BLOQUEADO` continuam valendo individualmente.

---

### Regra de rastreabilidade

Nenhum resultado acima deve ser usado para promover automaticamente outro MIG. Cada MIG conserva seu próprio critério objetivo. Se uma funcionalidade não estiver determinada pelo baseline ou pelas transformações válidas da release: **NÃO DETERMINADO PELO CÓDIGO ANALISADO.**
