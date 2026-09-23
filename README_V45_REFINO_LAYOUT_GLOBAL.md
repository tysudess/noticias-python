# V45 — Refinar layout global do programa

## Objetivo

Melhorar o design do Central sem mexer em nenhuma funcionalidade.

## O que a V45 refina

- botões com visual mais moderno;
- sombras sutis em botões e cards;
- tipografia base mais consistente;
- bordas, campos e combos com acabamento melhor;
- tabs mais elegantes;
- tabelas/listas com aspecto mais limpo;
- tooltips, menus e scrollbars refinados;
- melhoria geral de leitura e contraste;
- preservação da lógica atual do programa.

## Estratégia

A V45 aplica um patch visual global em runtime usando:
- stylesheet do Qt;
- tipografia base;
- polimento leve de widgets;
- sombras suaves por `QGraphicsDropShadowEffect`.

Não altera regras de negócio nem fluxo funcional.

## Arquivos

NOVO:
- `src/monitor_noticias/ui/visual_refinement_patch.py`

SUBSTITUIR:
- `src/monitor_noticias/app/application.py`

## Observações

- Esta versão foi feita para melhorar o layout de forma ampla e segura.
- Como é um refinamento global, ele afeta praticamente todas as telas:
  Início, Notícias, Demandas, Fontes, Capas, Extratores, Editor de PDF,
  Editor de Vídeo, Configurações etc.
- Nenhuma funcionalidade foi removida.

## Workflow

NÃO precisa alterar workflow.
NÃO precisa executar Rebuild Planilhas Runtime.

Basta subir os arquivos e gerar o build normal do Central.
