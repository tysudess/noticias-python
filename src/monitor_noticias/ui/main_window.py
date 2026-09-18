from __future__ import annotations

import logging

from PySide6.QtCore import QDateTime, QTimer, Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.collectors.video.catalog import VIDEO_SOURCES
from monitor_noticias.ui.catalog import NEWS_SOURCES, SPECIALIZED
from monitor_noticias.ui.controller import MainUiController
from monitor_noticias.ui.demands_page import DemandsPage
from monitor_noticias.ui.extractor_reference_page import (
    ReferenceExtractorPage as ExtractorPage,
)
from monitor_noticias.ui.layout_refresh import apply_reference_layout
from monitor_noticias.ui.pdf_editor_reference_page import (
    ReferencePdfEditorPage as PdfEditorPage,
)
from monitor_noticias.ui.video_editor_reference_page import (
    ReferenceVideoEditorPage as VideoEditorPage,
)
from monitor_noticias.ui.home_page import HomePage
from monitor_noticias.ui.news_page import NewsPage
from monitor_noticias.ui.news_extractor_page import NewsExtractorPage
from monitor_noticias.ui.covers_reference_page import (
    ReferenceCoversPage as CoversPage,
)
from monitor_noticias.ui.pages import StopPage
from monitor_noticias.ui.history_page import HistoryPage
from monitor_noticias.ui.settings_reference_page import (
    ReferenceSettingsPage as SettingsPage,
)
from monitor_noticias.ui.terms_page import TermsPage
from monitor_noticias.ui.source_page import SourcesPage
from monitor_noticias.ui.videos_page import VideosPage
from monitor_noticias.ui.sections import SECTION_ORDER, Section
from monitor_noticias.ui.sidebar_widgets import (
    SIDEBAR_STYLE,
    SidebarNavItem,
)
from monitor_noticias.ui.theme import APP_STYLESHEET
from monitor_noticias.windows.notifications import WindowsTrayNotifier

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: MainUiController | None = None,
        paths: AppPaths | None = None,
    ) -> None:
        super().__init__()

        self.paths = paths or (
            controller.paths
            if controller is not None
            else AppPaths.discover()
        )

        self.controller = controller or MainUiController.create_default(
            self.paths,
            news_sources=NEWS_SOURCES,
            video_sources=VIDEO_SOURCES,
            specialized_sources=SPECIALIZED,
        )

        self._allow_close = False
        self._current = Section.HOME

        self.setWindowTitle(
            "Central Inteligente de Mídia - Windows Portable v4.0.2"
        )
        self.resize(1600, 960)
        self.setMinimumSize(1180, 720)

        icon_path = self.paths.resources / "monitor-icon.svg"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setStyleSheet(APP_STYLESHEET + SIDEBAR_STYLE)

        self._build_ui()
        self._build_tray()
        apply_reference_layout(self)

        if hasattr(self.controller, "set_notifier"):
            self.controller.set_notifier(self.notifier)

        self.controller.subscribe(self._state_changed)

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self.navigate(Section.HOME)

    # -----------------------------------------------------------------
    # SIDEBAR
    # -----------------------------------------------------------------

    def _sidebar_navigation_order(self) -> tuple[Section, ...]:
        """Ordem visual exatamente igual à imagem de referência.

        A ordem do QStackedWidget continua usando SECTION_ORDER.
        Portanto mudar a ordem visual aqui não quebra os índices das páginas.
        """
        return (
            Section.HOME,
            Section.NEWS,
            Section.VIDEOS,
            Section.DEMANDS,
            Section.SOURCES,
            Section.HISTORY,
            Section.TERMS,
            Section.STOP,
            Section.NEWS_EXTRACTOR,
            Section.COVERS,
            Section.PDF_EDITOR,
            Section.EXTRACTOR,
            Section.VIDEO_EDITOR,
            Section.SETTINGS,
        )

    @staticmethod
    def _sidebar_icon_data(section: Section) -> tuple[str, str]:
        data = {
            Section.HOME: ("⌂", "#FFFFFF"),
            Section.NEWS: ("▤", "#A8D8FF"),
            Section.VIDEOS: ("▶", "#FF4262"),
            Section.DEMANDS: ("✓", "#24E3B3"),
            Section.SOURCES: ("Aa", "#B16DFF"),
            Section.HISTORY: ("◷", "#FFAA00"),
            Section.TERMS: ("▤", "#AABCD9"),
            Section.STOP: ("⌕", "#31D6FF"),
            Section.SETTINGS: ("✿", "#AD70FF"),
            Section.NEWS_EXTRACTOR: ("▣", "#38DDD0"),
            Section.COVERS: ("◆", "#EE5AC9"),
            Section.PDF_EDITOR: ("PDF", "#FF5574"),
            Section.EXTRACTOR: ("☁", "#4DDEDE"),
            Section.VIDEO_EDITOR: ("▰", "#B867F6"),
        }
        return data.get(section, ("•", "#FFFFFF"))

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(184)

        side = QVBoxLayout(sidebar)
        side.setContentsMargins(8, 10, 8, 10)
        side.setSpacing(3)

        # Logo / marca
        brand_wrap = QFrame()
        brand_wrap.setObjectName("sidebarBrandWrap")

        brand_row = QHBoxLayout(brand_wrap)
        brand_row.setContentsMargins(10, 3, 5, 7)
        brand_row.setSpacing(9)

        logo = QLabel("▣")
        logo.setObjectName("sidebarLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(36, 36)
        brand_row.addWidget(logo)

        brand_text = QVBoxLayout()
        brand_text.setContentsMargins(0, 1, 0, 0)
        brand_text.setSpacing(0)

        brand = QLabel("CENTRAL")
        brand.setObjectName("sidebarBrandTitle")

        sub = QLabel("INTELIGENTE DE MÍDIA")
        sub.setObjectName("sidebarBrandSub")

        brand_text.addWidget(brand)
        brand_text.addWidget(sub)
        brand_row.addLayout(brand_text, 1)

        side.addWidget(brand_wrap)
        side.addSpacing(2)

        # Itens
        self.nav_buttons: dict[Section, SidebarNavItem] = {}

        for section in self._sidebar_navigation_order():
            icon_text, icon_color = self._sidebar_icon_data(section)

            item = SidebarNavItem(
                icon_text=icon_text,
                label_text=section.value.label,
                icon_color=icon_color,
            )

            item.clicked.connect(
                lambda s=section: self.navigate(s)
            )

            side.addWidget(item)
            self.nav_buttons[section] = item

        side.addStretch(1)

        # Card de status inferior
        self.sidebar_status_card = QFrame()
        self.sidebar_status_card.setObjectName(
            "sidebarStatusCard"
        )

        status_row = QHBoxLayout(
            self.sidebar_status_card
        )
        status_row.setContentsMargins(10, 7, 9, 7)
        status_row.setSpacing(8)

        status_icon = QLabel("▱")
        status_icon.setObjectName("sidebarStatusIcon")
        status_icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        status_icon.setFixedWidth(20)
        status_row.addWidget(status_icon)

        status_text = QVBoxLayout()
        status_text.setSpacing(0)

        self.sidebar_status_title = QLabel(
            "Sistema operacional"
        )
        self.sidebar_status_title.setObjectName(
            "sidebarStatusTitle"
        )

        self.sidebar_status = QLabel(
            "Windows Portable v4.0.2"
        )
        self.sidebar_status.setObjectName(
            "sidebarStatusText"
        )

        status_text.addWidget(
            self.sidebar_status_title
        )
        status_text.addWidget(
            self.sidebar_status
        )

        status_row.addLayout(status_text, 1)

        side.addWidget(self.sidebar_status_card)

        return sidebar

    # -----------------------------------------------------------------
    # UI
    # -----------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.sidebar = self._build_sidebar()
        outer.addWidget(self.sidebar)

        content = QWidget()

        cl = QVBoxLayout(content)
        cl.setContentsMargins(18, 12, 18, 10)
        cl.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(12)

        self.header_identity = QWidget()

        text = QVBoxLayout(self.header_identity)
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(0)

        self.kicker = QLabel(
            "CENTRAL DE INTELIGÊNCIA DE MÍDIA"
        )
        self.kicker.setObjectName("pageKicker")

        self.title = QLabel()
        self.title.setObjectName("pageTitle")

        self.subtitle = QLabel()
        self.subtitle.setObjectName("pageSubtitle")

        text.addWidget(self.kicker)
        text.addWidget(self.title)
        text.addWidget(self.subtitle)

        header.addWidget(self.header_identity, 2)

        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText(
            "🔎  Buscar notícias, vídeos, demandas ou fontes...    Ctrl + K"
        )
        self.global_search.setMinimumWidth(390)
        self.global_search.returnPressed.connect(
            self._run_global_search
        )

        header.addWidget(self.global_search, 3)

        self.proxy_chip = QLabel("●  Proxy pronto")
        self.proxy_chip.setObjectName("chipGreen")
        header.addWidget(self.proxy_chip)

        self.auto_chip = QLabel("●  Automação ativa")
        self.auto_chip.setObjectName("chipGreen")
        header.addWidget(self.auto_chip)

        self.clock = QLabel()
        self.clock.setObjectName("clockCard")
        self.clock.setMinimumWidth(180)
        header.addWidget(self.clock)

        cl.addLayout(header)

        self.stack = QStackedWidget()
        cl.addWidget(self.stack, 1)

        self.pages = {
            Section.HOME: HomePage(self.controller),
            Section.NEWS: NewsPage(self.controller),
            Section.VIDEOS: VideosPage(self.controller),
            Section.DEMANDS: DemandsPage(self.controller),
            Section.SOURCES: SourcesPage(self.controller),
            Section.HISTORY: HistoryPage(self.controller),
            Section.TERMS: TermsPage(self.controller),
            Section.STOP: StopPage(self.controller),
            Section.SETTINGS: SettingsPage(self.controller),
            Section.NEWS_EXTRACTOR: NewsExtractorPage(
                self.paths.root
            ),
            Section.COVERS: CoversPage(self.paths.root),
            Section.PDF_EDITOR: PdfEditorPage(
                self.paths.root
            ),
            Section.EXTRACTOR: ExtractorPage(
                self.paths.root
            ),
            Section.VIDEO_EDITOR: VideoEditorPage(
                self.paths.root
            ),
        }

        # IMPORTANTE:
        # O stack continua exatamente na ordem de SECTION_ORDER.
        for section in SECTION_ORDER:
            self.stack.addWidget(
                self.pages[section]
            )

        home = self.pages[Section.HOME]
        if isinstance(home, HomePage):
            home.navigate.connect(
                lambda name: self.navigate(
                    Section[name]
                )
            )

        news_page = self.pages[Section.NEWS]
        if isinstance(news_page, NewsPage):
            news_page.extract_requested.connect(
                self._open_news_extractor_link
            )

        videos_page = self.pages[Section.VIDEOS]
        if isinstance(videos_page, VideosPage):
            videos_page.extract_requested.connect(
                self._open_video_extractor_link
            )

        pdf_page = self.pages[
            Section.PDF_EDITOR
        ]
        if isinstance(pdf_page, PdfEditorPage):
            pdf_page.back_requested.connect(
                lambda: self.navigate(
                    Section.HOME
                )
            )

        video_page = self.pages[
            Section.VIDEO_EDITOR
        ]
        if isinstance(
            video_page,
            VideoEditorPage,
        ):
            video_page.back_requested.connect(
                lambda: self.navigate(
                    Section.HOME
                )
            )

        footer = QHBoxLayout()

        self.footer_left = QLabel()
        self.footer_left.setObjectName("muted")

        self.footer_right = QLabel()
        self.footer_right.setObjectName("muted")

        footer.addWidget(self.footer_left)
        footer.addStretch()
        footer.addWidget(self.footer_right)

        cl.addLayout(footer)

        outer.addWidget(content, 1)

    # -----------------------------------------------------------------
    # TRAY
    # -----------------------------------------------------------------

    def _build_tray(self) -> None:
        icon = self.windowIcon()

        if icon.isNull():
            icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_ComputerIcon
            )

        self.tray = QSystemTrayIcon(
            icon,
            self,
        )
        self.tray.setToolTip(
            "Central Inteligente de Mídia"
        )

        menu = QMenu()

        open_action = menu.addAction(
            "Abrir"
        )
        open_action.triggered.connect(
            self._restore
        )

        menu.addSeparator()

        news = menu.addAction(
            "Buscar notícias agora"
        )
        news.triggered.connect(
            self.controller.search_news
        )

        videos = menu.addAction(
            "Buscar vídeos agora"
        )
        videos.triggered.connect(
            self.controller.search_videos
        )

        demands = menu.addAction(
            "Buscar demandas agora"
        )
        demands.triggered.connect(
            self.controller.search_all_demands
        )

        stop = menu.addAction(
            "Parar buscas"
        )
        stop.triggered.connect(
            self.controller.stop_all_searches
        )

        menu.addSeparator()

        exit_action = menu.addAction(
            "Sair"
        )
        exit_action.triggered.connect(
            self.exit_application
        )

        self.tray.setContextMenu(menu)

        self.tray.activated.connect(
            lambda reason: self._restore()
            if reason
            == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

        self.notifier = WindowsTrayNotifier(
            self.tray
        )

    # -----------------------------------------------------------------
    # ACTIONS
    # -----------------------------------------------------------------

    def _run_global_search(self) -> None:
        text = self.global_search.text().strip()

        if not text:
            self.controller.search_news()
            return

        lowered = text.lower()

        if "video" in lowered or "vídeo" in lowered:
            self.navigate(Section.VIDEOS)

        elif "demanda" in lowered:
            self.navigate(Section.DEMANDS)

        elif "fonte" in lowered:
            self.navigate(Section.SOURCES)

        else:
            self.navigate(Section.NEWS)

            page = self.pages.get(
                Section.NEWS
            )

            if hasattr(page, "query"):
                page.query.setText(text)

    def _open_video_extractor_link(
        self,
        url: str,
    ) -> None:
        extractor = self.pages.get(
            Section.EXTRACTOR
        )

        if isinstance(
            extractor,
            ExtractorPage,
        ):
            field = getattr(
                extractor,
                "url",
                None,
            )

            if field is not None:
                field.setText(url)

            self.navigate(
                Section.EXTRACTOR
            )

    def _open_news_extractor_link(
        self,
        url: str,
    ) -> None:
        page = self.pages.get(
            Section.NEWS_EXTRACTOR
        )

        if isinstance(
            page,
            NewsExtractorPage,
        ):
            self.navigate(
                Section.NEWS_EXTRACTOR
            )
            page.open_url(url)

    # -----------------------------------------------------------------
    # NAVIGATION
    # -----------------------------------------------------------------

    def navigate(
        self,
        section: Section,
    ) -> None:
        self._current = section

        self.stack.setCurrentIndex(
            SECTION_ORDER.index(section)
        )

        for sec, button in self.nav_buttons.items():
            button.set_active(
                sec == section
            )

        self.title.setText(
            section.value.label
        )
        self.subtitle.setText(
            section.value.subtitle
        )

        hide_identity = {
            Section.NEWS,
            Section.SETTINGS,
            Section.NEWS_EXTRACTOR,
            Section.COVERS,
            Section.PDF_EDITOR,
            Section.EXTRACTOR,
            Section.VIDEO_EDITOR,
        }

        self.header_identity.setVisible(
            section not in hide_identity
        )

        self.pages[section].refresh(
            self.controller.state
        )

    # -----------------------------------------------------------------
    # STATUS
    # -----------------------------------------------------------------

    def _tick(self) -> None:
        self.controller.sync_automation_state()

        self.pages[
            self._current
        ].refresh(
            self.controller.state
        )

        # Branding centralizado. O HomePage ainda usa internamente o nome
        # histórico em uma linha de atividade; trocamos somente a apresentação.
        home_page = self.pages.get(Section.HOME)
        activities = getattr(home_page, "activities_text", None)
        if activities is not None:
            current_text = activities.text()
            if "Monitor de Notícias v4.0.2" in current_text:
                activities.setText(
                    current_text.replace(
                        "Monitor de Notícias v4.0.2",
                        "Central Inteligente de Mídia v4.0.2",
                    )
                )

        now = QDateTime.currentDateTime()

        self.clock.setText(
            now.toString(
                "dd/MM/yyyy\nHH:mm:ss   ☀  29°C"
            )
        )

        state = self.controller.state
        cfg = self.controller.proxy_config
        auto = self.controller.automation_settings

        self.proxy_chip.setText(
            "●  Proxy pronto"
            if cfg.enabled
            else "○  Proxy inativo"
        )

        self.auto_chip.setText(
            "●  Automação ativa"
            if auto.automatic_monitoring
            else "○  Automação pausada"
        )

        # Card inferior compacto, como no print.
        self.sidebar_status_title.setText(
            "Sistema operacional"
        )
        self.sidebar_status.setText(
            "Windows Portable v4.0.2"
        )

        self.footer_left.setText(
            "Busca em andamento"
            if state.news_busy
            or state.video_busy
            else "Sistema operacional"
        )

        self.footer_right.setText(
            f"Notícias: {state.status}   •   "
            f"Vídeos: {state.video_status}"
        )

    def _state_changed(
        self,
        _state,
    ) -> None:
        pass

    def _restore(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    # -----------------------------------------------------------------
    # CLOSE
    # -----------------------------------------------------------------

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        if self._allow_close:
            event.accept()
            return

        event.ignore()
        self.hide()

    def exit_application(self) -> None:
        extractor = self.pages.get(
            Section.EXTRACTOR
        )

        if (
            isinstance(
                extractor,
                ExtractorPage,
            )
            and not extractor.shutdown()
        ):
            self.footer_right.setText(
                "Aguardando o Extrator encerrar "
                "a operação ativa antes de sair."
            )
            self._restore()
            return

        news_extractor = self.pages.get(
            Section.NEWS_EXTRACTOR
        )

        if isinstance(
            news_extractor,
            NewsExtractorPage,
        ):
            news_extractor.shutdown()

        covers = self.pages.get(
            Section.COVERS
        )

        if isinstance(
            covers,
            CoversPage,
        ):
            covers.shutdown()

        video_editor = self.pages.get(
            Section.VIDEO_EDITOR
        )

        if (
            isinstance(
                video_editor,
                VideoEditorPage,
            )
            and not video_editor.shutdown()
        ):
            self.footer_right.setText(
                "Não foi possível fechar todas as "
                "janelas do Editor de Vídeo."
            )
            self._restore()
            return

        self._allow_close = True
        self._timer.stop()
        self.controller.close()
        self.tray.hide()
        self.close()
