from __future__ import annotations

import tempfile
from pathlib import Path

from monitor_noticias.collectors.video import YouTubeCollector
from monitor_noticias.collectors.video.sources import DESKTOP_VIDEO_EXTRAS
from monitor_noticias.database import NewsDb
from monitor_noticias.repositories import NewsRepository


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="monitor-pass14-") as tmp:
        db=NewsDb(Path(tmp)/"news.db")
        try:
            for term in db.listTerms(): db.removeTerm(term)
            db.addTerm("MARINHA")
            result=NewsRepository(db,national_sources=()).search((),True)
            stored=db.listNews(200)
            if result.foundCount < 1 or not stored:
                raise SystemExit("LIVE NEWS FAIL: Google News respondeu, mas pipeline não persistiu resultado para MARINHA")
            print(f"LIVE NEWS OK found={result.foundCount} new={result.newCount} stored={len(stored)}")
        finally:
            db.close()
    g1=next(source for source in DESKTOP_VIDEO_EXTRAS if source.id=="youtube-g1")
    items=YouTubeCollector().collect(g1,0)
    if not items:
        raise SystemExit("LIVE VIDEO FAIL: canal oficial g1 não retornou itens")
    print(f"LIVE VIDEO COLLECTOR OK items={len(items)}")
    return 0

if __name__=="__main__": raise SystemExit(main())
