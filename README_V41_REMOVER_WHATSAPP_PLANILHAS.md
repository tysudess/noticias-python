# V41 — Remover WhatsApp e Planilhas do Central

## Objetivo

Retirar do programa:

- aba WhatsApp;
- aba Planilhas / Automação de Planilhas;
- navegação pela busca global para essas integrações;
- inicialização dos patches ligados à sessão compartilhada.

## Arquivos

SUBSTITUIR:
- `src/monitor_noticias/ui/sections.py`
- `src/monitor_noticias/app/application.py`

NOVO:
- `src/monitor_noticias/ui/removed_integrations_guard.py`

## O que permanece intacto

- Notícias
- Vídeos
- Demandas
- Fontes
- Histórico
- Termos
- Parar buscas
- Extrator de Notícias
- Capas
- Editor de PDF
- Extrator de Vídeos
- Editor de Vídeo
- Gravador de Tela
- Configurações
- Proxy Geral

Também permanecem ativos:
- correção de Proxy do Extrator de Vídeos;
- correção do toggle do Proxy Geral;
- correções de Capas;
- Proxy do Extrator de Matérias;
- link direto das notícias;
- botões das notícias dentro de Demandas.

## Código histórico

Os arquivos:
- `spreadsheet_automation_page.py`
- `whatsapp_browser_page.py`
- `whatsapp_browser_integration.py`
- `spreadsheet_shared_whatsapp_patch.py`
- `spreadsheet_keyboard_focus_patch.py`

podem permanecer no repositório. Eles não são instalados nem expostos pela V41.
Isso facilita rollback caso a integração seja retomada no futuro.

## Workflow

Para REMOVER AS ABAS do Central, NÃO é necessário alterar workflow.

Atenção:
o `build-portable.yml` atual ainda baixa e coloca o EXE grande da Automação
de Planilhas dentro do ZIP, embora ele fique sem uso na V41.

Isso não impede o programa de funcionar; apenas mantém peso desnecessário no
portable.

Se o objetivo for também eliminar esse ~85 MB do ZIP, faça depois uma limpeza
separada do `build-portable.yml`, removendo:
- PLANILHAS_RUNTIME_TAG
- PLANILHAS_RUNTIME_ASSET
- pasta tools/spreadsheet_automation no preparo do portable
- download do asset da Release
- validação de sheetExe/sheetConfig no ZIP.

Não é necessário rodar `Rebuild Planilhas Runtime` para a V41.

Depois de subir estes três arquivos, basta executar o build normal do Central.
