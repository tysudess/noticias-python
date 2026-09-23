# V44 — Melhorar dashboard da página Início

## Objetivo

Ajustar a Home do Central sem reescrever toda a página:

1. aumentar textos que estavam pequenos;
2. trocar "Central pronta para monitorar" por "Monitoramento";
3. retirar a área "Resumo do dia";
4. fazer "Agendamento automático" ocupar esse espaço;
5. remover a ilustração/placeholder da área central de monitoramento;
6. deixar a área de monitoramento usar melhor o espaço disponível.

## Estratégia

Como o pedido foi pontual e o restante da Home já está funcional, a V44
aplica um patch visual em runtime sobre a página Início existente.

Assim evitamos reescrever a tela inteira e reduzimos risco de regressão.

## O que a V44 faz

- aumenta a tipografia dos títulos, subtítulos e botões da Home;
- renomeia o card principal para `Monitoramento`;
- esconde o card `Resumo do dia`;
- expande `Agendamento automático` para ocupar a linha;
- esconde a ilustração/placeholder grande da área central de monitoramento;
- expande os blocos restantes do card de monitoramento.

## Arquivos

NOVO:
- `src/monitor_noticias/ui/home_dashboard_patch.py`

SUBSTITUIR:
- `src/monitor_noticias/app/application.py`

## Workflow

NÃO precisa alterar workflow.
NÃO precisa executar Rebuild Planilhas Runtime.

Basta subir os dois arquivos e gerar novamente o build normal do Central.
