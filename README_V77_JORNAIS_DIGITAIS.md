# V77 — Jornais Digitais

## Base usada

Patch preparado sobre a `main` confirmada antes da alteração:

`be508966826aecbf351d03c9d783e829064c8e2a`

A V77 preserva as correções anteriores, inclusive:

- V74 — Editor PDF com largura igual à capa padrão;
- V75 — Tribuna da Bahia no catálogo real antes do `AppContainer`;
- V76 — Home sem `Resumo do dia` e `Dicas`, com Agendamento em largura total;
- login/token sem revalidação periódica;
- Proxy Geral;
- compatibilidade SSL sem validação restrita ao proxy corporativo `proxy-7dn.mb:6060`.

## Nova aba

Adiciona **Jornais Digitais** à sidebar e ao `QStackedWidget` sem alterar o enum
`Section` nem `SECTION_ORDER`.

A integração fica isolada em:

`src/monitor_noticias/ui/digital_newspapers_integration.py`

Assim a nova funcionalidade não altera a navegação interna das páginas já
existentes.

## Jornais cadastrados

- Estadão
- Folha de S.Paulo
- O Globo
- Correio Braziliense
- Valor Econômico
- A Tarde
- Estado de Minas
- Gaúcha / Zero Hora / GZH
- Gazeta do Povo / Gazeta Revista
- The New York Times
- The Washington Post

## Segurança

A V77 **não grava a senha dos jornais**.

O login ocorre diretamente no site oficial dentro do Chromium/Qt WebEngine.

Para reaproveitar uma sessão, somente cookies do domínio do provedor são
serializados e protegidos localmente:

### Windows

DPAPI `CurrentUser`.

### Ubuntu

Secret Service / Keyring.

Não existe fallback de sessão em texto puro.

O navegador usa perfil `off-the-record`; portanto o banco de cookies normal do
Chromium não é persistido em disco. A persistência é feita somente pelo cofre
seguro acima.

## Proxy Geral

Antes de abrir o navegador, a V77 chama a mesma sincronização já usada pela aba
Capas:

`refresh_central_proxy()`

Assim o Qt WebEngine usa o mesmo Proxy Geral configurado na Central.

A autenticação do proxy também usa o mesmo usuário e senha já protegidos pelo
cofre da aplicação.

Erros de certificado só podem ser aceitos automaticamente quando a configuração
ativa `corporate_tls_compatibility()` confirmar exatamente:

`proxy-7dn.mb:6060`

Fora desse caso, a validação normal do Chromium permanece ativa.

## Download de edição completa

A V77 segue a prioridade definida para qualidade:

1. PDF oficial;
2. exportação/download autorizado pelo próprio visualizador;
3. páginas HD autorizadas — reservado para adaptadores específicos posteriores;
4. captura de tela não é tratada como PDF oficial.

O botão **Baixar edição completa** procura somente elementos da própria página
que indiquem explicitamente PDF/edição/exportação e aciona o recurso oferecido
pelo site. Um botão genérico de `Download` não é tratado automaticamente como
edição completa.

Se houver um link direto para PDF na página autenticada, o próprio Qt WebEngine
faz o download usando a sessão do assinante. Se o botão oficial estiver dentro
de um visualizador/iframe que o detector automático não enxergue, o assinante
pode clicar no botão oficial manualmente; o evento de download do Chromium
continua sendo capturado pela V77 quando o arquivo resultante é PDF.

Não existe código para:

- quebrar DRM;
- resolver ou burlar CAPTCHA;
- contornar paywall;
- descobrir URLs protegidas por força bruta;
- extrair pacotes offline de aplicativos móveis;
- baixar conteúdo fora da autorização da assinatura.

## PDF

Downloads identificados como PDF são salvos em:

`JornaisDigitais/<provedor>/<AAAA-MM-DD>/`

Nome padrão:

`provedor-AAAA-MM-DD.pdf`

O arquivo recebido do jornal é salvo diretamente, sem passar pelo Editor PDF,
sem recompressão e sem rasterização.

Após o download, `pypdf` é usado somente para contar o número de páginas. O PDF
não é regravado.

## Data selecionada na V77

A data escolhida na aba define a **data alvo**, o nome do arquivo e o registro do
histórico. Nesta primeira infraestrutura a V77 não inventa nem força URLs de
edições antigas. Quando o site possui seletor próprio de data, a edição deve ser
confirmada no visualizador oficial antes do download. Adaptadores posteriores
podem automatizar a seleção de data quando o próprio serviço oferecer um fluxo
web estável e autorizado.

## Histórico

O histórico é salvo em:

`data/digital_newspapers/history.json`

Campos:

- Jornal
- Data
- número de páginas
- qualidade
- método
- caminho do PDF
- status

Esse arquivo não contém senha, token ou cookie.

## Tratamentos iniciais

### Correio Braziliense

Marcado como `official_pdf`, pois a assinatura atual documenta a íntegra do
impresso em PDF.

### Estado de Minas

Marcado como `official_pdf`; o próprio FAQ informa leitura do jornal em PDF em
`digital.em.com.br` mediante login.

### Gazeta do Povo

A V77 trata **Gazeta Revista**, produto semanal em PDF. Não a apresenta como
réplica diária do antigo impresso.

### The Washington Post

Marcado como `app_only` para a edição completa, pois a documentação atual da
Print Edition concentra esse fluxo no aplicativo oficial. A V77 não tenta
extrair o pacote offline do app.

## Arquivos alterados

SUBSTITUIR:

- `src/monitor_noticias/app/application.py`

ADICIONAR:

- `src/monitor_noticias/digital_newspapers/__init__.py`
- `src/monitor_noticias/digital_newspapers/providers.py`
- `src/monitor_noticias/digital_newspapers/storage.py`
- `src/monitor_noticias/digital_newspapers/browser.py`
- `src/monitor_noticias/ui/digital_newspapers_page.py`
- `src/monitor_noticias/ui/digital_newspapers_integration.py`
- `tests/unit/test_digital_newspapers_v77.py`
- `README_V77_JORNAIS_DIGITAIS.md`

## Windows e Ubuntu

A implementação é compartilhada.

O projeto já possui Qt WebEngine e o Proxy Geral também já é aplicado ao Qt.
Não é necessário adicionar Selenium, Playwright ou outro navegador.

## WORKFLOW

**NÃO PRECISA ALTERAR.**
