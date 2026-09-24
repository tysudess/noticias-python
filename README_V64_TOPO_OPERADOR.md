# V64 — Topo refinado + busca removida + OPERADOR com todas as abas

## Objetivos

1. melhorar visualmente a faixa superior;
2. remover a caixa de busca do topo;
3. manter os chips de Proxy, Automação, usuário, Minha conta, Sair da conta e relógio com visual mais consistente;
4. ativar todas as abas/funções para o perfil `OPERADOR`.

## Arquivos

### NOVO

- `src/monitor_noticias/ui/header_refinement_patch.py`

### SUBSTITUIR

- `src/monitor_noticias/app/application.py`
- `tools/auth_server/Code.gs`

## O que muda no layout

- a caixa de busca superior é ocultada;
- o topo passa a ter espaçamento mais limpo;
- os chips superiores recebem borda, arredondamento e sombra padronizados;
- os botões `Minha conta` e `Sair da conta` ficam visualmente alinhados com o restante do cabeçalho;
- o relógio ganha um cartão visual mais consistente.

## O que muda na autenticação/permissões

O perfil `OPERADOR` agora usa `*`, ou seja, recebe todas as permissões.

### Importante

Se algum usuário do tipo OPERADOR tiver a coluna `PERMISSOES` preenchida manualmente na planilha, essa coluna continua tendo prioridade.

Se quiser que ele use o perfil completo do OPERADOR, deixe `PERMISSOES` em branco.

## Google Apps Script

Depois de substituir `tools/auth_server/Code.gs`, publique uma nova versão do Apps Script:

`Implantar -> Gerenciar implantações -> Editar -> Nova versão -> Implantar`

A URL `/exec` pode continuar a mesma.

## Workflow

NÃO PRECISA ALTERAR.
