# V80 — Jornais Digitais: provedores restantes

## Base confirmada antes da alteração

Patch preparado sobre a `main`:

`404f63e90a7ce6d4df4661dc100f53b8344bbad4`

Esse HEAD já contém a V79. Os arquivos-base de `providers.py` e `browser.py`
foram conferidos contra os blobs da `main` antes da V80.

A V80 não altera Android, login da Central, Proxy Geral, Home, Editor PDF,
Tribuna da Bahia ou workflows.

## Objetivo

Melhorar o download automático dos jornais que ainda terminavam com
"nenhum PDF localizado" na V78/V79.

A causa principal era que vários adaptadores ainda entravam na home do veículo,
e o detector examinava somente a primeira página carregada. Muitos jornais usam
um leitor separado, iframe, e-paper, redirect de login ou SPA carregada após o
`loadFinished`.

## Mudanças de arquitetura

### Pontos de entrada oficiais por provedor

A V80 passa a abrir prioritariamente os leitores corretos:

- Estado de Minas: `digital.em.com.br/estadodeminas`, com tentativa direta da data
  no padrão `/DD/MM/AAAA/p1`;
- Folha: `acervo.folha.uol.com.br/digital/index.do` e fallback para
  `edicaodigital.folha.uol.com.br`;
- Estadão: `digital.estadao.com.br/o-estado-de-s-paulo/AAAAMMDD`;
- O Globo: `jornaldigital.oglobo.globo.com`;
- Valor Econômico: `jornaldigital.valor.globo.com`;
- A Tarde: `flip.atarde.com.br/edicaodehoje/`;
- Zero Hora / GZH: `flipzh.clicrbs.com.br/jornal-digital/pub/gruporbs/`
  com `?numero=AAAAMMDD`;
- Gazeta Revista: página oficial `gazetadopovo.com.br/gazeta-revista/`;
- New York Times: `eeditionnytimes.newspaperdirect.com/epaper/viewer.aspx`,
  com fallback PressReader.

O Washington Post continua marcado como `app_only` porque não foi confirmado um
PDF completo desktop autorizado. A Central não extrai o pacote offline do app.

### Descoberta em múltiplas etapas

O detector passa a reconhecer e seguir, dentro dos domínios oficiais:

- PDF direto;
- links de edição digital;
- e-paper;
- replica edition;
- viewers;
- iframes/frames;
- embeds/objects;
- links de Jornal Digital;
- links da Gazeta Revista;
- botões explícitos de download/exportação.

Quando um leitor é uma SPA, a V80 repete a análise algumas vezes antes de desistir,
permitindo que a interface assíncrona termine de montar o DOM.

Há limite de navegação e conjunto de URLs já visitadas para evitar loops.

### Login/sessão

O fluxo normal continua invisível. A janela de navegador só aparece quando o
usuário escolhe explicitamente **Entrar / renovar sessão**.

Foi ampliada a compatibilidade de sessão do GZH para o domínio `gauchazh.com.br`,
além dos domínios RBS já existentes.

Não há senha em código nem no GitHub. Não há quebra de DRM, paywall ou CAPTCHA.

## V79 preservada

Como a V79 já estava na `main`, a V80 foi construída em cima dela e mantém:

- remontagem página a página do Correio Braziliense antes do fallback `all.pdf`;
- validação de sequência de páginas;
- ícone Windows multi-resolução.

## Arquivos da V80

### SUBSTITUIR

- `src/monitor_noticias/digital_newspapers/providers.py`
- `src/monitor_noticias/digital_newspapers/browser.py`

### ADICIONAR

- `tests/unit/test_digital_newspapers_v80.py`
- `README_V80_JORNAIS_DIGITAIS_PROVEDORES.md`

Nenhum outro arquivo deve ser substituído por este ZIP.

## Validação

- `py_compile`: OK
- testes V78 + V79 + V80 em conjunto: 15 passed
- testes específicos V80: 7 passed

## WORKFLOW

**NÃO PRECISA ALTERAR.**
