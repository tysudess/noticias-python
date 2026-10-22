# Central V109 — Logos oficiais dos veículos na lista de Notícias

## Base confirmada

Repositório `tysudess/noticias-python`, branch `main`, commit `a0b85ef19faccbe71b91a065bf61c2406a6e1d4e` (22/10/2026). Pacote incremental, sem modificar o repositório remoto.

## Objetivo

Trocar as iniciais azuis de cada cartão de notícia pelo favicon do site do veículo quando disponível, mantendo as iniciais como fallback caso o portal não forneça um ícone válido ou a conexão falhe.

## Implementação

- O parser do RSS do Google Notícias lê o atributo `url` do elemento `source` e registra em memória o endereço oficial do veículo. Isso permite identificar o domínio real mesmo quando o link do artigo é um link intermediário `news.google.com`.
- O novo painter sobrepõe o favicon no espaço atual de 40×40, sem alterar a altura dos cartões, os botões, o filtro ou o layout da lista.
- O download dos favicons é assíncrono, limitado a três tarefas simultâneas, iniciado somente quando um cartão visível precisa do ícone, cacheado em memória e limitado a 256 KiB por resposta. Nenhum ícone é baixado durante a busca de notícias.
- A requisição usa a configuração do Proxy Geral existente e os limites de timeout são curtos. Se o proxy não puder ser lido ou a imagem falhar, o cartão mantém as iniciais.
- Para registros antigos sem origem do RSS, há uma pequena tabela de domínios conhecidos e a tentativa de aproveitar o domínio de links diretos.
- Não há novos pacotes Python; usa `requests` e PySide6 já presentes no projeto. Nenhum conteúdo de notícia ou URL completa da matéria é enviado ao serviço de favicon; somente a origem do site é consultada.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/app/composition.py`
- `src/monitor_noticias/collectors/news/google_news.py`

### ADICIONAR
- `src/monitor_noticias/networking/source_sites.py`
- `src/monitor_noticias/ui/news_site_icons_patch.py`
- `tests/unit/test_v109_news_official_site_logos.py`
- `README_V109-LOGOS-OFICIAIS-NOTICIAS.md`

## Workflows

**WORKFLOW: NÃO PRECISA ALTERAR.** Os workflows atuais são acionados por `src/**` e executam os testes unitários.

## Limites e validação

Ícones vêm do serviço de favicon do Google a partir do domínio oficial informado pelo RSS; não são arquivos de logotipo vetorial/masthead. Portais sem favicon, indisponíveis pela rede ou inacessíveis pelo proxy continuarão mostrando as iniciais. Downloads reais dos favicons dependem da conexão do computador no qual a Central está rodando.
