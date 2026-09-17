from __future__ import annotations

from datetime import datetime
import html
import logging
from typing import Callable, Iterable
from urllib.parse import quote

from PySide6.QtCore import QDate, QThread, QTime, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QProgressBar, QScrollArea, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QTimeEdit, QVBoxLayout, QWidget,
)

from monitor_noticias.models import Demand, MediaSource, News, VideoItem, VideoSource
from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.theme import V5_BLUE, V5_GREEN, V5_MUTED, V5_ORANGE, V5_PURPLE, V5_RED

log = logging.getLogger(__name__)


def secondary(button: QPushButton) -> QPushButton:
    button.setProperty("secondary", True)
    return button


def card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame(); frame.setObjectName("card")
    layout = QVBoxLayout(frame); layout.setContentsMargins(14, 12, 14, 12); layout.setSpacing(8)
    return frame, layout


def heading(title: str, subtitle: str = "") -> QWidget:
    widget = QWidget(); layout = QVBoxLayout(widget); layout.setContentsMargins(0, 0, 0, 4); layout.setSpacing(2)
    label = QLabel(title); label.setObjectName("sectionTitle"); layout.addWidget(label)
    if subtitle:
        sub = QLabel(subtitle); sub.setObjectName("muted"); sub.setWordWrap(True); layout.addWidget(sub)
    return widget


def format_time(ms: int) -> str:
    if not ms: return "Nunca"
    return datetime.fromtimestamp(ms / 1000).strftime("%d/%m/%Y %H:%M")


def duration(ms: int) -> str:
    sec = max(0, int(ms // 1000))
    if sec < 60: return f"{sec}s"
    return f"{sec // 60}m {sec % 60}s"


def open_url(url: str) -> None:
    if url: QDesktopServices.openUrl(QUrl(url))


def copy_text(text: str) -> None:
    QApplication.clipboard().setText(text)


def open_whatsapp(title: str, url: str) -> None:
    open_url("https://wa.me/?text=" + quote(f"{title}\n{url}"))


class ProxyTestThread(QThread):
    completed = Signal(bool, str)
    def __init__(self, controller: MainUiController) -> None:
        super().__init__(); self.controller = controller
    def run(self) -> None:
        try: ok, text = self.controller.test_proxy()
        except Exception as exc: ok, text = False, f"Falha no proxy: {str(exc) or exc.__class__.__name__}"
        self.completed.emit(ok, text)


class BasePage(QWidget):
    def __init__(self, controller: MainUiController) -> None:
        super().__init__(); self.controller = controller
        self.root = QVBoxLayout(self); self.root.setContentsMargins(16, 14, 16, 14); self.root.setSpacing(10)
    def refresh(self, state: UiState) -> None: pass


class ExecutionPanel(QFrame):
    def __init__(self, kind: str) -> None:
        super().__init__(); self.kind = kind; self.setObjectName("card")
        box = QVBoxLayout(self); box.setContentsMargins(12, 9, 12, 9); box.setSpacing(5)
        row = QHBoxLayout(); self.title = QLabel(); self.title.setObjectName("sectionTitle"); row.addWidget(self.title)
        row.addStretch(); self.stats = QLabel(); self.stats.setObjectName("muted"); row.addWidget(self.stats); box.addLayout(row)
        self.status = QLabel(); self.status.setObjectName("muted"); box.addWidget(self.status)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); box.addWidget(self.progress)
        self.detail = QLabel(); self.detail.setObjectName("muted"); box.addWidget(self.detail)
    def set_state(self, busy: bool, progress, status: str, fresh: int, elapsed: int) -> None:
        fraction = max(0.0, min(1.0, float(getattr(progress, "fraction", 0.0)))) if busy else 1.0
        pct = round(fraction * 100); completed = getattr(progress, "completed", 0); total = getattr(progress, "total", 0)
        found = getattr(progress, "found", 0); errors = getattr(progress, "errors", 0)
        self.title.setText(f"{self.kind} • {'busca em andamento' if busy else 'última execução concluída'}")
        self.status.setText(status); self.progress.setValue(pct)
        self.stats.setText(f"{pct}%  •  {found} encontrados  •  {fresh} novos  •  {errors} falhas  •  {completed}/{total} etapas  •  {duration(elapsed)}")
        source = getattr(progress, "currentSource", "") or "Preparando..."; query = getattr(progress, "currentQuery", "") or "Preparando consulta..."
        self.detail.setText(f"{source} • {query}" if busy else f"{fresh} novo(s) nesta execução. A marcação Nova é recalculada a cada nova busca.")


class HomePage(BasePage):
    navigate = Signal(str)
    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller)
        self.root.addWidget(heading("Painel principal", "Acompanhe o estado atual e execute as mesmas ações manuais do Monitor."))
        metrics, ml = card(); row = QHBoxLayout(); ml.addLayout(row); self.metric_labels = {}
        for key, label in (("news","Notícias 24h"),("videos","Vídeos"),("today","Vídeos hoje"),("demands","Demandas"),("sources","Fontes")):
            box = QFrame(); lay = QVBoxLayout(box); title = QLabel(label); title.setObjectName("muted"); value=QLabel("0"); value.setStyleSheet("font-size:25px;font-weight:800")
            lay.addWidget(title); lay.addWidget(value); row.addWidget(box); self.metric_labels[key]=value
        self.root.addWidget(metrics)
        actions, al = card(); al.addWidget(heading("Ações rápidas")); ar=QHBoxLayout(); al.addLayout(ar)
        for text, slot, prop in (("Buscar notícias", controller.search_news, ""),("Buscar demandas", controller.search_all_demands, "orange"),("Buscar vídeos", controller.search_videos, "purple"),("Termos de busca", lambda: self.navigate.emit("TERMS"), "green")):
            b=QPushButton(text); b.setObjectName("home_"+text.lower().replace(" ","_"));
            if prop: b.setProperty(prop, True)
            b.clicked.connect(slot); ar.addWidget(b)
        self.root.addWidget(actions)
        summary, sl = card(); self.summary = QLabel(); self.summary.setWordWrap(True); sl.addWidget(heading("Resumo operacional")); sl.addWidget(self.summary); self.root.addWidget(summary)
        self.root.addStretch()
    def refresh(self, state: UiState) -> None:
        now_ms = int(datetime.now().timestamp()*1000); day_ago = now_ms-86_400_000
        self.metric_labels["news"].setText(str(len(state.news))); self.metric_labels["videos"].setText(str(len(state.videos)))
        self.metric_labels["today"].setText(str(sum(1 for v in state.videos if v.capturedAt>=day_ago))); self.metric_labels["demands"].setText(str(sum(1 for d in state.demands if d.active)))
        self.metric_labels["sources"].setText(str(len(self.controller.news_sources)))
        cfg=self.controller.proxy_config; auto=self.controller.automation_settings
        unstable = "Nenhuma" if not state.unstable_video_sources else ", ".join(str(getattr(x,"sourceName",x)) for x in state.unstable_video_sources)
        self.summary.setText(f"Notícias: {state.status}\nVídeos: {state.video_status}\nFontes instáveis: {unstable}\nProxy: {cfg.status_label}\nAutomação: {'Ativa' if auto.automatic_monitoring else 'Pausada'}")


class NewsPage(BasePage):
    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller); self.query=QLineEdit(); self.query.setPlaceholderText("Buscar nas notícias (título, fonte, termo...)"); self.only_demands=QCheckBox("Só demandas")
        top, tl=card(); row=QHBoxLayout(); row.addWidget(self.query,1); self.search24=QPushButton("Buscar últimas 24h"); self.search24.clicked.connect(lambda: controller.search_news(*controller.period_last_hours(24))); row.addWidget(self.search24); row.addWidget(self.only_demands); tl.addLayout(row)
        periods=QHBoxLayout();
        for label,hours in (("Hoje",None),("24 horas",24),("7 dias",168),("30 dias",720)):
            b=secondary(QPushButton(label)); b.clicked.connect((lambda _=False,h=hours: controller.search_news(*(controller.period_today() if h is None else controller.period_last_hours(h))))); periods.addWidget(b)
        self.custom=secondary(QPushButton("Período personalizado")); self.custom.setCheckable(True); periods.addWidget(self.custom); periods.addStretch(); tl.addLayout(periods)
        self.period_box=QFrame(); form=QHBoxLayout(self.period_box); today=QDate.currentDate(); self.start_date=QDateEdit(today.addDays(-1)); self.start_time=QTimeEdit(QTime(0,0)); self.end_date=QDateEdit(today); self.end_time=QTimeEdit(QTime(23,59)); self.period_go=QPushButton("Buscar período")
        for w in (self.start_date,self.start_time,self.end_date,self.end_time,self.period_go): form.addWidget(w)
        self.period_box.hide(); self.custom.toggled.connect(self.period_box.setVisible); self.period_go.clicked.connect(self._period); tl.addWidget(self.period_box); self.root.addWidget(top)
        self.exec=ExecutionPanel("Notícias"); self.root.addWidget(self.exec); self.stop=secondary(QPushButton("Parar busca")); self.stop.clicked.connect(controller.stop_news_search); self.root.addWidget(self.stop,0)
        self.count=QLabel(); self.count.setObjectName("sectionTitle"); self.root.addWidget(self.count); self.table=QTableWidget(0,6); self.table.setHorizontalHeaderLabels(["Data","Fonte","Título","Termo","Demanda","Ações"]); self.table.setAlternatingRowColors(True); self.table.setSortingEnabled(True); self.root.addWidget(self.table,1)
        self.query.textChanged.connect(lambda _: self.refresh(controller.state)); self.only_demands.toggled.connect(lambda _: self.refresh(controller.state))
    def _period(self):
        start=self.start_date.date().toString("yyyy-MM-dd"); st=self.start_time.time().toString("HH:mm"); end=self.end_date.date().toString("yyyy-MM-dd"); et=self.end_time.time().toString("HH:mm"); p=self.controller.parse_period(start,st,end,et)
        if p: self.controller.search_news(*p)
    def _rows(self,state):
        q=self.query.text().strip().lower(); return [n for n in state.news if (not self.only_demands.isChecked() or n.demand) and (not q or q in f"{n.title} {n.source} {n.matchedTerm} {n.matchedDemand}".lower())]
    def refresh(self,state):
        rows=self._rows(state); self.count.setText(f"Notícias encontradas — {len(rows)} exibida(s)"); self.search24.setEnabled(not state.news_busy and self.controller.search_available); self.period_go.setEnabled(not state.news_busy and self.controller.search_available); self.stop.setVisible(state.news_busy)
        self.exec.set_state(state.news_busy,state.news_progress,state.status,len(state.new_news_links),state.last_news_duration_ms); self.table.setSortingEnabled(False); self.table.setRowCount(len(rows))
        for r,n in enumerate(rows):
            vals=[format_time(n.date),n.source,n.title,n.matchedTerm,n.matchedDemand];
            for c,v in enumerate(vals): self.table.setItem(r,c,QTableWidgetItem(v))
            actions=QWidget(); lay=QHBoxLayout(actions); lay.setContentsMargins(0,0,0,0)
            for text,fn in (("Abrir",lambda _,u=n.link:open_url(u)),("WhatsApp",lambda _,t=n.title,u=n.link:open_whatsapp(t,u)),("Copiar",lambda _,u=n.link:copy_text(u))): b=secondary(QPushButton(text)); b.clicked.connect(fn); lay.addWidget(b)
            self.table.setCellWidget(r,5,actions)
        self.table.setSortingEnabled(True); self.table.resizeColumnsToContents()


class VideosPage(BasePage):
    def __init__(self,controller):
        super().__init__(controller); top,tl=card(); row=QHBoxLayout(); self.query=QLineEdit(); self.query.setPlaceholderText("Buscar nos vídeos (título, fonte, termo...)"); row.addWidget(self.query,1); self.run=QPushButton("Buscar vídeos agora"); self.run.clicked.connect(controller.search_videos); row.addWidget(self.run); tl.addLayout(row)
        prow=QHBoxLayout();
        for label,h in (("24 horas",24),("7 dias",168),("30 dias",720)):
            b=secondary(QPushButton(label)); b.clicked.connect(lambda _=False,h=h: controller.search_videos(*controller.period_last_hours(h))); prow.addWidget(b)
        prow.addStretch(); tl.addLayout(prow); self.root.addWidget(top); self.exec=ExecutionPanel("Vídeos"); self.root.addWidget(self.exec); self.stop=secondary(QPushButton("Parar busca")); self.stop.clicked.connect(controller.stop_video_search); self.root.addWidget(self.stop)
        self.warning=QLabel(); self.warning.setWordWrap(True); self.warning.hide(); self.root.addWidget(self.warning); self.count=QLabel(); self.count.setObjectName("sectionTitle"); self.root.addWidget(self.count)
        self.table=QTableWidget(0,6); self.table.setHorizontalHeaderLabels(["Data","Fonte","Título","Termo","Demanda","Ações"]); self.table.setSortingEnabled(True); self.table.setAlternatingRowColors(True); self.root.addWidget(self.table,1); self.query.textChanged.connect(lambda _:self.refresh(controller.state))
    def refresh(self,state):
        q=self.query.text().strip().lower(); rows=[v for v in state.videos if not q or q in f"{v.title} {v.sourceName} {v.matchedTerm} {v.matchedDemand}".lower()]; self.count.setText(f"Vídeos encontrados — {len(rows)} exibido(s)"); self.run.setEnabled(not state.video_busy and self.controller.search_available); self.stop.setVisible(state.video_busy); self.exec.set_state(state.video_busy,state.video_progress,state.video_status,len(state.new_video_links),state.last_video_duration_ms)
        if state.unstable_video_sources: self.warning.setText("Fontes com instabilidade na última busca: "+" • ".join(str(getattr(x,"sourceName",x)) for x in state.unstable_video_sources)); self.warning.show()
        else: self.warning.hide()
        self.table.setSortingEnabled(False); self.table.setRowCount(len(rows))
        for r,v in enumerate(rows):
            for c,text in enumerate([format_time(v.publishedAt),v.sourceName,v.title,v.matchedTerm,v.matchedDemand]): self.table.setItem(r,c,QTableWidgetItem(text))
            actions=QWidget(); lay=QHBoxLayout(actions); lay.setContentsMargins(0,0,0,0)
            for text,fn in (("Abrir",lambda _,u=v.link:open_url(u)),("WhatsApp",lambda _,t=v.title,u=v.link:open_whatsapp(t,u)),("Copiar",lambda _,u=v.link:copy_text(u))): b=secondary(QPushButton(text)); b.clicked.connect(fn); lay.addWidget(b)
            self.table.setCellWidget(r,5,actions)
        self.table.setSortingEnabled(True); self.table.resizeColumnsToContents()


class DemandsPage(BasePage):
    def __init__(self,controller):
        super().__init__(controller); form,fl=card(); row=QHBoxLayout(); self.vehicle=QLineEdit(); self.vehicle.setPlaceholderText("Selecione ou digite o veículo..."); self.subject=QLineEdit(); self.subject.setPlaceholderText("Digite o assunto da demanda..."); self.add=QPushButton("Adicionar"); self.all=secondary(QPushButton("Buscar todas")); row.addWidget(self.vehicle); row.addWidget(self.subject,1); row.addWidget(self.add); row.addWidget(self.all); fl.addLayout(row); self.root.addWidget(form); self.status=QLabel(); self.root.addWidget(self.status); self.table=QTableWidget(0,6); self.table.setHorizontalHeaderLabels(["Veículo","Assunto","Última busca","Encontrados","Novos","Ações"]); self.root.addWidget(self.table,1)
        self.add.clicked.connect(self._add); self.all.clicked.connect(controller.search_all_demands); self.vehicle.textChanged.connect(self._valid); self.subject.textChanged.connect(self._valid); self._valid()
    def _valid(self): self.add.setEnabled(bool(self.vehicle.text().strip() and self.subject.text().strip()))
    def _add(self): self.controller.add_demand(self.vehicle.text(),self.subject.text()); self.vehicle.clear(); self.subject.clear()
    def refresh(self,state):
        self.status.setText(("Status: Buscando — " if state.news_busy else "Status: Pronto — ")+(state.status if state.news_busy else "Sistema disponível para consultar e gerenciar demandas.")); self.all.setEnabled(not state.news_busy and self.controller.search_available); self.table.setRowCount(len(state.demands))
        for r,d in enumerate(state.demands):
            for c,text in enumerate([d.vehicle,d.subject,format_time(d.lastCheckedAt),str(d.lastFoundCount),str(d.lastNewCount)]): self.table.setItem(r,c,QTableWidgetItem(text))
            actions=QWidget(); lay=QHBoxLayout(actions); lay.setContentsMargins(0,0,0,0); find=secondary(QPushButton("Buscar")); find.clicked.connect(lambda _,d=d:self.controller.search_demand(d)); delete=secondary(QPushButton("Excluir")); delete.clicked.connect(lambda _,i=d.id:self.controller.remove_demand(i)); lay.addWidget(find); lay.addWidget(delete); self.table.setCellWidget(r,5,actions)
        self.table.resizeColumnsToContents()


class TermsPage(BasePage):
    def __init__(self,controller):
        super().__init__(controller); row=QHBoxLayout(); self.root.addLayout(row); self.news_list=QListWidget(); self.video_list=QListWidget(); row.addWidget(self._term_card("Termos de Notícias","Usados na varredura de matérias",self.news_list,controller.add_term,controller.remove_term)); row.addWidget(self._term_card("Termos de Vídeos","Lista independente para vídeos",self.video_list,self._video_block,self._video_block))
        self.video_list.setToolTip("Persistência VideoTermStore permanece bloqueada (MIG-024).")
    def _video_block(self,*_): self.video_list.setToolTip("VideoTermStore ainda não possui persistência migrada; ação não executada.")
    def _term_card(self,title,sub,listw,add_cb,remove_cb):
        frame,lay=card(); lay.addWidget(heading(title,sub)); edit=QLineEdit(); edit.setPlaceholderText("Novo termo"); b=QPushButton("Adicionar"); rr=QHBoxLayout(); rr.addWidget(edit,1); rr.addWidget(b); lay.addLayout(rr); lay.addWidget(listw,1); delete=secondary(QPushButton("Excluir selecionado")); lay.addWidget(delete); b.clicked.connect(lambda: (add_cb(edit.text()),edit.clear())); delete.clicked.connect(lambda: remove_cb(listw.currentItem().text()) if listw.currentItem() else None); return frame
    def refresh(self,state):
        self.news_list.clear(); self.news_list.addItems(state.terms); self.video_list.clear(); self.video_list.addItem("VideoTermStore — MIG-024 BLOQUEADO")


class SourcesPage(BasePage):
    def __init__(self,controller):
        super().__init__(controller); top,tl=card(); self.tabs=QTabWidget(); self.news_tab=QWidget(); self.video_tab=QWidget(); self.special_tab=QWidget(); self.tabs.addTab(self.news_tab,"Notícias"); self.tabs.addTab(self.video_tab,"Vídeos"); self.tabs.addTab(self.special_tab,"Mídia especializada"); tl.addWidget(self.tabs); self.query=QLineEdit(); self.query.setPlaceholderText("Pesquisar fonte..."); tl.addWidget(self.query); self.all_news=QCheckBox("TODOS OS VEÍCULOS — SEM EXCEÇÃO"); self.all_news.toggled.connect(self._all_news_changed); tl.addWidget(self.all_news); self.root.addWidget(top)
        self.news_list=QListWidget(); self.video_list=QListWidget(); self.special_list=QListWidget(); self._put(self.news_tab,self.news_list); self._put(self.video_tab,self.video_list); self._put(self.special_tab,self.special_list); self.query.textChanged.connect(lambda _:self.refresh(controller.state)); self.news_list.itemChanged.connect(self._news_changed); self.video_list.itemChanged.connect(self._video_changed); self._guard=False
    def _put(self,parent,listw): lay=QVBoxLayout(parent); lay.addWidget(listw)
    def _all_news_changed(self,v): self.controller.news_all_sources=v; self.refresh(self.controller.state)
    def _matches(self,s,q): return not q or q in f"{s.name} {s.region} {s.state} {s.group} {' '.join(s.aliases)}".lower()
    def _fill(self,listw,sources,selected,enabled=True):
        listw.clear()
        for s in sources:
            item=QListWidgetItem(f"{s.name} — {s.group} • {s.region} • {s.state or 'BR'}"); item.setData(256,s.id); item.setFlags(item.flags() | item.flags().__class__.ItemIsUserCheckable); item.setCheckState(2 if (not enabled or s.id in selected) else 0); item.setFlags(item.flags() if enabled else item.flags() & ~item.flags().__class__.ItemIsEnabled); listw.addItem(item)
    def refresh(self,state):
        q=self.query.text().strip().lower(); self._guard=True; self.all_news.blockSignals(True); self.all_news.setChecked(self.controller.news_all_sources); self.all_news.blockSignals(False); self._fill(self.news_list,[s for s in self.controller.news_sources if self._matches(s,q)],self.controller.selected_news_source_ids,not self.controller.news_all_sources); self._fill(self.video_list,[s for s in self.controller.video_sources if self._matches(s,q)],self.controller.selected_video_source_ids,True); self._fill(self.special_list,[s for s in self.controller.specialized_sources if self._matches(s,q)],self.controller.selected_news_source_ids,not self.controller.news_all_sources); self._guard=False
    def _news_changed(self,item):
        if not self._guard:self.controller.set_news_source(str(item.data(256)),item.checkState()==2)
    def _video_changed(self,item):
        if not self._guard:self.controller.set_video_source(str(item.data(256)),item.checkState()==2)


class HistoryPage(BasePage):
    def __init__(self,controller):
        super().__init__(controller); self.tabs=QTabWidget(); self.news=QTableWidget(0,4); self.news.setHorizontalHeaderLabels(["Data","Fonte","Título","Termo/Demanda"]); self.video=QTableWidget(0,4); self.video.setHorizontalHeaderLabels(["Data","Fonte","Título","Termo/Demanda"]); self.tabs.addTab(self.news,"Notícias"); self.tabs.addTab(self.video,"Vídeos"); self.root.addWidget(self.tabs,1); self.clear=secondary(QPushButton("Limpar histórico")); self.clear.clicked.connect(self._clear); self.root.addWidget(self.clear)
    def _clear(self): self.controller.clear_news_history() if self.tabs.currentIndex()==0 else self.controller.clear_video_history()
    def refresh(self,state):
        news=self.controller.news_db.listNews(2000); videos=self.controller.video_db.listAll(2000); self.news.setRowCount(len(news)); self.video.setRowCount(len(videos))
        for r,n in enumerate(news):
            for c,t in enumerate([format_time(n.date),n.source,n.title," • ".join(x for x in [n.matchedTerm,n.matchedDemand] if x)]): self.news.setItem(r,c,QTableWidgetItem(t))
        for r,v in enumerate(videos):
            for c,t in enumerate([format_time(v.publishedAt),v.sourceName,v.title," • ".join(x for x in [v.matchedTerm,v.matchedDemand] if x)]): self.video.setItem(r,c,QTableWidgetItem(t))
        self.news.resizeColumnsToContents(); self.video.resizeColumnsToContents()


class StopPage(BasePage):
    def __init__(self,controller):
        super().__init__(controller); self.root.addWidget(heading("Controle de buscas em andamento","Interrompa uma busca manual sem fechar o aplicativo. A automação permanece configurada.")); self.news_status=QLabel(); self.video_status=QLabel(); self.news=QPushButton("Parar notícias/demandas"); self.video=QPushButton("Parar vídeos"); self.all=QPushButton("Parar tudo"); self.all.setProperty("danger",True); self.news.clicked.connect(controller.stop_news_search); self.video.clicked.connect(controller.stop_video_search); self.all.clicked.connect(controller.stop_all_searches)
        for title,label,button in (("Notícias e demandas",self.news_status,self.news),("Vídeos",self.video_status,self.video)):
            f,l=card(); l.addWidget(heading(title)); l.addWidget(label); l.addWidget(button); self.root.addWidget(f)
        self.root.addWidget(self.all); self.root.addStretch()
    def refresh(self,state): self.news_status.setText(state.status if state.news_busy else "Nenhuma busca em andamento"); self.video_status.setText(state.video_status if state.video_busy else "Nenhuma busca em andamento"); self.news.setEnabled(state.news_busy); self.video.setEnabled(state.video_busy); self.all.setEnabled(state.news_busy or state.video_busy)


class SettingsPage(BasePage):
    def __init__(self,controller):
        super().__init__(controller); self.proxy_frame,self.pl=card(); self.pl.addWidget(heading("Configuração de proxy")); self.proxy_enabled=QCheckBox("Ativado"); self.user=QLineEdit(); self.password=QLineEdit(); self.password.setEchoMode(QLineEdit.EchoMode.Password); self.host=QLineEdit(); self.port=QSpinBox(); self.port.setRange(1,65535); form=QFormLayout(); form.addRow("Servidor",self.host); form.addRow("Porta",self.port); form.addRow("Usuário",self.user); form.addRow("Senha",self.password); self.pl.addWidget(self.proxy_enabled); self.pl.addLayout(form); rr=QHBoxLayout(); self.save_proxy=QPushButton("Salvar e aplicar"); self.test_proxy=secondary(QPushButton("Testar conexão")); rr.addWidget(self.save_proxy); rr.addWidget(self.test_proxy); rr.addStretch(); self.pl.addLayout(rr); self.proxy_message=QLabel(); self.proxy_message.setWordWrap(True); self.pl.addWidget(self.proxy_message); self.root.addWidget(self.proxy_frame)
        self.save_proxy.clicked.connect(self._save_proxy); self.test_proxy.clicked.connect(self._test_proxy); self._proxy_thread=None
        auto,al=card(); al.addWidget(heading("Buscas automáticas","Notícias, Demandas e Vídeos funcionam de forma independente.")); self.general=QCheckBox("Controle geral"); self.startup=QCheckBox("Iniciar Monitor de Notícias com o Windows"); al.addWidget(self.general); al.addWidget(self.startup); self.news_auto=QCheckBox("Notícias — automático"); self.news_interval=QComboBox(); self.news_interval.addItems(["15","30","45","60","120"]); self.dem_auto=QCheckBox("Demandas — automático"); self.dem_interval=QComboBox(); self.dem_interval.addItems(["15","30","45","60","120"]); self.video_auto=QCheckBox("Vídeos — automático"); self.video_times=QLineEdit(); self.video_times.setPlaceholderText("08:00, 12:00, 15:00, 19:00, 21:00")
        af=QFormLayout(); af.addRow(self.news_auto,self.news_interval); af.addRow(self.dem_auto,self.dem_interval); af.addRow(self.video_auto,self.video_times); al.addLayout(af); self.apply_auto=QPushButton("Aplicar automação"); al.addWidget(self.apply_auto); self.root.addWidget(auto); self.root.addStretch(); self.apply_auto.clicked.connect(self._apply_auto); self.startup.toggled.connect(self._startup)
    def _save_proxy(self):
        cfg=self.controller.save_proxy(self.proxy_enabled.isChecked(),self.host.text(),self.port.value(),self.user.text(),self.password.text()); self.proxy_message.setText("Configuração salva e aplicada."); self.password.clear(); self.host.setText(cfg.host); self.port.setValue(cfg.port)
    def _test_proxy(self):
        self.test_proxy.setEnabled(False); self.proxy_message.setText("Testando conexão..."); self._proxy_thread=ProxyTestThread(self.controller); self._proxy_thread.completed.connect(self._proxy_done); self._proxy_thread.start()
    def _proxy_done(self,ok,text): self.proxy_message.setText(text); self.test_proxy.setEnabled(True); self._proxy_thread=None
    def _startup(self,checked):
        ok=self.controller.set_start_with_windows(checked)
        if checked and not ok: self.startup.setToolTip("Executável empacotado ainda não existe; preferência preservada para o portable final.")
    def _apply_auto(self):
        s=self.controller.automation_settings; s.automatic_monitoring=self.general.isChecked(); s.news_automatic=self.news_auto.isChecked(); s.demand_automatic=self.dem_auto.isChecked(); s.video_automatic=self.video_auto.isChecked(); s.news_interval_minutes=int(self.news_interval.currentText()); s.demand_interval_minutes=int(self.dem_interval.currentText()); s.video_schedule_times={x.strip() for x in self.video_times.text().split(',') if x.strip()}; self.controller.refresh()
    def refresh(self,state):
        cfg=self.controller.proxy_config; self.proxy_enabled.blockSignals(True); self.proxy_enabled.setChecked(cfg.enabled); self.proxy_enabled.blockSignals(False); self.host.setText(cfg.host); self.port.setValue(cfg.port); self.user.setText(cfg.username)
        # Kotlin carrega a senha no campo; no Python ela não é reposta após refresh para reduzir exposição. DEC registrada.
        s=self.controller.automation_settings; self.general.setChecked(s.automatic_monitoring); self.news_auto.setChecked(s.news_automatic); self.dem_auto.setChecked(s.demand_automatic); self.video_auto.setChecked(s.video_automatic); self.news_interval.setCurrentText(str(s.news_interval_minutes)); self.dem_interval.setCurrentText(str(s.demand_interval_minutes)); self.video_times.setText(", ".join(sorted(s.video_schedule_times))); self.startup.blockSignals(True); self.startup.setChecked(self.controller.start_with_windows); self.startup.blockSignals(False)


class PlaceholderPage(BasePage):
    def __init__(self,controller,title,body):
        super().__init__(controller); frame,layout=card(); layout.addWidget(heading(title)); text=QLabel(body); text.setWordWrap(True); text.setAlignment(text.alignment()); layout.addWidget(text); self.root.addWidget(frame); self.root.addStretch()
