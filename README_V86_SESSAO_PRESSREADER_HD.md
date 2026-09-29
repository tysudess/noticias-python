# V86 — Sessão automática + PressReader HD reforçado

## Base confirmada
Patch preparado sobre a `main` confirmada em:

`42cd9ee1f8b28758b05679bbec9d26e06e2cf5e7`

Essa base já contém a V85.

## Correções

### 1. Credenciais salvas agora também renovam o login automaticamente
O usuário/senha já estavam armazenados no cofre local seguro. O problema era o fluxo manual
"Entrar / renovar sessão": ele preenchia o e-mail, mas não enviava automaticamente o formulário.
Em logins de duas etapas (e-mail -> Continuar -> senha), isso fazia parecer que a senha não tinha
sido salva.

A V86 mantém as credenciais no mesmo cofre seguro e, quando existe acesso salvo, faz auto-submit
nas etapas do login. CAPTCHA, MFA ou confirmação adicional continuam manuais.

### 2. Valor Econômico: vários arquivos candidatos por página
A V85 escolhia apenas um URL `prcdn.co/img?...&page=N&file=...` por página. O print do teste mostrou
que um desses arquivos era somente 335x536 px.

A V86:
- guarda todos os `file=` observados para cada página;
- tenta as variantes `scale=` e `width=` em cada arquivo;
- só acusa qualidade insuficiente depois de esgotar os candidatos daquela página;
- aumenta o viewport do Chromium para 1800x2800 e zoom 1.8;
- mantém cada imagem HD separada em `paginas_hd`;
- não apaga imagens válidas de uma tentativa anterior ao reiniciar a busca.

### 3. Total real de páginas
O motor lê textos do viewer como `35 de 38` ou `1 of 44` e usa esse total para encerrar a coleta
exatamente no fim da edição, sem precisar depender apenas da tentativa da página seguinte.

### 4. O Globo usa o mesmo motor PressReader HD
O teste real mostrou o viewer:

`https://infoglobo.pressreader.com/o-globo/AAAAMMDD/page/N`

Por isso O Globo passa a usar o mesmo mecanismo de páginas HD do Valor, salvando imagens
separadas e depois montando o PDF.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/digital_newspapers/providers.py`
- `src/monitor_noticias/digital_newspapers/browser.py`
- `src/monitor_noticias/digital_newspapers/pressreader_hd.py`
- `tests/unit/test_digital_newspapers_v84.py`
- `tests/unit/test_digital_newspapers_v85.py`

### ADICIONAR
- `tests/unit/test_digital_newspapers_v86.py`
- `README_V86_SESSAO_PRESSREADER_HD.md`

## Workflow
**WORKFLOW: NÃO PRECISA ALTERAR**

## Validação
- `py_compile`: OK
- testes V84 + V85 + V86: 15 passed
