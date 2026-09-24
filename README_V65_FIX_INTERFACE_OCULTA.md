# V65 — Correção crítica da interface Windows/Ubuntu

## Sintoma

Depois da V64, a Central abria mostrando praticamente apenas a barra
lateral. A área principal (Home, Notícias, Vídeos etc.) desaparecia.

Afetava:
- ADMIN;
- OPERADOR;
- Windows Portable;
- Ubuntu Portable.

## Causa confirmada

Em `header_refinement_patch.py`, a função `_hide_search()` tentou
ocultar o pai da caixa de busca quando o pai possuía poucos itens:

```python
parent = edit.parentWidget()

if parent.layout().count() <= 3:
    target = parent
```

Na MainWindow real, o `parentWidget()` de `global_search` é o QWidget
`content`.

Esse mesmo QWidget contém:
1. cabeçalho;
2. QStackedWidget com TODAS as páginas;
3. rodapé.

Portanto a V64 ocultava o programa inteiro à direita da sidebar.

## Correção V65

Agora:
- somente `window.global_search` é ocultado;
- nenhum `parentWidget()` é escondido;
- nenhuma página é escondida;
- nenhum layout/container principal é alterado;
- o espaço da busca é devolvido ao header via `QSizePolicy.Ignored`.

## Arquivo para substituir

`src/monitor_noticias/ui/header_refinement_patch.py`

## Teste de regressão novo

`tests/unit/test_header_refinement_v65.py`

O teste monta exatamente um container com:
- header;
- busca;
- stack de páginas;
- footer;

e confirma que esconder a busca NÃO esconde o conteúdo principal.

## Windows e Ubuntu

A correção é compartilhada em `src/**`.
Portanto vale para os dois sistemas.

## WORKFLOW

NÃO PRECISA ALTERAR.
