# Central V104 — Extrator de Notícias: desempenho e qualidade

## Base consultada

Repositório `tysudess/noticias-python`, branch `main`, commit verificado antes da preparação: `5d4dfa2d6fe7a06726fbc812135dcd924219522c`.

## O que muda

- O novo `monitor-bootstrap.js` é o ponto de entrada do worker Electron headless; a interface normal continua encaminhada para `monitor-main.js` e `main.js`.
- No worker integrado, o tempo de uma requisição individual fica limitado a 8,5 segundos em modo rápido. A lógica original de retry da leitura principal continua disponível; leituras complementares ficam limitadas a duas tentativas.
- Respostas HTML bem-sucedidas da mesma URL podem ser reutilizadas em memória durante aquela extração, evitando baixar de novo a mesma página para revisar cabeçalho ou conferir blocos. O cache é por processo, somente GET HTML e até 5 MiB; não grava artigos nem credenciais em cache persistente.
- O corpo recebe uma limpeza conservadora de parágrafos repetidos e chamadas isoladas de navegação/publicidade. O extrator passa a recusar trechos extremamente curtos e previews UOL marcados como incompletos, em vez de registrá-los como matéria completa.
- `package.json` inclui o novo arquivo no empacotamento Windows e Linux. Nome e versão externa do executável permanecem compatíveis com os workflows atuais.
- `portable/linux/TESTAR-PORTABLE.sh` ganha as expressões de compatibilidade pedidas pelos testes V98/V101 e preserva o teste funcional rawvideo/BGRA da V102.

## Arquivos

### SUBSTITUIR

- `tools/news_extractor/package.json`
- `portable/linux/TESTAR-PORTABLE.sh`

### ADICIONAR

- `tools/news_extractor/monitor-bootstrap.js`
- `tests/unit/test_v104_news_extractor_fast_quality.py`
- `README_V104-EXTRATOR-NOTICIAS-PERFORMANCE-QUALIDADE.md`

## Workflows

**WORKFLOW: NÃO PRECISA ALTERAR.** Os workflows existentes já monitoram alterações em `tools/news_extractor/**`, `tests/unit/**` e `portable/linux/TESTAR-PORTABLE.sh`; o pacote continua usando os mesmos nomes dos executáveis.

## Validação e limite

O pacote deve passar pelos testes Python, `node --check` e `bash -n`. A melhoria de rede é específica ao worker headless da Central e não modifica o proxy nem desativa TLS. O tempo real depende do portal, autenticação, rede e proxy. É preciso validar nos dois portables após reconstruir; o teste local não equivale a uma extração em todos os veículos jornalísticos.
