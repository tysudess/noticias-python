from __future__ import annotations

import logging
from PySide6.QtCore import QDateTime, QTimer
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QFrame,QHBoxLayout,QLabel,QMainWindow,QMenu,QPushButton,QStackedWidget,QStyle,QSystemTrayIcon,QVBoxLayout,QWidget

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.collectors.video.catalog import VIDEO_SOURCES
from monitor_noticias.ui.catalog import NEWS_SOURCES, SPECIALIZED
from monitor_noticias.ui.controller import MainUiController
from monitor_noticias.ui.extractor_page import ExtractorPage
from monitor_noticias.ui.pdf_editor_page import PdfEditorPage
from monitor_noticias.ui.video_editor_page import VideoEditorPage
from monitor_noticias.ui.pages import DemandsPage,HistoryPage,HomePage,NewsPage,SettingsPage,StopPage,VideosPage
from monitor_noticias.ui.runtime_pages import TermsPage
from monitor_noticias.ui.source_page import SourcesPage
from monitor_noticias.ui.sections import SECTION_ORDER,Section
from monitor_noticias.ui.theme import APP_STYLESHEET
from monitor_noticias.windows.notifications import WindowsTrayNotifier

log=logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self,controller:MainUiController|None=None,paths:AppPaths|None=None)->None:
        super().__init__(); self.paths=paths or (controller.paths if controller is not None else AppPaths.discover())
        self.controller=controller or MainUiController.create_default(self.paths,news_sources=NEWS_SOURCES,video_sources=VIDEO_SOURCES,specialized_sources=SPECIALIZED)
        self._allow_close=False; self._current=Section.HOME
        self.setWindowTitle("Monitor de Notícias - Windows Portable v4.0.2"); self.resize(1600,960)
        icon_path=self.paths.resources/"monitor-icon.svg"
        if icon_path.is_file(): self.setWindowIcon(QIcon(str(icon_path)))
        self.setStyleSheet(APP_STYLESHEET); self._build_ui(); self._build_tray()
        if hasattr(self.controller,"set_notifier"): self.controller.set_notifier(self.notifier)
        self.controller.subscribe(self._state_changed)
        self._timer=QTimer(self); self._timer.setInterval(250); self._timer.timeout.connect(self._tick); self._timer.start(); self.navigate(Section.HOME)

    def _build_ui(self)->None:
        root=QWidget(); root.setObjectName("root"); self.setCentralWidget(root); outer=QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        self.sidebar=QFrame(); self.sidebar.setObjectName("sidebar"); self.sidebar.setFixedWidth(258); side=QVBoxLayout(self.sidebar); side.setContentsMargins(14,16,14,14); side.setSpacing(5)
        brand=QLabel("MONITOR DE NOTÍCIAS"); brand.setObjectName("brandTitle"); side.addWidget(brand); sub=QLabel("Centro de monitoramento • Windows"); sub.setObjectName("brandSub"); side.addWidget(sub); side.addSpacing(12)
        self.nav_buttons={}
        for section in SECTION_ORDER:
            button=QPushButton(f"{section.value.icon}   {section.value.label}"); button.setObjectName("navButton"); button.setCheckable(True); button.setMinimumHeight(36); button.clicked.connect(lambda _=False,s=section:self.navigate(s)); side.addWidget(button); self.nav_buttons[section]=button
        side.addStretch(); self.sidebar_status=QLabel(); self.sidebar_status.setObjectName("brandSub"); self.sidebar_status.setWordWrap(True); side.addWidget(self.sidebar_status); ver=QLabel("Windows Portable v4.0.2"); ver.setObjectName("brandSub"); side.addWidget(ver); outer.addWidget(self.sidebar)
        content=QWidget(); cl=QVBoxLayout(content); cl.setContentsMargins(18,12,18,8); cl.setSpacing(8); header=QHBoxLayout(); text=QVBoxLayout(); self.kicker=QLabel("CENTRAL DE MONITORAMENTO"); self.kicker.setObjectName("pageKicker"); self.title=QLabel(); self.title.setObjectName("pageTitle"); self.subtitle=QLabel(); self.subtitle.setObjectName("pageSubtitle"); text.addWidget(self.kicker); text.addWidget(self.title); text.addWidget(self.subtitle); header.addLayout(text); header.addStretch(); self.clock=QLabel(); self.clock.setObjectName("muted"); header.addWidget(self.clock); cl.addLayout(header)
        self.stack=QStackedWidget(); cl.addWidget(self.stack,1)
        self.pages={Section.HOME:HomePage(self.controller),Section.NEWS:NewsPage(self.controller),Section.VIDEOS:VideosPage(self.controller),Section.DEMANDS:DemandsPage(self.controller),Section.SOURCES:SourcesPage(self.controller),Section.HISTORY:HistoryPage(self.controller),Section.TERMS:TermsPage(self.controller),Section.STOP:StopPage(self.controller),Section.SETTINGS:SettingsPage(self.controller),Section.PDF_EDITOR:PdfEditorPage(self.paths.root),Section.EXTRACTOR:ExtractorPage(self.paths.root),Section.VIDEO_EDITOR:VideoEditorPage(self.paths.root)}
        for section in SECTION_ORDER:self.stack.addWidget(self.pages[section])
        home=self.pages[Section.HOME]
        if isinstance(home,HomePage):home.navigate.connect(lambda name:self.navigate(Section[name]))
        pdf_page=self.pages[Section.PDF_EDITOR]
        if isinstance(pdf_page,PdfEditorPage):pdf_page.back_requested.connect(lambda:self.navigate(Section.HOME))
        video_page=self.pages[Section.VIDEO_EDITOR]
        if isinstance(video_page,VideoEditorPage):video_page.back_requested.connect(lambda:self.navigate(Section.HOME))
        footer=QHBoxLayout(); self.footer_left=QLabel(); self.footer_left.setObjectName("muted"); footer.addWidget(self.footer_left); footer.addStretch(); self.footer_right=QLabel(); self.footer_right.setObjectName("muted"); footer.addWidget(self.footer_right); cl.addLayout(footer); outer.addWidget(content,1)

    def _build_tray(self)->None:
        icon=self.windowIcon()
        if icon.isNull():icon=self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray=QSystemTrayIcon(icon,self); self.tray.setToolTip("Monitor de Notícias"); menu=QMenu(); open_action=menu.addAction("Abrir"); open_action.triggered.connect(self._restore); menu.addSeparator()
        news=menu.addAction("Buscar notícias agora"); news.triggered.connect(self.controller.search_news); videos=menu.addAction("Buscar vídeos agora"); videos.triggered.connect(self.controller.search_videos); demands=menu.addAction("Buscar demandas agora"); demands.triggered.connect(self.controller.search_all_demands); stop=menu.addAction("Parar buscas"); stop.triggered.connect(self.controller.stop_all_searches); menu.addSeparator(); exit_action=menu.addAction("Sair"); exit_action.triggered.connect(self.exit_application)
        self.tray.setContextMenu(menu); self.tray.activated.connect(lambda reason:self._restore() if reason==QSystemTrayIcon.ActivationReason.Trigger else None)
        if QSystemTrayIcon.isSystemTrayAvailable():self.tray.show()
        self.notifier=WindowsTrayNotifier(self.tray)

    def navigate(self,section:Section)->None:
        self._current=section; self.stack.setCurrentIndex(SECTION_ORDER.index(section))
        for sec,button in self.nav_buttons.items():button.setChecked(sec==section)
        self.title.setText(section.value.label); self.subtitle.setText(section.value.subtitle); self.pages[section].refresh(self.controller.state)

    def _tick(self)->None:
        self.controller.sync_automation_state(); self.pages[self._current].refresh(self.controller.state); self.clock.setText(QDateTime.currentDateTime().toString("dd/MM/yyyy  •  HH:mm:ss")); state=self.controller.state; cfg=self.controller.proxy_config; auto=self.controller.automation_settings
        self.sidebar_status.setText(f"● Sistema operacional\nDados locais • modo portátil\n{cfg.status_label}\nAutomação {'ativa' if auto.automatic_monitoring else 'pausada'}"); self.footer_left.setText("Busca em andamento" if state.news_busy or state.video_busy else "Sistema operacional"); self.footer_right.setText(f"Notícias: {state.status}   •   Vídeos: {state.video_status}")

    def _state_changed(self,_state)->None:
        pass
    def _restore(self)->None:self.show(); self.raise_(); self.activateWindow()
    def closeEvent(self,event:QCloseEvent)->None:
        if self._allow_close:event.accept(); return
        event.ignore(); self.hide()
    def exit_application(self)->None:
        extractor=self.pages.get(Section.EXTRACTOR)
        if isinstance(extractor,ExtractorPage) and not extractor.shutdown():
            self.footer_right.setText("Aguardando o Extrator encerrar a operação ativa antes de sair."); self._restore(); return
        video_editor=self.pages.get(Section.VIDEO_EDITOR)
        if isinstance(video_editor,VideoEditorPage) and not video_editor.shutdown():
            self.footer_right.setText("Não foi possível fechar todas as janelas do Editor de Vídeo."); self._restore(); return
        self._allow_close=True; self._timer.stop(); self.controller.close(); self.tray.hide(); self.close()
