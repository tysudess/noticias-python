# V30 - WhatsApp compartilhado

Arquivos completos gerados para `tysudess/noticias-python`.

## Arquivos novos
- `src/monitor_noticias/ui/whatsapp_browser_page.py`
- `src/monitor_noticias/ui/whatsapp_browser_integration.py`
- `src/monitor_noticias/ui/spreadsheet_shared_whatsapp_patch.py`

## Arquivos substituídos
- `src/monitor_noticias/app/application.py`
- `tools/planilhas_runtime_source/engine/index.js`
- `tools/planilhas_runtime_source/main.js`

## Workflow
Não há alteração de workflow nesta versão.
O workflow existente `.github/workflows/rebuild-planilhas-runtime.yml` já:
1. baixa o Chrome for Testing portátil;
2. inclui `chrome-portable` no runtime Electron;
3. recompila `tools/planilhas_runtime_source`;
4. substitui o asset `AutomacaoPlanilhas-Windows-Portable-v1.0.4.exe`.

Depois de subir os arquivos:
1. execute `Rebuild Planilhas Runtime`;
2. confirme o asset atualizado na tag `planilhas-runtime-v1.0.4`;
3. gere um novo portable do Central pelo workflow normal.

## Arquitetura
- Perfil fixo: `<Central>/data/whatsapp_chrome_profile`
- Remote debugging: `http://127.0.0.1:9223`
- O Chrome é lançado pelo runtime usando o Chrome portátil já empacotado.
- `whatsapp-web.js` usa `browserURL` e `NoAuth`; a autenticação fica no perfil real do Chrome.
- `LOGOUT/auth timeout` não apagam mais o perfil.
- Sessão expirada encerra somente o motor e exige reconexão manual.
