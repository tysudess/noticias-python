from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QListWidget, QPushButton
from monitor_noticias.ui.pages import BasePage, card, heading, secondary

class TermsPage(BasePage):
    """Termos de notícias e de vídeos ligados às persistências reais em produção."""
    def __init__(self,controller):
        super().__init__(controller)
        row=QHBoxLayout(); self.root.addLayout(row)
        self.news_list=QListWidget(); self.video_list=QListWidget()
        row.addWidget(self._term_card("Termos de Notícias","Usados na varredura de matérias",self.news_list,controller.add_term,controller.remove_term))
        add_video=getattr(controller,"add_video_term",lambda _value:None)
        remove_video=getattr(controller,"remove_video_term",lambda _value:None)
        row.addWidget(self._term_card("Termos de Vídeos","Lista independente para vídeos",self.video_list,add_video,remove_video))
    def _term_card(self,title,sub,listw,add_cb,remove_cb):
        frame,lay=card(); lay.addWidget(heading(title,sub)); edit=QLineEdit(); edit.setPlaceholderText("Novo termo"); button=QPushButton("Adicionar")
        line=QHBoxLayout(); line.addWidget(edit,1); line.addWidget(button); lay.addLayout(line); lay.addWidget(listw,1)
        delete=secondary(QPushButton("Excluir selecionado")); lay.addWidget(delete)
        button.clicked.connect(lambda: (add_cb(edit.text()),edit.clear()))
        delete.clicked.connect(lambda: remove_cb(listw.currentItem().text()) if listw.currentItem() else None)
        return frame
    def refresh(self,state):
        self.news_list.clear(); self.news_list.addItems(state.terms)
        self.video_list.clear(); self.video_list.addItems(getattr(self.controller,"video_terms",[]))
