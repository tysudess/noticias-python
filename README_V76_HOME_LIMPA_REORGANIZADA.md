# V76 — Home limpa e reorganizada

## Correção definitiva

A V73 tentava ocultar os cards da Home depois que eles já haviam sido
construídos. Isso não foi suficiente.

A V76 altera os builders da `HomePage` ANTES de a janela ser criada.

Assim os blocos não são apenas escondidos: eles deixam de ser criados.

## Removido

- `Resumo do dia`
- `Dicas`

## Reorganizado

### Agendamento automático

Passa a ocupar sozinho toda a largura da linha onde antes dividia espaço com
`Resumo do dia`.

Os três blocos continuam visíveis:

- Notícias
- Demandas
- Vídeos

### Parte inferior

Ficam apenas:

- Top 10 veículos
- Últimas atividades

Os dois passam a dividir o espaço em duas colunas equilibradas.

## Mantido

- métricas superiores;
- Monitoramento;
- Ações rápidas;
- agendamentos;
- Top 10 veículos;
- Últimas atividades;
- todas as funções e atualizações dinâmicas da Home.

## Arquivos

NOVO:
- `src/monitor_noticias/ui/home_layout_v76_patch.py`

SUBSTITUIR:
- `src/monitor_noticias/app/application.py`

ADICIONAR:
- `tests/unit/test_home_layout_v76.py`

## Windows e Ubuntu

A alteração é compartilhada.

## WORKFLOW

NÃO PRECISA ALTERAR.
