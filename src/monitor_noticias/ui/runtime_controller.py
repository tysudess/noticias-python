from __future__ import annotations

import time

from monitor_noticias.repositories import VideoTermStore
from .controller import MainUiController


DAY_MS = 24 * 60 * 60 * 1000


class RuntimeUiController(MainUiController):
    """Controller de produção: somente ponte UI ↔ serviços reais.

    Correção V8:
    - a aba Vídeos inicia mostrando somente as últimas 24 horas;
    - 24h / 7 dias / 30 dias / personalizado passam a controlar também
      o período exibido na lista;
    - uma busca de Notícias não volta mais a lista de Vídeos para 7 dias;
    - "Buscar vídeos agora" usa explicitamente as últimas 24 horas;
    - buscas automáticas continuam usando as últimas 24 horas.
    """

    def __init__(
        self,
        *,
        default_video_source_ids,
        video_term_store: VideoTermStore,
        **kwargs,
    ) -> None:
        self.default_video_source_ids = set(default_video_source_ids)
        self.video_term_store = video_term_store
        self.video_terms = []

        self._last_news_busy = False
        self._last_video_busy = False
        self._runtime_closed = False

        # A interface de Vídeos abre em "24 horas".
        now = int(time.time() * 1000)
        self._video_view_to_ms = now
        self._video_view_from_ms = now - DAY_MS

        super().__init__(**kwargs)

        self.video_terms = self.video_term_store.load(
            self.state.terms
        )

        # MainUiController carrega 7 dias por compatibilidade com o histórico.
        # Na interface atual, porém, o botão selecionado por padrão é "24 horas".
        # Portanto corrigimos imediatamente a lista visível.
        self.state.videos = self.video_db.listPeriod(
            self._video_view_from_ms,
            self._video_view_to_ms,
            1500,
        )
        self._emit()

    @property
    def selected_video_source_ids(self) -> set[str]:
        return (
            self.prefs.get_string_set(
                "desktop_video_source_ids",
                set(self.default_video_source_ids),
            )
            or set()
        )

    @selected_video_source_ids.setter
    def selected_video_source_ids(
        self,
        value: set[str],
    ) -> None:
        self.prefs.update(
            desktop_video_source_ids=set(value)
        )

    @property
    def video_view_period(self) -> tuple[int, int]:
        """Período que deve estar visível na aba Vídeos."""
        return (
            self._video_view_from_ms,
            self._video_view_to_ms,
        )

    def search_videos(
        self,
        from_ms: int | None = None,
        to_ms: int | None = None,
    ) -> bool:
        """Executa a busca e fixa a lista exatamente no período solicitado.

        Quando a UI chama sem datas ("Buscar vídeos agora"), o período é
        explicitamente convertido em últimas 24 horas.
        """
        if self.automation is None:
            return self._missing_search_engine("Vídeos")

        if from_ms is None or to_ms is None:
            from_ms, to_ms = self.period_last_hours(24)

        from_ms = int(from_ms)
        to_ms = int(to_ms)

        if to_ms < from_ms:
            from_ms, to_ms = to_ms, from_ms

        self._video_view_from_ms = from_ms
        self._video_view_to_ms = to_ms

        # Mantém a lista já existente limitada ao novo período enquanto
        # a nova busca roda. Assim itens antigos não permanecem na tela.
        self.state.videos = self.video_db.listPeriod(
            from_ms,
            to_ms,
            1500,
        )

        ok = self.automation.search_videos(
            from_ms,
            to_ms,
        )

        self.sync_automation_state()
        self._emit()

        return ok

    def search_demand(self, demand) -> bool:
        if self.automation is None:
            return self._missing_search_engine("Demandas")

        ok = self.automation.search_demand(demand)
        self.sync_automation_state()
        self._emit()
        return ok

    def add_video_term(self, value: str) -> None:
        self.video_terms = self.video_term_store.add(
            value,
            self.news_db.listTerms(),
        )
        self._emit()

    def remove_video_term(self, value: str) -> None:
        self.video_terms = self.video_term_store.remove(
            value,
            self.news_db.listTerms(),
        )
        self._emit()

    def sync_automation_state(self) -> None:
        """Sincroniza estado sem misturar janela temporal de Notícias e Vídeos."""
        was_news = self._last_news_busy
        was_video = self._last_video_busy

        super().sync_automation_state()

        if self.automation is None:
            return

        automation_state = self.automation.state

        self.state.new_news_links = set(
            getattr(
                automation_state,
                "newNewsLinks",
                set(),
            )
        )
        self.state.new_video_links = set(
            getattr(
                automation_state,
                "newVideoLinks",
                set(),
            )
        )

        now_news = self.state.news_busy
        now_video = self.state.video_busy

        # Busca automática de vídeo é disparada diretamente pelo
        # AutomationService, sem passar por search_videos() da UI.
        # Quando detectamos esse início, voltamos a janela visual para 24h.
        if not was_video and now_video:
            status = (
                self.state.video_status
                or ""
            ).lower()

            if "no período" not in status:
                (
                    self._video_view_from_ms,
                    self._video_view_to_ms,
                ) = self.period_last_hours(24)

        # IMPORTANTE:
        # Antes, ao terminar QUALQUER busca (notícia OU vídeo),
        # o código executava:
        #
        #   self.state.videos = self.video_db.listRecent(7, 1500)
        #
        # Isso é exatamente o que fazia vídeos de 15/09 reaparecerem
        # em 18/09 mesmo com "24 horas" selecionado.
        #
        # Agora cada área atualiza apenas seu próprio conteúdo.

        if was_news and not now_news:
            self.state.news = self.news_db.listRecent(
                24,
                1000,
            )
            self.state.terms = self.news_db.listTerms()
            self.state.demands = self.news_db.listDemands()
            self.video_terms = self.video_term_store.load(
                self.state.terms
            )

        if was_video and not now_video:
            self.state.videos = self.video_db.listPeriod(
                self._video_view_from_ms,
                self._video_view_to_ms,
                1500,
            )

        self._last_news_busy = now_news
        self._last_video_busy = now_video

    def set_notifier(self, notifier) -> None:
        if self.automation is not None:
            self.automation.notify = notifier

    def close(self) -> None:
        if self._runtime_closed:
            return

        self._runtime_closed = True
        super().close()
