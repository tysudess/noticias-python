from __future__ import annotations

from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.collectors.video.catalog import DEFAULT_IDS, selected as select_video_sources
from monitor_noticias.collectors.video.sources import DESKTOP_VIDEO_EXTRAS
from monitor_noticias.models import Demand, MediaSource
from monitor_noticias.repositories import NewsRepository, VideoRepository


class RuntimeNewsRunner:
    def __init__(
        self,
        repository: NewsRepository,
        prefs: SharedPreferences,
        news_sources,
        *,
        specialized_source_ids=None,
    ) -> None:
        self.repository = repository
        self.prefs = prefs
        self.by_id = {source.id: source for source in news_sources}
        # Por compatibilidade, os ids conhecidos do catálogo especializado
        # são detectados pelo prefixo histórico, ou podem ser informados pelo
        # composition root para catálogos que usem outra convenção.
        supplied_ids = specialized_source_ids
        self.specialized_source_ids = frozenset(
            str(value)
            for value in (
                supplied_ids
                if supplied_ids is not None
                else (
                    source_id
                    for source_id in self.by_id
                    if source_id.startswith("especializada-")
                )
            )
        )

    def _selection(self):
        """Retorna uma seleção combinada sem misturar os controles das abas.

        ``desktop_news_all_sources`` é a preferência antiga. A nova preferência
        de mídia especializada usa essa opção como fallback para preservar a
        configuração de instalações existentes até que o usuário a altere na
        aba correspondente.
        """
        all_news = self.prefs.get_boolean(
            "desktop_news_all_sources",
            True,
        )
        all_specialized = self.prefs.get_boolean(
            "desktop_specialized_all_sources",
            all_news,
        )

        raw_news_ids = self.prefs.get_string_set(
            "desktop_news_source_ids",
            set(),
        ) or set()
        legacy_specialized_ids = {
            str(value)
            for value in raw_news_ids
            if str(value) in self.specialized_source_ids
        }
        raw_specialized_ids = self.prefs.get_string_set(
            "desktop_specialized_source_ids",
            legacy_specialized_ids,
        ) or set()

        general_ids = set(self.by_id) - self.specialized_source_ids
        if all_news:
            general_sources = [
                self.by_id[source_id]
                for source_id in sorted(general_ids)
            ]
        else:
            general_sources = [
                self.by_id[str(source_id)]
                for source_id in sorted(raw_news_ids)
                if str(source_id) in self.by_id
                and str(source_id) not in self.specialized_source_ids
            ]

        if all_specialized:
            specialized_sources = [
                self.by_id[source_id]
                for source_id in sorted(self.specialized_source_ids)
                if source_id in self.by_id
            ]
        else:
            specialized_sources = [
                self.by_id[str(source_id)]
                for source_id in sorted(raw_specialized_ids)
                if str(source_id) in self.by_id
                and str(source_id) in self.specialized_source_ids
            ]

        # O modo irrestrito só é usado quando os dois grupos estão inteiros
        # ativos. Nos demais casos, o repositório filtra pelo conjunto combinado.
        if all_news and all_specialized:
            return (), True

        combined = {
            source.id: source
            for source in (*general_sources, *specialized_sources)
        }
        return tuple(combined.values()), False

    def search_news(self, *, token, progress, from_ms=None, to_ms=None):
        selected, all_sources = self._selection()
        token.raise_if_cancelled()
        callback = lambda state, _items=(): progress(state)
        if from_ms is None or to_ms is None:
            return self.repository.search(
                selected,
                all_sources,
                on_update=callback,
                cancel=token.raise_if_cancelled,
            )
        return self.repository.search_period(
            from_ms,
            to_ms,
            selected,
            all_sources,
            on_update=callback,
            cancel=token.raise_if_cancelled,
        )

    def search_demand(self, demand: Demand, *, token):
        return self.repository.search_demand(
            demand,
            cancel=token.raise_if_cancelled,
        )

    def search_all_demands(self, *, token):
        return self.repository.search_all_demands(
            cancel=token.raise_if_cancelled,
        )


class RuntimeVideoRunner:
    def __init__(self, repository: VideoRepository, prefs: SharedPreferences) -> None:
        self.repository = repository
        self.prefs = prefs
        self._migrate_desktop_extras()

    def _migrate_desktop_extras(self):
        key = "desktop_video_sources_v6_migrated"
        if self.prefs.get_boolean(key, False):
            return
        current = self.prefs.get_string_set(
            "desktop_video_source_ids",
            set(DEFAULT_IDS),
        ) or set(DEFAULT_IDS)
        current |= {source.id for source in DESKTOP_VIDEO_EXTRAS}
        self.prefs.update(
            desktop_video_source_ids=current,
            **{key: True},
        )

    def selected_ids(self):
        return self.prefs.get_string_set(
            "desktop_video_source_ids",
            set(DEFAULT_IDS),
        ) or set(DEFAULT_IDS)

    def search_videos(self, *, token, progress, from_ms=None, to_ms=None):
        token.raise_if_cancelled()
        sources = select_video_sources(self.selected_ids())
        callback = lambda state, _items=(): progress(state)
        return self.repository.search(
            sources,
            from_ms=from_ms,
            to_ms=to_ms,
            on_update=callback,
            cancel=token.raise_if_cancelled,
        )
