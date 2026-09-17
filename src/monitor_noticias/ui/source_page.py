from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from monitor_noticias.ui.catalog import REGIONS, STATES
from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage, card, heading, secondary


class SourcesPage(BasePage):
    """Tela Fontes do Dashboard V5: tabs, busca, região/estado e seleção."""
    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller)
        filters, fl = card()
        top = QHBoxLayout()
        self.query = QLineEdit(); self.query.setPlaceholderText("Pesquisar fonte...")
        self.region = QComboBox(); self.region.addItems(REGIONS)
        self.state = QComboBox(); self.state.addItem("Todos")
        self._reload_states()
        top.addWidget(QLabel("Região")); top.addWidget(self.region)
        top.addWidget(QLabel("Estado")); top.addWidget(self.state)
        top.addWidget(self.query, 1); fl.addLayout(top)
        self.all_news = QCheckBox("TODOS OS VEÍCULOS — SEM EXCEÇÃO")
        self.all_news.setToolTip("Ligado: aceita qualquer veículo encontrado, inclusive fora do catálogo padrão.")
        fl.addWidget(self.all_news)
        actions = QHBoxLayout(); self.select_visible=QPushButton("Selecionar visíveis"); self.clear_visible=secondary(QPushButton("Limpar visíveis")); self.select_all=secondary(QPushButton("Todas")); self.clear_all=secondary(QPushButton("Nenhuma"))
        for b in (self.select_visible,self.clear_visible,self.select_all,self.clear_all): actions.addWidget(b)
        actions.addStretch(); fl.addLayout(actions); self.root.addWidget(filters)
        self.tabs=QTabWidget(); self.news_tab=QWidget(); self.video_tab=QWidget(); self.special_tab=QWidget()
        self.tabs.addTab(self.news_tab,"Notícias"); self.tabs.addTab(self.video_tab,"Vídeos"); self.tabs.addTab(self.special_tab,"Mídia especializada")
        self.news_list=QListWidget(); self.video_list=QListWidget(); self.special_list=QListWidget()
        self._put(self.news_tab,self.news_list); self._put(self.video_tab,self.video_list); self._put(self.special_tab,self.special_list); self.root.addWidget(self.tabs,1)
        self.info=QLabel(); self.info.setObjectName("muted"); self.info.setWordWrap(True); self.root.addWidget(self.info)
        self._guard=False
        self.query.textChanged.connect(lambda _:self.refresh(controller.state)); self.region.currentTextChanged.connect(self._region_changed); self.state.currentTextChanged.connect(lambda _:self.refresh(controller.state)); self.tabs.currentChanged.connect(lambda _:self.refresh(controller.state)); self.all_news.toggled.connect(self._all_news_changed)
        self.news_list.itemChanged.connect(self._news_changed); self.special_list.itemChanged.connect(self._news_changed); self.video_list.itemChanged.connect(self._video_changed)
        self.select_visible.clicked.connect(lambda:self._set_visible(True)); self.clear_visible.clicked.connect(lambda:self._set_visible(False)); self.select_all.clicked.connect(lambda:self._set_all(True)); self.clear_all.clicked.connect(lambda:self._set_all(False))

    def _put(self,parent,listw):
        lay=QVBoxLayout(parent); lay.setContentsMargins(8,8,8,8); lay.addWidget(listw)

    def _region_changed(self,_):
        self._reload_states(); self.refresh(self.controller.state)

    def _reload_states(self):
        current=self.state.currentText() if hasattr(self,"state") else "Todos"; region=self.region.currentText() if hasattr(self,"region") else "Todas"
        self.state.blockSignals(True); self.state.clear(); self.state.addItem("Todos")
        for code,name,reg in STATES:
            if region in {"Todas","Nacional"} or reg==region: self.state.addItem(code)
        idx=self.state.findText(current); self.state.setCurrentIndex(max(0,idx)); self.state.blockSignals(False)

    def _all_news_changed(self,value):
        self.controller.news_all_sources=value; self.refresh(self.controller.state)

    def _selected_sources(self):
        tab=self.tabs.currentIndex(); region=self.region.currentText(); state=self.state.currentText(); q=self.query.text().strip().lower()
        base = self.controller.news_sources if tab==0 else (self.controller.video_sources if tab==1 else self.controller.specialized_sources)
        result=[]
        for source in base:
            src_region=getattr(source,"region","Nacional") or "Nacional"; src_state=getattr(source,"state","") or "BR"
            if region!="Todas" and src_region!=region: continue
            if state!="Todos" and src_state!=state: continue
            hay=f"{source.name} {src_region} {src_state} {source.group} {' '.join(source.aliases)}".lower()
            if q and q not in hay: continue
            result.append(source)
        return result

    def _fill(self,listw,sources,selected,enabled=True):
        listw.blockSignals(True); listw.clear()
        for source in sources:
            item=QListWidgetItem(f"{source.name} — {source.group} • {getattr(source,'region','Nacional')} • {getattr(source,'state','') or 'BR'}")
            item.setData(Qt.ItemDataRole.UserRole,source.id); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if (not enabled or source.id in selected) else Qt.CheckState.Unchecked)
            if not enabled: item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            listw.addItem(item)
        listw.blockSignals(False)

    def refresh(self,state:UiState):
        self._guard=True; self.all_news.blockSignals(True); self.all_news.setChecked(self.controller.news_all_sources); self.all_news.blockSignals(False)
        tab=self.tabs.currentIndex(); visible=self._selected_sources()
        if tab==0:
            self._fill(self.news_list,visible,self.controller.selected_news_source_ids,not self.controller.news_all_sources)
            self.info.setText(f"{len(visible)} fonte(s) visível(is)" + (" • seletor ignorado" if self.controller.news_all_sources else ""))
        elif tab==1:
            self._fill(self.video_list,visible,self.controller.selected_video_source_ids,True); self.info.setText(f"{len(visible)} fonte(s) de vídeo visível(is). Fontes Desktop incluem g1 e Domingo Espetacular.")
        else:
            self._fill(self.special_list,visible,self.controller.selected_news_source_ids,not self.controller.news_all_sources); self.info.setText(f"Mídia especializada: {len(visible)} veículo(s) focado(s) em Defesa, Forças Armadas e assuntos navais.")
        self._guard=False

    def _news_changed(self,item):
        if not self._guard:self.controller.set_news_source(str(item.data(Qt.ItemDataRole.UserRole)),item.checkState()==Qt.CheckState.Checked)
    def _video_changed(self,item):
        if not self._guard:self.controller.set_video_source(str(item.data(Qt.ItemDataRole.UserRole)),item.checkState()==Qt.CheckState.Checked)

    def _set_visible(self,checked:bool):
        tab=self.tabs.currentIndex()
        for source in self._selected_sources():
            if tab==1:self.controller.set_video_source(source.id,checked)
            else:self.controller.set_news_source(source.id,checked)
        self.refresh(self.controller.state)

    def _set_all(self,checked:bool):
        tab=self.tabs.currentIndex(); base=self.controller.video_sources if tab==1 else (self.controller.specialized_sources if tab==2 else self.controller.news_sources)
        if tab==1:self.controller.selected_video_source_ids={s.id for s in base} if checked else set()
        else:
            if tab==0 and checked:self.controller.news_all_sources=True
            elif tab==0 and not checked:self.controller.news_all_sources=False; self.controller.selected_news_source_ids=set()
            else:
                ids=self.controller.selected_news_source_ids; spec={s.id for s in base}; ids=(ids|spec) if checked else (ids-spec); self.controller.selected_news_source_ids=ids
        self.refresh(self.controller.state)
