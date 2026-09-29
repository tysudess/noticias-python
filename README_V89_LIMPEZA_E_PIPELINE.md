# Central V89 — Limpeza estrutural e pipeline de qualidade

Base conferida antes da alteração:

`ba5776ed7a96599861a0dd05ba6b24f1b885c390`

## O que esta versão faz

### 1. Planilhas deixa de nascer para depois ser escondida

Antes, `MainWindow` ainda importava e construía `SpreadsheetAutomationPage`.
Depois, `removed_integrations_guard.py` removia a página da navegação e a
apagava da janela.

A V89 retira a integração diretamente da fonte:

- `Section.SPREADSHEETS` deixa de existir;
- `MainWindow` não importa nem instancia Planilhas;
- a busca global não tenta navegar para Planilhas;
- o fechamento da Central não procura mais esse processo;
- `application.py` não instala mais o guard legado.

Isso reduz inicialização, imports e risco de regressões.

### 2. Build Windows não baixa mais Automação de Planilhas

Foram removidos do workflow Windows:

- `PLANILHAS_RUNTIME_TAG`;
- `PLANILHAS_RUNTIME_ASSET`;
- download da release standalone;
- pasta `tools/spreadsheet_automation` no Portable;
- cópia de `config.json`;
- validação da Automação de Planilhas no ZIP.

O workflow passa a reprovar o ZIP caso algum conteúdo legado de Planilhas volte
a ser incluído acidentalmente.

### 3. Testes antes do build

Windows e Ubuntu agora executam antes do PyInstaller/Electron:

- `python -m compileall -q src`;
- `node --check tools/news_extractor/monitor-main.js`;
- `python -m pytest -q tests/unit -k "not digital_newspapers"`.

Os testes antigos de Jornais Digitais ficam excluídos temporariamente do comando
porque a V89 também determina a remoção definitiva desses arquivos históricos.

### 4. `.gitignore`

A raiz passa a ignorar:

- `__pycache__`;
- `.pyc`;
- `.pytest_cache`;
- ambientes virtuais;
- `build/` e `dist/`;
- `node_modules` e `tools/news_extractor/dist`;
- dados/logs/temp gerados localmente;
- arquivos de IDE/SO.

### 5. Versão única da aplicação

A versão oficial passa a existir em:

`src/monitor_noticias/version.py`

com:

`APP_VERSION = "4.0.2"`

O `pyproject.toml` lê essa mesma constante por configuração dinâmica do
setuptools. A janela também usa a mesma fonte.

O rótulo é escolhido pela plataforma:

- Windows: `Windows Portable v4.0.2`;
- Ubuntu/Linux: `Ubuntu Portable v4.0.2`.

### 6. Interface: sem temperatura inventada

O cabeçalho não mostra mais `29°C` fixo. Como a Central não possui uma fonte
climática real, passa a exibir somente data e hora reais do sistema.

### 7. Menos refresh desnecessário

O timer visual muda de 500 ms para 1000 ms e a página ativa só é redesenhada
quando uma assinatura do estado muda. Eventos reais emitidos pelo controller
ainda atualizam a tela imediatamente.

Isso reduz trabalho de UI sem sacrificar o acompanhamento das buscas.

### 8. Dependências

`pytest` sai de `requirements.txt` (runtime) e vai para
`requirements-build.txt`. O Portable deixa de carregar dependência de teste sem
necessidade.

O `pyproject.toml` passa a representar também as dependências PDF/imagem usadas
pelo programa.

## Limpeza manual no GitHub

O arquivo `REMOVER_DO_GITHUB_V89.txt` contém a relação exata dos arquivos
legados que devem ser excluídos: Jornais Digitais, Planilhas standalone,
WhatsApp Browser antigo, `__pycache__`, testes antigos e workflow de rebuild de
Planilhas.

O compartilhamento via WhatsApp existente nos botões da aba Notícias NÃO foi
removido; o que sai é somente a antiga página/browser integrado de WhatsApp.

## Arquivos para substituir

- `.github/workflows/build-portable.yml`
- `.github/workflows/build-ubuntu.yml`
- `pyproject.toml`
- `requirements.txt`
- `requirements-build.txt`
- `src/monitor_noticias/app/application.py`
- `src/monitor_noticias/ui/main_window.py`
- `src/monitor_noticias/ui/sections.py`
- `tests/unit/test_ui_step9.py`

## Arquivos para adicionar

- `.gitignore`
- `src/monitor_noticias/version.py`
- `tests/unit/test_v89_structural_cleanup.py`
- `README_V89_LIMPEZA_E_PIPELINE.md`
- `REMOVER_DO_GITHUB_V89.txt`

## Workflow

**WORKFLOW: PRECISA ALTERAR**

Os dois workflows de build fazem parte desta versão.
