# V43 — Valor Econômico somente pelo Gmail

A capa do VALOR ECONÔMICO passa a usar exclusivamente:

Gmail -> Apps Script -> PDF -> Página 1 -> imagem da capa

FrontPages e PressReader não são mais usados automaticamente para o Valor.

O Washington Post continua com o fluxo V42 pelo FrontPages.

Também foi reforçada a leitura da resposta do Apps Script para aceitar:
- page / pageNumber / page_number / pagina
- pages / attachments / files
- dataBase64 / data_base64 / base64
- filename / fileName / name

Se o Gmail não entregar a Página 1, o Central mostra o erro e não substitui
a capa por uma imagem da internet.

Arquivos:
- SUBSTITUIR: src/monitor_noticias/capas_tool/app/valor_email_pdf.py
- NOVO: src/monitor_noticias/ui/covers_valor_gmail_only_patch.py
- SUBSTITUIR: src/monitor_noticias/app/application.py

Workflow:
- NÃO alterar workflow.
- NÃO executar Rebuild Planilhas Runtime.
- Executar somente o build normal do Central.
