# Correção isolada da aba Capas — associação Gmail e diagnóstico

Base consultada: `main` no commit `2258c55a019e7ba3878243d8040baaeb471fe18d`.

## Problema encontrado no código atual

1. A ponte Apps Script agrupa os links pelo campo `name` recebido.
2. A aba Capas procura esses grupos usando igualdade literal (`matters.get(e.name)`).
3. Diferenças de maiúsculas/minúsculas, acentos, pontuação ou nomes editoriais alternativos fazem a aba marcar o jornal como ausente, embora o link esteja no retorno do Gmail.
4. A rotina que abre `Leia mais` já guarda erros por página, mas o estado final da interface não expõe a causa detalhada ao usuário.

## O que esta correção faz

- Normaliza e associa variações conhecidas a nomes canônicos já existentes: O Globo, Folha de São Paulo, Estadão, Correio Braziliense, Estado de Minas e The New York Times.
- Agrupa links de nomes equivalentes sem perder URLs distintas.
- Não usa associação aproximada para jornais desconhecidos; mantém o nome original para diagnóstico.
- Mostra ao final da atualização os contadores retornados pela ponte: conversas, mensagens lidas, `Leia mais` encontrados e itens na data.
- Expõe no status de cada jornal o erro específico de páginas que não abriram.
- Preserva o fluxo especial do Valor Econômico e do Washington Post; não os adiciona ao conjunto Gmail comum.

## Arquivos

- SUBSTITUIR `src/monitor_noticias/ui/covers_page.py`.
- NOVO `src/monitor_noticias/ui/covers_gmail_reliability_patch.py`.
- NOVO `src/monitor_noticias/capas_tool/app/paper_names.py`.
- NOVO `tests/unit/test_covers_gmail_name_normalization.py`.
- NOVO `tests/unit/test_covers_gmail_reliability_patch.py`.

## Limite da verificação

O código-fonte do Apps Script é externo e não está neste repositório. Esta entrega corrige a associação de nomes no Python e torna visíveis os indicadores da ponte. Se os contadores mostrarem que as mensagens não foram classificadas, ou que `Leia mais` não foi encontrado, será necessário ajustar a implantação do Apps Script; o diagnóstico agora distingue essas situações.

Nenhum workflow, dependência, build portátil, módulo do Estúdio de Artes ou recurso de outra aba foi alterado.
