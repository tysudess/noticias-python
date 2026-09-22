# V33 — Teclado na aba Planilhas incorporada

## Diagnóstico confirmado pela tela
O Electron incorporado recebe mouse, mas o teclado não chega aos inputs HTML.

O código antigo chamava `SetFocus()` no HWND principal do Electron.
No Chromium/Electron quem recebe WM_KEYDOWN/WM_CHAR é normalmente o child
`Chrome_RenderWidgetHostHWND`.

## Correção V33
NOVO:
- `src/monitor_noticias/ui/spreadsheet_keyboard_focus_patch.py`

SUBSTITUIR:
- `src/monitor_noticias/app/application.py`

O patch:
- detecta o clique físico dentro da área incorporada;
- localiza recursivamente o child `Chrome_RenderWidgetHostHWND`;
- usa `AttachThreadInput`;
- transfere `SetFocus` para o renderer Chromium;
- repete o foco alguns milissegundos após o clique para não competir com
  o próprio processamento do mouse pelo Electron.

## Workflow
Não precisa alterar workflow.
Também não precisa executar `Rebuild Planilhas Runtime` para esta V33,
porque a correção é somente no Python/PySide6 do Central.

Basta subir os dois arquivos e gerar um novo portable normal do Central.

## Teste
Na aba Planilhas > Configurações:
1. clique dentro de Apps Script URL;
2. digite algumas letras;
3. use Backspace;
4. teste Ctrl+A e Ctrl+V;
5. teste também Caminho do Chrome e IDs dos grupos.

Os campos de Proxy podem continuar desabilitados quando o Proxy Geral é
gerenciado pelo Central; isso é esperado.
