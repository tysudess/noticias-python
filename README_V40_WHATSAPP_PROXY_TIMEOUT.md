# V40 — WhatsApp Web: ERR_CONNECTION_TIMED_OUT com Proxy Geral

## Erro observado

Na aba WhatsApp:

`net::ERR_CONNECTION_TIMED_OUT at https://web.whatsapp.com/`

O Chrome abre e o Central mostra o Proxy Geral ativo, mas a página não carrega.

## Causa corrigida no código

O Proxy do Chrome é definido por:

`--proxy-server=http://HOST:PORT`

Esse argumento só é aplicado quando o processo Chrome nasce.

O `main.js` atual reutilizava qualquer Chrome já respondendo em `127.0.0.1:9223`
sem verificar com qual configuração de proxy ele havia sido iniciado.

Assim era possível ter:

- interface mostrando o Proxy Geral atual;
- motor recebendo as credenciais atuais;
- Chrome ainda rodando com proxy antigo, sem proxy ou estado de rede de uma
  execução anterior.

## Correções V40

### 1. Assinatura da configuração de rede

O runtime passa a salvar:

`data/whatsapp_chrome_network.json`

A senha NÃO é salva. É gravado somente SHA-256 da configuração completa.

Se host, porta, usuário, senha ou estado ligado/desligado mudarem, o Chrome
dedicado é encerrado e iniciado novamente usando o MESMO perfil persistente.

O login do WhatsApp permanece salvo em:

`data/whatsapp_chrome_profile`

### 2. Teste real antes de abrir o Chrome

Com Proxy Geral ativo, o runtime testa:

`https://web.whatsapp.com/`

usando exatamente:
- host;
- porta;
- usuário;
- senha.

Log esperado:

`TESTE WHATSAPP VIA PROXY: proxy-7dn.mb:6060`
`TESTE WHATSAPP VIA PROXY: OK (HTTP 200).`

Se esse teste der timeout, o problema é a rota/proxy até o WhatsApp e o
programa agora informa isso claramente em vez de abrir um Chrome que ficará
preso em ERR_CONNECTION_TIMED_OUT.

### 3. QUIC desativado

O Chrome compartilhado recebe:

`--disable-quic`

Isso força o fluxo web a permanecer no caminho TCP/HTTPS, mais previsível
através de proxy HTTP autenticado.

### 4. Segunda tentativa autenticada do Chromium

O patch do `whatsapp-web.js` passa a tratar:

- ERR_CONNECTION_TIMED_OUT
- ERR_TIMED_OUT
- ERR_PROXY_CONNECTION_FAILED
- ERR_TUNNEL_CONNECTION_FAILED
- ERR_PROXY_AUTH_REQUESTED

Nesses casos:
1. volta para `about:blank`;
2. limpa autenticação anterior;
3. reaplica usuário/senha do Proxy Geral;
4. tenta `web.whatsapp.com` novamente.

Não há fallback silencioso para internet direta.

## Arquivo a substituir

Somente:

`tools/planilhas_runtime_source/scripts/patch-whatsapp-web.js`

Este arquivo já inclui as correções anteriores V37, V38 e V38.1.

## Workflow

NÃO alterar `rebuild-planilhas-runtime.yml`.

Depois de subir o arquivo, executar o workflow existente:

`Rebuild Planilhas Runtime`

Quando ele atualizar:

`AutomacaoPlanilhas-Windows-Portable-v1.0.4.exe`

na tag:

`planilhas-runtime-v1.0.4`

gere novamente o portable normal do Central.

## Como interpretar o teste depois do build

### Caso A
Log:

`TESTE WHATSAPP VIA PROXY: OK`

mas Chromium ainda falha.

Nesse caso o HTTP proxy responde para o WhatsApp e devemos concentrar o
diagnóstico no Chromium/Puppeteer.

### Caso B
Log:

`O Proxy Geral não conseguiu acessar https://web.whatsapp.com/`

Nesse caso não é sessão, QR, LocalAuth nem Puppeteer. O próprio proxy não está
conseguindo alcançar o WhatsApp naquele momento.

### Caso C
Log:

`HTTP 407`

As credenciais do Proxy Geral foram rejeitadas.

## Observação

A documentação do Chromium confirma que `--proxy-server` é configuração de
lançamento do navegador. O Puppeteer suporta credenciais por `page.authenticate`.
A V40 mantém essa arquitetura, mas garante que Chrome, credenciais e
configuração atual do Central estejam sincronizados.
