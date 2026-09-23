# V46 — Colocar ícone no programa

## Objetivo

Aplicar o novo ícone futurista da Central no programa.

## O que esta versão faz

- adiciona o ícone do app em PNG;
- adiciona o ícone do app em ICO;
- cria um carregador robusto do ícone;
- aplica o ícone ao `QApplication`;
- aplica o ícone ao `MainWindow`;
- mantém as funcionalidades atuais sem alteração.

## Arquivos

NOVO:
- `src/monitor_noticias/assets/app_icon.png`
- `src/monitor_noticias/assets/app_icon.ico`
- `src/monitor_noticias/ui/app_icon_loader.py`

SUBSTITUIR:
- `src/monitor_noticias/app/application.py`

## Observação importante sobre build do Windows

Esta versão já coloca o ícone dentro do programa (janela/barra/tarefa) em runtime.

Se você também quiser garantir que o EXE final do Windows apareça com esse
mesmo ícone no arquivo executável do Explorer, o ideal é também apontar o
`.spec` do PyInstaller para:

`src/monitor_noticias/assets/app_icon.ico`

Como eu não alterei o workflow aqui, esta V46 foca no programa em si.
Se quiser, no próximo passo eu posso te entregar uma V46.1 ajustando o
`MonitorDeNoticias.spec` para o EXE sair com esse ícone também.

## Workflow

Para aplicar o ícone dentro do programa:
- NÃO precisa alterar workflow.

Se depois você quiser o ícone embutido também no executável final:
- aí sim vale revisar o `.spec` do PyInstaller.
