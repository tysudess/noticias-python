# V81 — Validação de edição, acesso local seguro e ícone do EXE

## Base confirmada

Patch preparado sobre a `main` confirmada imediatamente antes da alteração:

`300fa53e49b64338827677720e39d4afc67e8915`

Essa `main` já contém V74/V75/V76, V77, V78, V79 e V80.

A V81 não altera Android e não mexe no login principal da Central, Proxy Geral,
Home, Editor PDF ou catálogo de fontes.

## 1. Falsos PDFs: Estadão e GZH

Os arquivos produzidos pela V80 mostraram que o motor estava aceitando qualquer
PDF encontrado dentro de determinados portais.

Exemplos observados no teste real:

- arquivo salvo como Estadão: documento interno de Política de Anticorrupção,
  somente 6 páginas;
- arquivo salvo como GZH/Zero Hora: comprovantes bancários, somente 7 páginas.

Na V81, um PDF só pode virar “edição concluída” depois de passar por validação de:

1. assinatura PDF real;
2. tamanho mínimo compatível com edição completa;
3. quantidade mínima de páginas;
4. marcadores de conteúdo que denunciem documentos errados;
5. intenção explícita de edição/download antes de aceitar o download no WebEngine.

Um `.pdf` genérico por si só não recebe mais prioridade alta.

Documentos com sinais como política/compliance, boleto, invoice, receipt,
comprovante, contrato, regulamento etc. deixam de ser candidatos automáticos.

## 2. Correio Braziliense volta ao fluxo que funcionou

A tentativa V79/V80 de reconstrução página a página foi desativada para o
Correio Braziliense.

A V81 volta ao comportamento direto da V78:

`https://edicao.correiobraziliense.com.br/correiobraziliense/AAAA/MM/DD/all.pdf`

O PDF integral oficial continua sendo salvo sem recompressão.

## 3. Acesso de assinante salvo localmente

Não é necessário — nem recomendado — colocar usuário/senha no código ou no
GitHub.

A aba Jornais Digitais agora possui campos:

- Usuário / e-mail
- Senha
- **Salvar acesso neste PC**
- **Apagar acesso**

O acesso fica protegido somente no computador:

### Windows

DPAPI `CurrentUser`, em arquivo local criptografado na pasta de dados da Central.

### Ubuntu

Secret Service / Keyring.

Não existe fallback para senha em texto puro.

No fluxo automático, quando o site realmente apresentar tela de login, a Central
pode preencher o acesso salvo e acionar o botão de login/continuar do formulário.
A senha nunca é gravada no repositório.

## 4. Folha

O domínio `folha.com.br` foi incluído no conjunto autorizado do provedor para
permitir o fluxo de autenticação em `login.folha.com.br`, além dos domínios já
usados pela Edição Folha/Acervo.

## 5. Demais jornais

Os pontos de entrada específicos da V80 são preservados:

- Estado de Minas → leitor EM Digital;
- Folha → Acervo/Edição Folha;
- Estadão → Estadão Digital;
- O Globo → Jornal Digital;
- Valor → Jornal Digital Valor;
- A Tarde → Flip A TARDE;
- GZH/Zero Hora → leitor FlipZH;
- Gazeta Revista → fluxo semanal;
- NYT → Replica Edition/PressReader.

A diferença da V81 é que a Central deixa de “forçar sucesso”: se o serviço não
entregar uma edição completa autorizada, o resultado é “não localizado” em vez
de salvar um PDF qualquer.

## 6. Ícone do MonitorDeNoticias.exe

O `MonitorDeNoticias.spec` já passava `icon=` ao PyInstaller, mas no teste real
o Windows continuou exibindo o ícone genérico.

A V81 mantém `icon=` e, após o `COLLECT`, atualiza explicitamente os recursos
Windows:

- `RT_ICON`;
- `RT_GROUP_ICON`.

A implementação usa a API nativa `BeginUpdateResourceW` / `UpdateResourceW` e,
após aplicar o ícone, valida o EXE com `ExtractIconExW`.

Se o executável final não possuir um ícone reconhecível, o próprio build falha em
vez de publicar silenciosamente um portable com ícone genérico.

## 7. Validação realizada

- sintaxe Python dos arquivos alterados: OK;
- testes V77 + V78 + V79 + V80 + V81: **28 passed**;
- os dois PDFs errados fornecidos no teste real foram executados contra a nova
  validação e foram rejeitados;
- nenhuma senha, usuário ou credencial real foi adicionada ao patch.

## Arquivos

### SUBSTITUIR

- `MonitorDeNoticias.spec`
- `src/monitor_noticias/digital_newspapers/providers.py`
- `src/monitor_noticias/digital_newspapers/browser.py`
- `src/monitor_noticias/digital_newspapers/storage.py`
- `src/monitor_noticias/ui/digital_newspapers_page.py`
- `tests/unit/test_digital_newspapers_v79.py`
- `tests/unit/test_digital_newspapers_v80.py`

### ADICIONAR

- `src/monitor_noticias/digital_newspapers/validation.py`
- `tests/unit/test_digital_newspapers_v81.py`
- `README_V81_VALIDACAO_CREDENCIAIS_ICONE.md`

## GitHub Actions

O workflow atual já é disparado por alterações em `src/**` e
`MonitorDeNoticias.spec`.

**WORKFLOW: NÃO PRECISA ALTERAR**
