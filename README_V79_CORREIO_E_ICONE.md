# V79 — Correio página faltando + ícone real do EXE

## Base de trabalho
- Esta correção foi preparada sobre a **última base confirmada aqui no chat** após a V78.
- Objetivo: **não sobrescrever** login/proxy/Home/PDF Editor/V74-V76/V77-V78.

## Problemas corrigidos

### 1) Correio Braziliense: página 3 pulando da 2 para a 4
Na V78 o fluxo do Correio priorizava o `all.pdf` oficial. Em alguns casos, esse PDF integral pode vir com falha de composição da própria edição (ex.: salto de página).

A V79 altera a estratégia do **Correio Braziliense**:
1. primeiro tenta **reconstituir a edição página a página** a partir dos PDFs individuais oficiais da data;
2. se localizar sequência válida e contínua, monta o PDF final **sem recompressão**;
3. se as páginas individuais não existirem, estiverem incompletas ou exigirem autenticação específica, a rotina cai para o **`all.pdf` oficial**.

Resultado esperado:
- maior chance de evitar saltos como **2 → 4**;
- quando a sequência individual estiver incompleta, a Central informa o fallback antes de usar o PDF integral.

### 2) Ícone do EXE ainda genérico no Windows
O `.ico` anterior tinha somente um tamanho principal. A V79 troca por um **ICO multi-resolução real** (16, 20, 24, 32, 40, 48, 64, 128 e 256 px), mais compatível com:
- Explorer;
- área de trabalho;
- barra de tarefas;
- cache de ícones do Windows;
- executável gerado pelo PyInstaller.

## Arquivos para substituir/adicionar

### Substituir
- `src/monitor_noticias/digital_newspapers/providers.py`
- `src/monitor_noticias/digital_newspapers/browser.py`
- `src/monitor_noticias/assets/app_icon.ico`

### Adicionar
- `tests/unit/test_digital_newspapers_v79.py`
- `README_V79_CORREIO_E_ICONE.md`

## Observações importantes
- **WORKFLOW: NÃO PRECISA ALTERAR**
- Esta versão **não mexe no Android**.
- O botão/fluxo normal continua sem abrir a janela do navegador para o usuário.
- Se depois do rebuild o Windows ainda mostrar o ícone antigo, teste com **uma pasta portable nova** (o Explorer costuma manter cache por caminho do executável).

## Validação local desta correção
- `py_compile` dos arquivos alterados: OK
- testes `test_digital_newspapers_v79.py`: **3 passed**
