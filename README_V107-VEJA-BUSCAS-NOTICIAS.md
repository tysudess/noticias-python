# Central V107 — Inclusão da VEJA nas buscas por notícias

## Base verificada

Repositório: `tysudess/noticias-python`  
Branch: `main`  
Commit consultado antes desta alteração: `3fcc053d3cc31dba23dac57dbf2a8a264485c6bb` (16/10/2026).

A base já contém a V106. Este pacote é incremental sobre a `main` atual e não repete os arquivos da V105/V106.

## O que muda

- Adiciona a fonte **VEJA** ao conjunto nacional usado nas buscas de notícias.
- Adiciona a fonte à lista geral entregue à interface, para aparecer na seleção de veículos nacionais.
- Registra a rota oficial de últimas notícias `https://veja.abril.com.br/ultimas-noticias/` no coletor direto. Os artigos continuam passando pelos filtros existentes de termos, período e domínio permitido.
- Usa o `HttpClient` compartilhado da aplicação; portanto, a coleta mantém a configuração existente do Proxy Geral.
- Não altera a lista de fontes estaduais, a busca de vídeos, o Android nem configurações de autenticação.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/app/composition.py` — liga a fonte VEJA ao catálogo nacional e ao conjunto usado pela interface.

### ADICIONAR
- `src/monitor_noticias/collectors/news/veja_source.py` — definição da fonte, aliases, rota oficial e extensão do catálogo.
- `tests/unit/test_v107_veja_news_source.py` — testes da inclusão, correspondência de veículo e coleta direta de notícia.
- `README_V107-VEJA-BUSCAS-NOTICIAS.md` — documentação desta correção.

## Workflows

**WORKFLOW: NÃO PRECISA ALTERAR.** As alterações ficam em `src/**` e `tests/unit/**`, já cobertos pelos workflows existentes de Windows e Ubuntu.

## Validação e observação

Os testes novos verificam que VEJA entre uma única vez na lista nacional e na lista geral, que o portal direto usa o domínio autorizado e que o coletor preserva o link do artigo. A verificação ao vivo de disponibilidade do portal durante o uso final depende da rede e do Proxy Geral configurados no computador.
