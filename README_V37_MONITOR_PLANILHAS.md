# V37 — Automação Planilhas: conectado mas não recebe mensagens

## Sintoma

A interface mostrava:

- WhatsApp: CONECTADO
- Motor: RODANDO
- 3 grupos carregados
- Planilha: AGUARDANDO

mas mensagens novas colocadas nos grupos não eram processadas.

## Causas tratadas

### 1. `browserURL` criava nova aba a cada inicialização

O whatsapp-web.js 1.34.7 executa:

`puppeteer.connect(...)`
`browser.newPage()`

quando usa `browserURL`.

Na arquitetura do Central isso podia criar várias abas do WhatsApp dentro do
mesmo Chrome persistente após reinícios do motor.

A V37 muda o Client.js durante o build para:

1. reutilizar primeiro uma aba `web.whatsapp.com` já existente;
2. senão reutilizar `about:blank`;
3. somente criar uma nova aba se nenhuma das anteriores existir.

Assim o motor trabalha na mesma aba/sessão do Chrome compartilhado.

### 2. Recuperação quando `Msg.on('add')` não entrega a mensagem

O listener oficial continua ativo.

Além dele, a V37 faz uma varredura a cada 1,5 segundo das mensagens recentes
já carregadas pelo WhatsApp Web. Ela serve somente como recuperação quando o
evento interno falha.

Um Set de IDs impede que evento normal + varredura enviem a mesma mensagem
duas vezes.

Na inicialização, somente mensagens dos últimos 3 minutos ficam elegíveis para
recuperação; histórico antigo não é importado.

### 3. IDs de grupos mais robustos

O motor agora reconhece IDs em diferentes representações:

- string normal `...@g.us`;
- `_serialized`;
- objeto `{user, server}`;
- ID completo da mensagem contendo o `...@g.us`.

Isso evita ignorar mensagem porque a versão atual do WhatsApp Web entregou o
JID em formato de objeto.

## Log esperado

Depois que o WhatsApp ficar pronto:

`[MONITOR V37] aba compartilhada + eventos + varredura de recuperação ativos`

Ao chegar uma mensagem em um dos três grupos:

`MENSAGEM CAPTURADA DO GRUPO: 556...@g.us | tipo: chat | própria: false`

Depois, se o texto estiver no formato esperado:

`NOTÍCIA IDENTIFICADA`

e finalmente:

`PLANILHA ATUALIZADA`
`Linha: ...`

## Arquivo a substituir

- `tools/planilhas_runtime_source/scripts/patch-whatsapp-web.js`

## Workflow

NÃO alterar o workflow.

É necessário executar o workflow existente:

`Rebuild Planilhas Runtime`

porque a V37 altera o whatsapp-web.js dentro do runtime durante o build e
também aplica o hotfix ao `engine/index.js`.

Depois que o asset
`AutomacaoPlanilhas-Windows-Portable-v1.0.4.exe`
for substituído na tag `planilhas-runtime-v1.0.4`, gere novamente o portable
normal do Central.

## Teste recomendado

1. Abra o Central.
2. Entre em Planilhas.
3. Confirme CONECTADO / RODANDO.
4. Abra LOG e confirme `[MONITOR V37]`.
5. Envie uma NOVA matéria para um dos três grupos.
6. Confirme `MENSAGEM CAPTURADA DO GRUPO`.
7. Confirme `NOTÍCIA IDENTIFICADA`.
8. Confirme `PLANILHA ATUALIZADA`.

Se aparecer `MENSAGEM CAPTURADA DO GRUPO` mas não `NOTÍCIA IDENTIFICADA`,
o recebimento já estará resolvido e o próximo ponto será somente o formato da
mensagem enviada ao grupo.
