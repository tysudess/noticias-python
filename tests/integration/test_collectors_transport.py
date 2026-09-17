from monitor_noticias.collectors.news.google_news import GoogleNewsCollector

class EmptyTransport:
    def __init__(self):self.call=None
    def get_text(self,url,**kwargs):self.call=(url,kwargs);return '<rss><channel/></rss>'

def test_http_transport_is_injectable_and_preserves_contract():
    transport=EmptyTransport();assert GoogleNewsCollector(transport).collect('Marinha')==[];url,kwargs=transport.call;assert url.startswith('https://news.google.com/rss/search?q=Marinha&') and kwargs['connect_timeout']==8.0 and kwargs['read_timeout']==10.0
