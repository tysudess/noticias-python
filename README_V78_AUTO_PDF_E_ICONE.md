# V78 — Jornais Digitais automático + novo ícone

## Base usada

Patch preparado sobre a `main` confirmada antes da alteração:

`7006c4e819fff036ecdc892285d4abe70282ef7e`

Essa é a `main` que já contém a V77 de Jornais Digitais.

A V78 não altera V74/V75/V76, autenticação da Central, Proxy Geral, Editor PDF,
Home ou catálogo de fontes.

## 1. Jornais Digitais sem abrir navegador no clique

Na V77, `download_current()` fazia:

- criar/obter `DigitalNewspaperBrowserDialog`;
- `show()`;
- `raise_()`;
- `activateWindow()`;
- só então tentar o download.

Isso fazia surgir a janela grande mostrada no teste.

Na V78 o fluxo normal muda para:

`clicar no jornal → iniciar download em segundo plano → salvar PDF → histórico`

`download_current()` não chama mais `show()`, `raise_()` ou `activateWindow()`.

O clique simples em uma linha da lista já dispara o download. O botão
**Baixar edição completa agora** permanece como alternativa explícita.

## 2. Login somente quando realmente necessário

A janela WebEngine continua existindo apenas como ferramenta de autenticação,
porque alguns jornais exigem login interativo do assinante.

Ela só aparece se o usuário clicar deliberadamente em:

**Entrar / renovar sessão**

No download normal ela fica invisível e a tentativa ocorre em segundo plano.

A senha do jornal continua não sendo armazenada. A V78 preserva o cofre de
cookies/sessão criado na V77:

- Windows: DPAPI CurrentUser;
- Ubuntu: Secret Service / Keyring.

## 3. Correio Braziliense — PDF completo direto

Foi confirmado no serviço atual do Correio Braziliense que a edição possui o
link **Download Edição Certificada**, cujo PDF integral segue o formato oficial:

`https://edicao.correiobraziliense.com.br/correiobraziliense/AAAA/MM/DD/all.pdf`

Exemplo observado para 27/09/2026:

`https://edicao.correiobraziliense.com.br/correiobraziliense/2026/09/27/all.pdf`

A V78 agora possui adaptador específico para esse caminho.

Ao clicar em **Correio Braziliense**, a Central não abre navegador: baixa o PDF
oficial da data escolhida em uma thread de rede, preservando os bytes originais.

Se a edição ainda não estiver publicada, informa isso em vez de baixar a edição
de outro dia.

## 4. Demais jornais

Quando ainda não existe uma URL oficial direta confirmada, a V78 mantém o
adaptador separado e tenta silenciosamente o fluxo autorizado do visualizador.

Se a sessão estiver expirada ou o serviço exigir interação, a interface informa
que é necessário usar **Entrar / renovar sessão**.

Não foi adicionada nenhuma técnica para:

- quebrar DRM;
- contornar paywall;
- burlar CAPTCHA;
- acessar conteúdo fora da assinatura;
- forçar URLs protegidas;
- extrair pacotes de aplicativos móveis.

## 5. Validação do PDF

A V78 não considera mais qualquer arquivo `.pdf` como sucesso.

Antes de registrar no histórico:

1. valida a assinatura `%PDF-`;
2. abre com `pypdf`;
3. conta as páginas;
4. só então considera o download concluído.

Arquivos inválidos são descartados.

O PDF oficial não é regravado, rasterizado ou recomprimido.

## 6. Nome determinístico

O arquivo final continua no padrão:

`JornaisDigitais/<provedor>/<AAAA-MM-DD>/<provedor>-AAAA-MM-DD.pdf`

Ao baixar novamente a mesma edição, a V78 substitui o arquivo daquela data em
vez de criar cópias `-2`, `-3`, etc.

## 7. Novo ícone da Central

Foram substituídos:

- `src/monitor_noticias/assets/app_icon.png`
- `src/monitor_noticias/assets/app_icon.ico`

O novo ícone usa identidade visual própria da Central Inteligente de Mídia:
notícias/documentos + letra C + indicadores de mídia, em azul/ciano com detalhe
quente.

O ICO contém múltiplos tamanhos para Windows, de 16x16 a 256x256.

### Windows

`MonitorDeNoticias.spec` agora:

- inclui os assets de ícone da aplicação no bundle;
- passa `app_icon.ico` para o parâmetro `icon=` do `EXE` do PyInstaller.

Isso corrige o ícone genérico exibido no Explorer para `MonitorDeNoticias.exe`.

### Ubuntu

O `MonitorDeNoticias-Linux.spec` já incluía exatamente os mesmos
`src/monitor_noticias/assets/app_icon.png` e `.ico`. Como os arquivos foram
substituídos mantendo o mesmo caminho, o novo ícone também será usado pela
interface Ubuntu sem alteração adicional no spec Linux.

## Arquivos da V78

SUBSTITUIR:

- `src/monitor_noticias/digital_newspapers/providers.py`
- `src/monitor_noticias/digital_newspapers/browser.py`
- `src/monitor_noticias/ui/digital_newspapers_page.py`
- `src/monitor_noticias/assets/app_icon.png`
- `src/monitor_noticias/assets/app_icon.ico`
- `MonitorDeNoticias.spec`

ADICIONAR:

- `tests/unit/test_digital_newspapers_v78.py`
- `README_V78_AUTO_PDF_E_ICONE.md`

## GitHub Actions

Os workflows atuais já disparam quando há mudanças em `src/**` e em
`MonitorDeNoticias.spec`.

Não é preciso alterar nenhum arquivo `.github/workflows`.

## WORKFLOW

**NÃO PRECISA ALTERAR.**
