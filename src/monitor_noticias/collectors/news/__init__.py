from .google_news import GoogleNewsCollector, parse_google_news_xml
from .latest import NewsLatestCollector, Outcome, ROUTES

# Poder Naval já existe no catálogo de mídia especializada. A rota direta
# complementa a busca Google Notícias e permite ler as matérias recentes do
# próprio portal quando essa fonte é selecionada.
ROUTES.setdefault(
    "especializada-poder-naval",
    ("https://www.naval.com.br/blog/", {"naval.com.br"}),
)

__all__ = ["GoogleNewsCollector", "parse_google_news_xml", "NewsLatestCollector", "Outcome"]
