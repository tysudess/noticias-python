# Central V140 — Extrator de matérias e tema escuro

Base utilizada: branch `main` do repositório `tysudess/noticias-python`, commit
`89d45199fcac23e61df49297d9a68ee86bb1353a`.

Este pacote não altera o GitHub. Extraia o ZIP na raiz do repositório e mantenha
os caminhos das pastas. Substitua os arquivos indicados e adicione os novos.

## O que muda

### Extrator de notícias — motor V1.25.21

- Cria uma leitura direcionada para `zona-militar.com` e
  `defesaaereanaval.com.br`, com seletores alternativos para o corpo editorial.
- Mantém a extração principal como primeira tentativa. A leitura específica do
  portal é usada como recuperação ou quando apresenta um corpo melhor.
- Remove blocos conhecidos de publicidade, recomendação, comentários, tags,
  chamadas “Leia mais”, créditos isolados, navegação e parágrafos duplicados.
- Amplia a limpeza genérica com regras curtas e conservadoras, sem remover
  listas jornalísticas curtas que podem conter especificações ou dados.
- Reutiliza a configuração de rede/proxy do motor atual. Não tenta contornar
  bloqueios, autenticação ou conteúdo exclusivo para assinantes.

O alias `extrator-materia-v1.25.10-runtime.js` passa a carregar o runtime
V1.25.21. Assim, `main.js` e `monitor-main.js` continuam usando o mesmo ponto
de entrada já existente.

**Compatibilidade do portable:** o nome do executável continuará sendo
`ExtratorMateriasPortable-V1.25.19` nos pacotes Windows/Ubuntu porque os dois
workflows atuais procuram e copiam exatamente esse caminho. A versão funcional
do motor é apresentada como `1.25.21` pelo runtime; não renomeie o executável
nesta entrega, para não quebrar o empacotamento existente.

### Tema escuro — Início e Fontes

- Inclui `SourceDelegate` no adaptador de pintura do tema, eliminando os cartões
  brancos desenhados diretamente na lista de Fontes.
- Propaga a paleta Claro/Escuro a cada widget e à viewport dos componentes
  roláveis; a área de conteúdo da aba Início passa a preencher com a cor correta.
- Preserva os delegates já adaptados de Notícias e Histórico e mantém os estilos
  próprios das ações/botões.
- O seletor Claro/Escuro e a persistência da preferência permanecem inalterados.

## Arquivos deste pacote

| Ação | Caminho |
|---|---|
| Substituir | `src/monitor_noticias/ui/theme_engine.py` |
| Substituir | `src/monitor_noticias/ui/theme_preferences.py` |
| Adicionar | `tests/unit/test_theme_engine_v140.py` |
| Substituir | `tools/news_extractor/engine/extrator-materia-v1.25.10-runtime.js` |
| Adicionar | `tools/news_extractor/engine/extrator-materia-v1.25.21-runtime.js` |
| Adicionar | `tools/news_extractor/tests/extrator-v12521.test.js` |

## Validações realizadas neste ambiente

- `node --check` nos dois runtimes e no arquivo de testes: aprovado.
- `python -m compileall` nos módulos de tema alterados: aprovado.
- Testes `test_theme_engine_v139.py` e `test_theme_engine_v140.py`: 7 aprovados.
- Não foi possível executar os testes Node de extração porque a dependência
  `jsdom` não está instalada neste ambiente. Execute após instalar as
  dependências do extrator:

```bash
cd tools/news_extractor
npm install --no-audit --no-fund
node --test tests/extrator-v12521.test.js
```

- Não foi possível fazer teste visual Qt porque PySide6 não está disponível
  neste ambiente. Os builds oficiais Windows e Ubuntu e a validação visual nas
  duas plataformas precisam ser conferidos depois que os arquivos forem
  enviados à `main`.

## Testes Python

Na raiz do repositório:

```bash
python -m pytest -q tests/unit/test_theme_engine_v139.py tests/unit/test_theme_engine_v140.py
```
