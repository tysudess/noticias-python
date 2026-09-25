# V73 — Refinamento visual completo + Home repaginada + Tribuna da Bahia + ajuste seguro de velocidade do Extrator

## Objetivos

Esta versão aplica o pacote de melhorias solicitado:

1. **refino visual global** em todas as abas, sem alterar funcionalidades;
2. **melhoria minuciosa** de botões, sombras, tipografia e acabamento geral;
3. **repaginação da aba Início**;
4. remoção do card **Resumo do dia**;
5. remoção do card **Dicas**;
6. expansão do card ao lado de **Agendamento automático** para ocupar o espaço liberado;
7. reforço do layout do bloco **Monitoramento**;
8. inclusão de **Tribuna da Bahia** na área de Fontes da Bahia;
9. ajuste conservador para o **Extrator de Notícias iniciar/executar em modo mais rápido**, reduzindo tempo morto e priorizando modo rápido.

## O que esta versão faz

### 1) Layout / Design
- aprimora aparência de botões em toda a aplicação;
- melhora sombras e profundidade visual;
- uniformiza tipografia;
- melhora cards, campos, listas, tabelas, abas e navegação lateral;
- reforça o visual da sidebar, deixando os itens mais consistentes.

### 2) Aba Início
- esconde o card **Resumo do dia**;
- esconde o card **Dicas**;
- faz **Agendamento automático** ocupar melhor o espaço;
- reorganiza os cards inferiores para aproveitar melhor a área;
- remove a área ilustrativa/placeholder do card **Monitoramento** quando detectada;
- melhora tamanhos de fonte e leitura geral da Home.

### 3) Fontes da Bahia
- injeta **Tribuna da Bahia** nas coleções detectadas da aba **Fontes**.

### 4) Extrator de Notícias
- ativa um modo rápido conservador;
- reduz tempo morto de navegação/espera passiva;
- sinaliza ao runtime integrado que deve priorizar extração rápida;
- mantém compatibilidade com o fluxo existente.

## Arquivos

### NOVOS
- `src/monitor_noticias/ui/sources_bahia_patch.py`
- `src/monitor_noticias/ui/news_extractor_speed_patch.py`

### SUBSTITUIR
- `src/monitor_noticias/app/application.py`
- `src/monitor_noticias/ui/home_dashboard_patch.py`
- `src/monitor_noticias/ui/visual_refinement_patch.py`
- `tools/news_extractor/monitor-main.js`

## Observações

- Esta versão foi pensada para **não mexer na regra de negócio principal**.
- A inclusão de **Tribuna da Bahia** é feita por patch de interface/modelo detectado em runtime.
- O ganho de velocidade do extrator é **seguro e conservador**: ele reduz tempo morto e favorece modo rápido, sem reescrever o motor fechado da extração.

## Workflow

Não precisa criar outro repositório.
Pode continuar no mesmo projeto atual.

Depois de subir os arquivos, gere normalmente o próximo build do Central.
