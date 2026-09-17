# Adendo oficial MIG — Passo 15

Este documento complementa `docs/MIGRACAO_KOTLIN_PYTHON.md` sem reescrever o histórico do Passo 14.

## Commits congelados

- Kotlin: `tysudess/noticias-monitor@df1701ba5427a04954093e8ebed63f26abb2b2b7`, 2026-09-12T20:11:33Z.
- Python no início do gate: `tysudess/MONITOR-DE-NOTICAS-PYTHON@fb6773a534853645253c8641f2dace631333a8f8`, branch `migration/python-foundation`, 2026-09-13T01:10:37Z.

## Reavaliação dos MIG não aprovados

Todos os MIG que estavam `EM TESTE`, `PENDENTE` ou `BLOQUEADO` no Passo 14 foram reconsiderados contra as evidências do gate. A regra usada foi conservadora: teste unitário verde isolado não promove MIG cujo escopo exige interação real, binário externo, visualização humana ou build portable.

### Permanecem EM TESTE

`MIG-003`, `MIG-004`, `MIG-022`, `MIG-027`, `MIG-028`, `MIG-033`, `MIG-039`, `MIG-040`, `MIG-042`, `MIG-044`, `MIG-047`, `MIG-048`, `MIG-049`, `MIG-051`, `MIG-052`, `MIG-053`, `MIG-054`, `MIG-055`, `MIG-057`, `MIG-068`, `MIG-069`, `MIG-070`, `MIG-071`, `MIG-072`, `MIG-074`, `MIG-075`, `MIG-076`, `MIG-090`, `MIG-091`, `MIG-092`, `MIG-093`, `MIG-094`, `MIG-095`, `MIG-096`, `MIG-097`, `MIG-098`, `MIG-099`, `MIG-100`, `MIG-102`, `MIG-103`, `MIG-106`, `MIG-108`, `MIG-110`.

Motivos principais:

- DPAPI e Registry reais passaram no Windows, mas os MIG de segurança/integração mais amplos incluem fluxos de aplicativo e lifecycle além da chamada isolada.
- UI real inicializou, mas não houve sessão humana visual completa de cada tela.
- Editor de Vídeo não executou probe/preview/export com `ffmpeg.exe`/`ffprobe.exe` do conjunto que deverá acompanhar o futuro pacote.
- Extrator abriu pelo entry point após correção, mas downloads externos, updater e fechamento durante operação ainda não foram todos validados de ponta a ponta.
- PDF possui motor amplamente testado, mas o workspace visual e fechamento humano continuam dentro do estado `EM TESTE` onde já estavam.

### Permanecem PENDENTE

- `MIG-002` — raiz frozen/portable: CWD externo e caminho com espaços/acento foram aprovados em source mode, mas `sys.frozen` somente será provado na build futura.
- `MIG-061` — rotação/flip no PDF: suporte interno existe, porém ação visual ativa equivalente não foi comprovada.
- `MIG-079` a `MIG-083` — build/portable: propositalmente não executados no Passo 15.
- `MIG-114` — resolver Google News: componente existe, consumo pelo Dashboard V5 ativo não foi comprovado; não criar wiring por suposição.

### Permanece BLOQUEADO

- `MIG-050` — login interno Globoplay: `GloboplayLoginHelper.exe` é esperado pelo fluxo, porém a cadeia válida do workflow V8 auditado não comprovou sua construção/cópia. A presença no artefato aprovado é **NÃO DETERMINADO PELO CÓDIGO ANALISADO.**

### MIG novos

- `MIG-116` — **Lifecycle/Shutdown das ferramentas integradas — BLOQUEADO**.

Escopo: ao escolher `Sair` com operação de ferramenta ativa, provar encerramento/cancelamento coordenado de QThreads do Extrator, processo auxiliar conhecido e janelas top-level do Editor de Vídeo, sem órfãos nem corrupção. O `MainWindow.exit_application()` fecha controller/tray/janela principal, mas não existe coordenação explícita dessas ferramentas. Terminação forçada de thread Python não foi inventada.

## Achado corrigido sem novo MIG

No entry point real, a construção de `ExtractorPage` podia emitir o sinal `toggled` da qualidade antes de `cancel_button` existir. Isso derrubava a aplicação com `AttributeError`. Foi corrigido no próprio escopo de `MIG-106` usando uma guarda de inicialização; o motor, presets e download não foram alterados.

## Contagem oficial após Passo 15

Como nenhum MIG antigo foi promovido por inferência e foi criado apenas `MIG-116`:

- Total: **116 MIGs**.
- `APROVADO`: **63**.
- `EM TESTE`: **43**.
- `PENDENTE`: **8**.
- `BLOQUEADO`: **2** (`MIG-050`, `MIG-116`).

Os IDs `MIG-001` a `MIG-116` são permanentes. Novos achados recebem IDs maiores que 116.
