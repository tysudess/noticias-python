# Central V106 — Desempenho das buscas regionais de vídeos

## Base atual confirmada

Repositório `tysudess/noticias-python`, branch `main`, commit `5b80a0144e10de1da45a88c8529aadad9de9c8eb` (16/10/2026). Esse commit já inclui a V105 de correção de precisão; este pacote é **incremental sobre essa base** e não repete arquivos já aplicados.

## Objetivo

Reduzir chamadas redundantes nas buscas regionais, medir o custo real por fonte e manter as correções de precisão já presentes na `main`. A busca nacional por termos adicionais permanece limitada às fontes nacionais, evitando multiplicar as requisições regionais nesta etapa.

## Alterações

- **Cache temporário de HTML GET:** o `HttpClient` recebe cache local à thread, ativo apenas durante uma busca de vídeos. Limites: até 96 respostas e 24 MiB no total, com teto de 4 MiB por resposta. Só armazena HTML sem `Set-Cookie`; inclui URL, cabeçalhos e limite do corpo na chave. O cache é destruído ao final da busca e não grava dados em disco.
- **Descoberta regional do Globoplay:** para fontes associadas a uma UF, o coletor de edições consulta no máximo duas URLs de descoberta: termo principal e, se necessário, um alias. Os aliases completos continuam disponíveis para pontuar páginas e títulos; não é alterado o catálogo nem a seleção de fontes.
- **Medição por fonte:** a aba Vídeos emite o estado da fonte antes da coleta em rede. Os logs passam a registrar linhas `VIDEO_SEARCH_PERF` para fontes regionais, com duração total, GETs reais, acertos de cache, bytes, resultados aceitos e falhas. O log rotativo principal da aplicação se chama `monitor-noticias.log`.
- **Escopo e compatibilidade:** o cache só existe durante `VideoRepository.search()`, é local à thread e usa o `HttpClient` já configurado com o Proxy Geral. Notícias e outros fluxos não ganham cache persistente nem novas dependências.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/repositories/video_search.py` — V105 já presente na `main` + anúncio de início antecipado da coleta e comentários ajustados para V106.
- `src/monitor_noticias/repositories/video_collect.py`
- `src/monitor_noticias/repositories/video_repository.py`
- `src/monitor_noticias/networking/http_client.py`

### ADICIONAR
- `src/monitor_noticias/repositories/video_performance.py`
- `tests/unit/test_v106_regional_video_performance.py`
- `README_V106-DESEMPENHO-BUSCAS-REGIONAIS.md`

## Workflows

**WORKFLOW: NÃO PRECISA ALTERAR.** Os workflows de Windows e Ubuntu já são acionados por `src/**` e executam `tests/unit`.

## Validação e limites

Os testes isolados de V105 e V106 passaram juntos (19 testes) usando coletores HTTP simulados. A sintaxe Python também passou na verificação local. Isso valida a lógica e as regressões cobertas, mas não equivale a uma medição ao vivo de todos os portais. A comparação de tempos reais deve ser feita depois dos builds usando as linhas `VIDEO_SEARCH_PERF` no log; o próximo ciclo pode priorizar as fontes que ainda mostrarem mais tempo ou GETs.
