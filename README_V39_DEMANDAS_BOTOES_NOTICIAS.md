# V39 — Mesmos botões da aba Notícias dentro de Demandas

## O que muda

A aba Demandas passa a ter um segundo painel:

`Notícias encontradas pelas demandas`

Esse painel mostra somente notícias que vieram de demanda, usando:

- `news.demand == True`
- ou `news.matchedDemand` preenchido.

## Botões

Cada resultado usa exatamente o mesmo `NewsDelegate` da aba Notícias.

Portanto aparecem os mesmos quatro botões:

1. ↗ Abrir matéria
2. ◉ WhatsApp
3. ▣ Copiar link
4. ⇩ Extrair matéria

Não existe código duplicado para esses botões. Se a lógica do botão mudar em
Notícias, a aba Demanda acompanha automaticamente porque usa o mesmo delegate.

## Comportamento

### Abrir matéria
Usa o mesmo resolvedor de link direto da aba Notícias.

### WhatsApp
Usa o mesmo compartilhamento da aba Notícias.

### Copiar link
Copia a URL resolvida do veículo, não o link intermediário do Google News.

### Extrair matéria
Abre o Extrator de Notícias do Central e envia a URL da matéria.

## Layout

As Demandas cadastradas e as Notícias encontradas ficam em um splitter
vertical redimensionável:

- parte superior: demandas cadastradas;
- parte inferior: notícias encontradas.

O usuário pode arrastar a divisão para dar mais espaço à área desejada.

## Arquivos

SUBSTITUIR:
- `src/monitor_noticias/ui/demands_page.py`
- `src/monitor_noticias/app/application.py`

NOVO:
- `src/monitor_noticias/ui/demands_news_actions_integration.py`

## Workflow

NÃO precisa alterar workflow.
NÃO precisa executar `Rebuild Planilhas Runtime`.

É uma alteração somente do Python/PySide6 do Central.
Depois de subir os arquivos, execute apenas o build normal do Portable.
