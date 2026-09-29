# Central V90.2 — Correção do import de Startup

Base confirmada:

`29cd09681ce73fa82cb3eed15ab546f50ebbe11d`

## Erro real do GitHub Actions

Windows run 236 e Ubuntu run 64 interromperam a coleta do pytest com:

`ImportError: cannot import name 'WindowsStartupBackend' from
'monitor_noticias.windows.startup'`

A classe existe em:

`monitor_noticias.platform.startup`

porém o módulo histórico:

`monitor_noticias.windows.startup`

não a reexportava.

## Correção

O módulo de compatibilidade agora reexporta `WindowsStartupBackend`, assim como
já fazia com `StartupManager`, `WinRegBackend`, `LinuxAutostartBackend` e os
demais nomes históricos.

Nenhuma lógica de startup foi alterada.

## Workflow

**WORKFLOW: NÃO PRECISA ALTERAR**
