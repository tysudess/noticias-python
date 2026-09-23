# V38 — Pipeline completo WhatsApp → Google Planilhas

## O que estava faltando

A auditoria comparou o runtime atual com o motor antigo que preenchia a
planilha. O POST para o Apps Script continua praticamente igual. A falha está
principalmente ANTES do POST.

### 1. Formato incompatível entre Notícias e Automação

A aba Notícias estava compartilhando:

TÍTULO
LINK

Mas a Automação esperava:

LINK
VEÍCULO
TÍTULO
[autor]
DATA

A V38 corrige os dois lados:
- o botão WhatsApp do Central passa a enviar LINK / VEÍCULO / TÍTULO / DATA;
- a Automação também aceita o formato antigo TÍTULO / LINK;
- mensagem somente com link passa a tentar título/descrição da prévia do
  WhatsApp em vez de ser descartada imediatamente.

### 2. `message` e `message_create`

Os dois eventos agora podem alimentar o pipeline. Uma trava por ID evita dois
POSTs simultâneos da mesma mensagem.

### 3. Grupo enviado ao Apps Script

O código descobria o grupo corretamente, mas mandava:

`grupo: ""`

Agora envia o JID real do grupo monitorado.

### 4. Diagnóstico real do Apps Script

Antes, "AGUARDANDO" não dizia em qual etapa o processo parou.

Agora o LOG mostra:

[MONITOR V38] ...
[CONFIG MOTOR] grupos: 3 | Apps Script: CONFIGURADO
[GRUPO VALIDADO] ...
MENSAGEM CAPTURADA DO GRUPO: ...
NOTÍCIA IDENTIFICADA
[PLANILHA] ENVIANDO: ...
[PLANILHA] HTTP: 200
[PLANILHA] RESPOSTA: {...}
PLANILHA ATUALIZADA
Linha: ...

Com isso fica possível saber exatamente se o bloqueio está no WhatsApp,
parser, proxy/HTTP ou Apps Script.

## Arquivos a substituir

- `tools/planilhas_runtime_source/scripts/patch-whatsapp-web.js`
- `src/monitor_noticias/ui/url_tools.py`

## Workflow

NÃO precisa alterar o workflow.

Mas é necessário rodar o workflow já existente:

`Rebuild Planilhas Runtime`

porque `patch-whatsapp-web.js` é aplicado durante a geração do Electron.

Depois que o asset
`AutomacaoPlanilhas-Windows-Portable-v1.0.4.exe`
for atualizado na tag `planilhas-runtime-v1.0.4`, gere novamente o portable
normal do Central para incluir também o novo `url_tools.py`.

## Observação importante

O código-fonte do Google Apps Script (`doPost`) NÃO está no repositório
`noticias-python`. Portanto o cliente pode ser auditado completamente, mas o
contrato do lado servidor só pode ser confirmado pelo retorno registrado em:

`[PLANILHA] RESPOSTA: ...`

Se o log chegar a HTTP 200 e a resposta não tiver `sucesso:true`,
`success:true` ou `status:"OK"`, será necessário conferir o código/deployment
do Apps Script.
