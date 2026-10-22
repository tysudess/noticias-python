# Central V111 — Logos nas fontes de Notícias, Vídeos e Mídia especializada

## Base confirmada
Repositório `tysudess/noticias-python`, branch `main`, commit `091ff763d2a93def038e05b346bd2ef4f2b8ff65` (22/10/2026).

## Mudança
A lista de fontes usa favicon/site oficial no espaço atual das iniciais, para as abas Notícias, Vídeos e Mídia especializada. Mantém o desenho e tamanho das linhas, usando as iniciais como fallback quando não há URL/domínio conhecido ou o ícone falha.

A resolução tenta primeiro atributos de URL presentes no objeto da fonte (`url`, `homepage`, `website`, `site_url`, `source_url`, `base_url`), depois reutiliza o catálogo de domínios já conhecido pela lista de notícias. Downloads são assíncronos, limitados a três tarefas, limitados a 256 KiB por ícone e respeitam o Proxy Geral. Cache apenas em memória.

## Arquivos
- SUBSTITUIR `src/monitor_noticias/app/composition.py`
- ADICIONAR `src/monitor_noticias/ui/source_list_logos_patch.py`
- ADICIONAR `tests/unit/test_v111_source_list_logos.py`

## Workflow
WORKFLOW: NÃO PRECISA ALTERAR.

## Validação
Teste de sintaxe Python e integridade do ZIP. É necessário validar os favicons dos catálogos completos de vídeo e mídia especializada no aplicativo em execução; fontes sem URL ou sem domínio conhecido mantêm as iniciais.
