# Central V88 — Login e Extrator: desempenho e confiabilidade

Base conferida antes da alteração:

`471bcd1bd61209029217738ab202040278edf005`

## Escopo desta versão

A V88 é a primeira etapa da estabilização geral solicitada.

Ela trata primeiro os dois pontos mais sensíveis pedidos nesta etapa:

1. demora na certificação/validação do login;
2. velocidade e confiabilidade do Extrator de Notícias.

Nenhuma alteração é feita em Android.

## 1. Login

### O que a revisão encontrou

A Central continua obedecendo à regra definida na V72:

- abre o programa;
- lê o token protegido;
- faz uma validação real no Apps Script;
- entra;
- não revalida a cada 30 minutos.

A validação de abertura NÃO foi removida.

No cliente desktop, cada chamada ao Apps Script criava uma nova
`requests.Session`, portanto conexões HTTP/TLS não podiam ser reaproveitadas
entre operações da mesma execução.

Além disso, havia apenas um timeout geral de 18 segundos, sem separar o tempo
para conseguir conectar do tempo necessário para o Apps Script processar a
requisição.

### Mudanças da V88

`src/monitor_noticias/auth/client.py` agora:

- mantém uma `requests.Session` durante a vida do `AuthRuntime`;
- permite keep-alive e reaproveitamento de conexão quando o servidor/proxy
  permitir;
- mantém a regra V71: com Proxy Geral ativo não herda proxy do ambiente;
- mantém SSL normal fora do proxy corporativo autorizado;
- usa timeout de conexão mais curto e mantém 18 s para leitura/processamento;
- mede o tempo real de GET, POST, login e validate;
- não registra token, senha ou credencial do proxy;
- o botão de teste do login passa a informar o tempo em milissegundos.

### Por que ainda pode haver demora

A revisão do `tools/auth_server/Code.gs` mostrou que a validação do token no
Apps Script ainda:

- obtém um `ScriptLock`;
- percorre a planilha de sessões;
- percorre a planilha de usuários;
- atualiza `ULTIMA_VALIDACAO`;
- percorre dispositivos;
- atualiza `ULTIMO_ACESSO`.

Isso significa que parte relevante da demora pode estar no Apps Script/Google
Sheets, especialmente em cold start ou quando a planilha cresceu.

A V88 adiciona a medição real no cliente antes de modificar o servidor. Assim
podemos separar:

- tempo da rede/proxy;
- tempo do Apps Script.

A otimização do `Code.gs` deve ser feita na próxima etapa, porque exige
reimplantação do Web App e é melhor não misturar a troca do servidor com a
primeira validação do novo cliente.

## 2. Extrator de Notícias

### Problema encontrado

Antes, para cada matéria:

Central -> abre um novo Electron -> carrega Node/engine -> extrai -> encerra.

Isso faz a Central pagar repetidamente:

- inicialização do Electron;
- carregamento de jsdom/Readability;
- inicialização do Undici;
- criação do ProxyAgent;
- preparação do motor.

### Mudança principal

A V88 cria um worker persistente:

Central -> inicia Electron headless na primeira matéria -> reutiliza o mesmo
worker nas próximas extrações.

Enquanto Proxy Geral e parâmetros de rede permanecerem iguais, o processo
continua vivo.

Se a configuração do Proxy Geral mudar, a Central detecta a assinatura diferente,
encerra o worker antigo e inicia um novo com os dados atuais.

### Confiabilidade

O motor atual V1.25.19 e todos os fallbacks já existentes são preservados.

A V88 acrescenta uma conferência conservadora do resultado.

Uma segunda leitura só ocorre quando:

- a primeira tentativa falha por erro que pode ser transitório; ou
- título/corpo retornam claramente curtos ou suspeitos.

Não repete automaticamente erros como:

- 401;
- 403;
- 404;
- 407;
- falha explícita de credenciais/proxy.

Quando duas leituras produzem resultado, fica a versão com melhor pontuação
de conteúdo.

### Entrega do resultado

O JSON temporário passa a ser escrito primeiro em `.tmp` e depois renomeado.
Isso reduz o risco de a interface tentar ler um arquivo parcialmente escrito.

A interface também verifica o arquivo periodicamente, além do sinal enviado
pelo worker, deixando o retorno mais tolerante a diferenças entre Windows e
Ubuntu.

A tela mostra:

- caracteres extraídos;
- duração da extração;
- se foi necessária segunda leitura.

## Arquivos a substituir

- `src/monitor_noticias/auth/client.py`
- `src/monitor_noticias/ui/news_extractor_page.py`
- `tools/news_extractor/monitor-main.js`

## Arquivo a adicionar

- `tests/unit/test_v88_auth_extractor_performance.py`

## Próximas etapas

Depois que a V88 estiver na `main`, a próxima versão será construída sobre a
nova `main`, conforme a regra do projeto, e seguirá com:

- otimização do Apps Script de validação;
- limpeza definitiva de Jornais Digitais / Planilhas / WhatsApp;
- remoção de código morto e `__pycache__`;
- `.gitignore`;
- consolidação dos patches estáveis;
- versão única;
- remoção dos dados visuais fictícios;
- testes obrigatórios nos workflows;
- diagnóstico integrado;
- demais melhorias estruturais já levantadas.

## Workflow

WORKFLOW: NÃO PRECISA ALTERAR

Os workflows atuais já observam alterações em `src/**` e
`tools/news_extractor/**`, portanto o motor Electron será recompilado
automaticamente.
