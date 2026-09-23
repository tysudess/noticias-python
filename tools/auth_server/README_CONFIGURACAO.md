# Central Auth — Google Apps Script + Google Sheets

## O que este servidor controla

- usuário/senha;
- ativo/bloqueado;
- validade;
- limite de computadores;
- computadores autorizados;
- perfil;
- permissões por aba;
- sessões;
- último acesso;
- logs.

A senha não fica em texto puro na planilha.

## 1. Criar a planilha

Crie uma nova Planilha Google, por exemplo:

`CENTRAL - USUARIOS`

Abra:

`Extensões -> Apps Script`

Apague o conteúdo de `Code.gs` e cole o arquivo `Code.gs` deste pacote.

Se quiser, também copie o conteúdo de `appsscript.json` para o manifesto
do projeto.

## 2. Preparar a planilha

No editor do Apps Script, execute uma vez:

`setupCentralAuth`

Autorize o script quando o Google solicitar.

Serão criadas as abas:

- USUARIOS
- DISPOSITIVOS
- SESSOES
- LOGS
- CONFIG

Também será criado o usuário inicial:

`admin`

## 3. Definir a senha do admin

Na aba `USUARIOS`, localize a linha `admin`.

Na coluna:

`NOVA_SENHA`

digite uma senha com pelo menos 8 caracteres.

Depois, na planilha:

`Central Auth -> Processar senhas pendentes`

O Apps Script:

- gera salt aleatório;
- cria hash iterado;
- usa um pepper secreto salvo em Script Properties;
- grava apenas salt + hash;
- limpa a coluna NOVA_SENHA.

A senha em texto puro não permanece na planilha.

## 4. Cadastrar outros usuários

Adicione uma nova linha em `USUARIOS`.

Campos principais:

USERNAME
: login em letras/números.

NOME
: nome mostrado no programa.

STATUS
: `ATIVO` ou `BLOQUEADO`.

NOVA_SENHA
: senha temporária para processamento.

PERFIL
: `ADMIN`, `OPERADOR`, `EDICAO` ou `CONSULTA`.

VALIDADE
: opcional. Pode deixar em branco.

MAX_DISPOSITIVOS
: normalmente `1`.

PERMISSOES
: `*` para tudo ou lista separada por vírgulas.

Depois use novamente:

`Central Auth -> Processar senhas pendentes`

## Permissões disponíveis

- home
- news
- videos
- demands
- sources
- history
- terms
- stop
- news_extractor
- covers
- pdf_editor
- extractor
- video_editor
- settings

Exemplo:

`news,videos,demands,sources,history`

Para administrador:

`*`

## 5. Publicar como Web App

No Apps Script:

`Implantar -> Nova implantação`

Tipo:

`App da Web`

Executar como:

`Eu`

Quem tem acesso:

`Qualquer pessoa`

Publique.

O Google fornecerá uma URL parecida com:

`https://script.google.com/macros/s/...../exec`

COPIE A URL `/exec`.

Essa é a URL que será colocada no aplicativo.

## 6. Importante

Não envie o arquivo da planilha para os usuários.

Eles recebem apenas o portable.

A planilha e o Apps Script ficam sob sua conta Google.

## Dispositivos

Quando um usuário entra pela primeira vez em um computador, esse computador
é registrado na aba `DISPOSITIVOS`.

Se `MAX_DISPOSITIVOS=1`, um segundo computador é recusado.

Para bloquear um PC já autorizado, altere a coluna `ATIVO` desse dispositivo
para `FALSE`.

Para permitir um PC novo quando o limite já foi atingido, desative/remova o
dispositivo antigo.

## Bloquear usuário

Na aba USUARIOS altere:

`ATIVO`

para:

`BLOQUEADO`

Na próxima validação, o acesso é recusado.

Para derrubar sessões imediatamente, use:

`Central Auth -> Revogar todas as sessões`

## Próximo passo

Depois de publicar o Web App, envie a URL terminada em `/exec`.

A próxima versão da Central irá:

1. colocar essa URL no cliente;
2. mostrar a tela de login ANTES da MainWindow;
3. salvar o token em DPAPI no Windows;
4. salvar o token em Keyring no Ubuntu;
5. validar a sessão em cada abertura;
6. esconder/bloquear abas conforme as permissões retornadas pelo servidor.
