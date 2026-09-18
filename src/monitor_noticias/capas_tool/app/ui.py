from __future__ import annotations
import os, shutil
from datetime import date, datetime
from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt, QSize, QThreadPool, Signal, QObject, QUrl
from PySide6.QtGui import QIcon, QPixmap, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QCheckBox,
    QListWidget,QListWidgetItem,QStackedWidget,QDateEdit,QFrame,QScrollArea,QFileDialog,
    QMessageBox,QProgressBar,QDialog,QDialogButtonBox,QLineEdit,QGroupBox,QSizePolicy
)
from .config import bundle_dir, cache_dir, downloads_dir, GMAIL_PAPERS, WEB_PAPERS, load_settings, save_settings
from .models import CandidatePage
from .network import fetch_matters, download_image, safe_slug
from .newspapers import load_entries
from .ocr import score_candidate, normalize
from .pdf_export import export_pdf, build_filename
from .workers import Worker
from .web_resolver import Resolver, CentralClippingBatchResolver, ParallelCentralClippingResolver, AppsScriptFeedResolver, ANDROID_FRONT_UA
from .valor_email_pdf import load_valor_candidates

STYLE = """
QMainWindow,QWidget{background:#071625;color:#eaf3ff;font-family:'Segoe UI';font-size:13px}
QFrame#header{background:#0b2948;border:1px solid #284867;border-radius:14px}
QFrame#card{background:#0b1f33;border:1px solid #29445f;border-radius:12px}
QLabel#title{font-size:24px;font-weight:700;color:white}
QLabel#sub{color:#8fa9c3}
QLabel#green{color:#53e879}
QPushButton{background:#0d2943;border:1px solid #315675;border-radius:9px;padding:9px 14px;color:#eaf3ff;font-weight:600}
QPushButton:hover{background:#123858}
QPushButton#primary{background:#176fc1;border-color:#2d8cff}
QPushButton#greenBtn{background:#1d8f50;border-color:#39b76d}
QPushButton#danger{background:#48202a;border-color:#733443}
QCheckBox{spacing:8px}
QListWidget{background:#081827;border:1px solid #203b56;border-radius:11px;padding:4px;outline:none}
QListWidget::item{padding:9px;border-radius:8px;margin:2px}
QListWidget::item:selected{background:#0d3152;border:1px solid #2d8cff}
QDateEdit,QLineEdit{background:#0c2034;border:1px solid #315675;border-radius:8px;padding:8px;color:white}
QProgressBar{border:0;background:#0c2034;border-radius:3px;height:6px} QProgressBar::chunk{background:#2d8cff;border-radius:3px}
QGroupBox{border:1px solid #29445f;border-radius:10px;margin-top:12px;padding-top:12px;font-weight:600}
QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 6px;color:#b9cbe0}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Principais Capas — Windows Portable")
        self.setWindowIcon(QIcon(str(bundle_dir()/"assets"/"app_icon.ico")))
        self.resize(1320,820); self.setMinimumSize(1050,680)
        self.setStyleSheet(STYLE)
        self.entries=load_entries(); self.settings=load_settings(); self.threadpool=QThreadPool.globalInstance()
        # v1.0.1: os ramos Gmail e Web usam resolvers independentes, igual ao Android.
        # Isso evita que timeout de Post/Valor bloqueie O Globo/Folha/Estadão/etc.
        self.gmail_resolver=None
        self.gmail_feed_resolver=None
        self.gmail_batch_resolver=None
        self.web_resolvers=[]
        self.gmail_queue=[]
        self.gmail_sent_counts={}
        self.gmail_matter_urls={}
        self.refresh_generation=0
        self.pending_branches=0
        self.active_workers=[]
        self.last_pdf=None; self.current_entry=None
        self._build(); self._refresh_list(); self._select_row(0)

    def _build(self):
        central=QWidget(); self.setCentralWidget(central); root=QVBoxLayout(central); root.setContentsMargins(12,12,12,12); root.setSpacing(8)
        header=QFrame(); header.setObjectName("header"); hl=QHBoxLayout(header); hl.setContentsMargins(14,10,14,10)
        icon=QLabel(); icon.setPixmap(QPixmap(str(bundle_dir()/"assets"/"app_icon.png")).scaled(54,54,Qt.KeepAspectRatio,Qt.SmoothTransformation)); hl.addWidget(icon)
        tt=QVBoxLayout(); title=QLabel("PRINCIPAIS CAPAS"); title.setObjectName("title"); tt.addWidget(title); sub=QLabel("Windows Portable • busca automática • revisão manual • PDF otimizado"); sub.setObjectName("sub"); tt.addWidget(sub); hl.addLayout(tt,1)
        self.date_edit=QDateEdit(); self.date_edit.setCalendarPopup(True); self.date_edit.setDate(datetime.now().date()); self.date_edit.setDisplayFormat("dd/MM/yyyy"); hl.addWidget(QLabel("Data:")); hl.addWidget(self.date_edit)
        cfg=QPushButton("⚙ Apps Script"); cfg.clicked.connect(self.configure_script); hl.addWidget(cfg)
        root.addWidget(header)

        actions=QHBoxLayout();
        self.refresh_btn=QPushButton("↻  ATUALIZAR CAPAS"); self.refresh_btn.setObjectName("primary"); self.refresh_btn.clicked.connect(self.refresh_all); actions.addWidget(self.refresh_btn)
        self.pdf_btn=QPushButton("▣  GERAR PDF"); self.pdf_btn.setObjectName("greenBtn"); self.pdf_btn.clicked.connect(self.generate_pdf); actions.addWidget(self.pdf_btn)
        self.open_btn=QPushButton("▤  ABRIR PDF GERADO"); self.open_btn.clicked.connect(self.open_pdf); actions.addWidget(self.open_btn)
        allb=QPushButton("✓ Marcar todas"); allb.clicked.connect(lambda:self.set_all(True)); actions.addWidget(allb)
        noneb=QPushButton("× Desmarcar"); noneb.clicked.connect(lambda:self.set_all(False)); actions.addWidget(noneb)
        root.addLayout(actions)
        self.progress=QProgressBar(); self.progress.setRange(0,0); self.progress.hide(); root.addWidget(self.progress)

        content=QHBoxLayout(); content.setSpacing(10); root.addLayout(content,1)
        left=QFrame(); left.setObjectName("card"); ll=QVBoxLayout(left); ll.addWidget(QLabel("JORNAIS (8)"))
        self.list=QListWidget(); self.list.currentRowChanged.connect(self._select_row); ll.addWidget(self.list,1); content.addWidget(left,38)
        right=QFrame(); right.setObjectName("card"); rl=QVBoxLayout(right); self.paper_title=QLabel("Selecione um jornal"); self.paper_title.setObjectName("title"); rl.addWidget(self.paper_title)
        self.paper_status=QLabel(""); self.paper_status.setObjectName("green"); self.paper_status.setWordWrap(True); rl.addWidget(self.paper_status)
        self.preview=QLabel("Aguardando capa"); self.preview.setAlignment(Qt.AlignCenter); self.preview.setMinimumHeight(360); self.preview.setStyleSheet("background:#061321;border:1px solid #29445f;border-radius:10px;color:#8fa9c3"); rl.addWidget(self.preview,1)
        candbox=QGroupBox("Páginas recebidas / candidatas"); cl=QHBoxLayout(candbox); self.prev_btn=QPushButton("◀ Anterior"); self.prev_btn.clicked.connect(lambda:self.move_candidate(-1)); cl.addWidget(self.prev_btn); self.cand_label=QLabel("0 de 0"); self.cand_label.setAlignment(Qt.AlignCenter); cl.addWidget(self.cand_label,1); self.next_btn=QPushButton("Próxima ▶"); self.next_btn.clicked.connect(lambda:self.move_candidate(1)); cl.addWidget(self.next_btn); rl.addWidget(candbox)
        ba=QHBoxLayout(); self.review_btn=QPushButton("USAR ESTA PÁGINA"); self.review_btn.setObjectName("primary"); self.review_btn.clicked.connect(self.use_current_candidate); ba.addWidget(self.review_btn); manual=QPushButton("INSERIR CAPA MANUALMENTE"); manual.clicked.connect(self.manual_cover); ba.addWidget(manual); restore=QPushButton("VOLTAR PARA AUTOMÁTICA"); restore.clicked.connect(self.restore_auto); ba.addWidget(restore); rl.addLayout(ba)
        content.addWidget(right,62)
        self.statusBar().showMessage("Pronto")

    def target_date(self):
        q=self.date_edit.date(); return date(q.year(),q.month(),q.day())

    def set_status(self,msg): self.statusBar().showMessage(msg)
    def set_busy(self,b):
        self.progress.setVisible(b); self.refresh_btn.setEnabled(not b); self.pdf_btn.setEnabled(not b)

    def _start_worker(self, worker):
        """Mantém referência do QRunnable até o sinal final.

        Evita que o wrapper Python/Signals seja coletado antes do callback em
        builds PyInstaller, algo que pode deixar a UI presa em 'Localizando…'.
        """
        self.active_workers.append(worker)
        def release(*_):
            try:
                self.active_workers.remove(worker)
            except ValueError:
                pass
        worker.signals.finished.connect(release)
        worker.signals.error.connect(release)
        self.threadpool.start(worker)

    def _refresh_list(self):
        row=self.list.currentRow(); self.list.clear()
        for e in self.entries:
            item=QListWidgetItem(); item.setData(Qt.UserRole,e.name); self.list.addItem(item)
            w=QWidget(); l=QHBoxLayout(w); l.setContentsMargins(6,4,6,4)
            cb=QCheckBox(); cb.setChecked(e.selected); cb.toggled.connect(lambda v,en=e:self._toggle(en,v)); l.addWidget(cb)
            num=QLabel(str(self.entries.index(e)+1)); num.setFixedWidth(28); num.setStyleSheet("font-size:16px;font-weight:700;color:#8fb9e6"); l.addWidget(num)
            tx=QVBoxLayout(); nm=QLabel(e.name); nm.setStyleSheet("font-size:15px;font-weight:700;color:white"); tx.addWidget(nm); st=QLabel(e.status); st.setObjectName("sub"); st.setWordWrap(True); tx.addWidget(st); l.addLayout(tx,1)
            if e.current_path:
                pm=QPixmap(str(e.current_path)).scaled(48,68,Qt.KeepAspectRatio,Qt.SmoothTransformation); thumb=QLabel(); thumb.setPixmap(pm); l.addWidget(thumb)
            item.setSizeHint(QSize(300,78)); self.list.setItemWidget(item,w)
        if self.entries:
            self.list.setCurrentRow(max(0,min(row if row>=0 else 0,len(self.entries)-1)))

    def _toggle(self,e,v): e.selected=v
    def set_all(self,v):
        for e in self.entries:e.selected=v
        self._refresh_list()

    def _select_row(self,row):
        if not (0<=row<len(self.entries)):return
        self.current_entry=self.entries[row]; self._show_entry()

    def _show_entry(self):
        e=self.current_entry
        if not e:return
        self.paper_title.setText(e.name); self.paper_status.setText(e.status)
        n=len(e.candidates)
        if n:
            if not (0 <= e.review_index < n):
                e.review_index = e.chosen_index if 0 <= e.chosen_index < n else 0
            idx=e.review_index
        else:
            idx=0

        # A revisão mostra a candidata navegada; o PDF continua usando apenas
        # chosen_index (ou a capa manual) até o usuário confirmar "USAR ESTA PÁGINA".
        display_path=None
        current_candidate=None
        if e.is_manual:
            display_path=e.manual_path
        elif n and 0 <= idx < n:
            current_candidate=e.candidates[idx]
            if current_candidate.available and current_candidate.path and current_candidate.path.exists():
                display_path=current_candidate.path

        if display_path and display_path.exists():
            self.preview.setPixmap(QPixmap(str(display_path)).scaled(self.preview.size()-QSize(18,18),Qt.KeepAspectRatio,Qt.SmoothTransformation)); self.preview.setText("")
        else:
            self.preview.setPixmap(QPixmap())
            if current_candidate and not current_candidate.available:
                self.preview.setText(
                    f"Candidata {current_candidate.page_number} de {n} recebida do Gmail\n\n"
                    "A imagem original não abriu nesta tentativa.\n"
                    "A posição foi preservada para a revisão."
                )
            else:
                self.preview.setText("Aguardando capa")

        self.cand_label.setText(f"{idx+1 if n else 0} de {n}" + (" • MANUAL" if e.is_manual else ""))
        self.prev_btn.setEnabled(n>1); self.next_btn.setEnabled(n>1)
        if hasattr(self, "review_btn"):
            self.review_btn.setEnabled(bool(current_candidate and current_candidate.available) and not e.is_manual)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.current_entry:self._show_entry()

    def move_candidate(self,step):
        e=self.current_entry; n=len(e.candidates) if e else 0
        if n<1:return
        idx=e.review_index if 0<=e.review_index<n else (e.chosen_index if 0<=e.chosen_index<n else 0)
        idx=(idx+step)%n; e.review_index=idx
        c=e.candidates[idx]
        if c.available:
            e.status=f"Revisando candidata {c.page_number}/{n} • confiança {c.confidence}%"
        else:
            e.status=f"Revisando candidata {c.page_number}/{n} • recebida, mas imagem não aberta"
        self._show_entry(); self._refresh_list()

    def use_current_candidate(self):
        e=self.current_entry
        if not e or not e.candidates:return
        idx=e.review_index if 0<=e.review_index<len(e.candidates) else 0
        c=e.candidates[idx]
        if not c.available or not c.path or not c.path.exists():
            QMessageBox.warning(self,"Candidata indisponível","Essa página foi recebida pelo Gmail, mas a imagem original não abriu. Escolha outra candidata disponível.")
            return
        e.choose(idx); e.status=f"Candidata {c.page_number}/{len(e.candidates)} escolhida • confiança {c.confidence}%"; self._show_entry(); self._refresh_list()

    def manual_cover(self):
        e=self.current_entry
        if not e:return
        fn,_=QFileDialog.getOpenFileName(self,"Inserir capa manualmente","","Imagens (*.jpg *.jpeg *.png *.webp *.bmp)")
        if not fn:return
        e.set_manual(Path(fn)); self._show_entry(); self._refresh_list()

    def restore_auto(self):
        e=self.current_entry
        if not e:return
        e.restore_automatic(); self._show_entry(); self._refresh_list()

    def configure_script(self):
        dlg=QDialog(self); dlg.setWindowTitle("Apps Script"); lay=QVBoxLayout(dlg); lay.addWidget(QLabel("URL /exec do Apps Script:")); edit=QLineEdit(self.settings.get("apps_script_url","")); lay.addWidget(edit); bb=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); lay.addWidget(bb); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        if dlg.exec(): self.settings["apps_script_url"]=edit.text().strip(); save_settings(self.settings); QMessageBox.information(self,"Apps Script","URL salva.")

    def refresh_all(self):
        """Mesmo desenho de execução do Android v0.7.5.9.

        Ramo 1: Gmail/Apps Script -> todos os Leia mais consolidados -> Ver página -> original_page.
        Ramo 2: Valor/Post em paralelo, sem esperar o Gmail.
        """
        self.refresh_generation += 1
        generation = self.refresh_generation
        self.set_busy(True)
        self.set_status("Atualizando capas…")
        self.gmail_queue = []
        self.gmail_sent_counts = {}
        self.gmail_matter_urls = {}
        self.web_resolvers = []
        self.gmail_resolver = None
        self.gmail_feed_resolver = None
        self.gmail_batch_resolver = None
        self.pending_branches = 2

        for e in self.entries:
            e.status = "Aguardando"
            e.candidates = []
            e.chosen_index = -1
            e.automatic_index = -1
            e.automatic_status = ""
            e.review_index = -1
            e.manual_path = None
        self._refresh_list()

        # Igual ao Android: os dois ramos iniciam imediatamente.
        self._start_web_branch(generation)
        self._start_gmail_branch(generation)

    def _branch_done(self, generation):
        if generation != self.refresh_generation:
            return
        self.pending_branches -= 1
        if self.pending_branches <= 0:
            self._finalize_refresh(generation)

    # ---------------- Gmail / Apps Script ----------------
    def _start_gmail_branch(self, generation):
        if generation != self.refresh_generation:
            return
        url = self.settings.get("apps_script_url", "").strip()
        if not url:
            for e in self.entries:
                if e.name in GMAIL_PAPERS:
                    e.status = "Gmail automático não configurado • sem usar internet"
            self._refresh_list()
            self._branch_done(generation)
            return

        for e in self.entries:
            if e.name in GMAIL_PAPERS:
                e.status = "Localizando páginas no Gmail…"
        self._refresh_list()

        # v1.2.6: primeiro usa a pilha de rede Windows nativa/requests robusta.
        # Se ainda assim falhar, cai automaticamente para o Chromium interno.
        w = Worker(fetch_matters, url, self.target_date())
        w.signals.finished.connect(lambda result, g=generation: self._feed_ready(result, g))
        w.signals.error.connect(lambda msg, u=url, g=generation: self._feed_direct_error(msg, u, g))
        self._start_worker(w)

    def _feed_direct_error(self, msg, url, generation):
        if generation != self.refresh_generation:
            return
        for e in self.entries:
            if e.name in GMAIL_PAPERS:
                e.status = "Conexão direta falhou • tentando navegador do Windows…"
        self._refresh_list()
        self.set_status("Gmail: tentando navegador interno após falha da conexão direta")
        self.gmail_feed_resolver = AppsScriptFeedResolver(self)
        self.gmail_feed_resolver.progress.connect(self.set_status)
        self.gmail_feed_resolver.completed.connect(
            lambda matters, meta, g=generation: self._feed_ready((matters, meta), g)
        )
        self.gmail_feed_resolver.failed.connect(
            lambda browser_msg, direct_msg=str(msg), g=generation: self._feed_error(
                f"direto: {direct_msg} | navegador: {browser_msg}", g
            )
        )
        self.gmail_feed_resolver.fetch(
            url, self.settings.get("access_key", "PC26-8F2D4A7B-31C9E6F0-5A1D"), self.target_date()
        )

    def _feed_error(self, msg, generation):
        if generation != self.refresh_generation:
            return
        for e in self.entries:
            if e.name in GMAIL_PAPERS:
                e.status = f"Gmail: {msg} • sem usar internet"
        self._refresh_list()
        self.set_status("Gmail: " + msg)
        self._branch_done(generation)

    def _feed_ready(self, result, generation):
        if generation != self.refresh_generation:
            return
        matters, meta = result
        self.gmail_sent_counts = {}

        bridge_version = str((meta or {}).get("version") or "").strip()
        if bridge_version and not (bridge_version.startswith("0.7.5") or bridge_version.startswith("0.7.6") or bridge_version.startswith("0.7.7")):
            self.set_status(f"Ponte Gmail v{bridge_version}: recomendado Apps Script 0.7.7.1")

        filtered = {}
        for e in self.entries:
            if e.name not in GMAIL_PAPERS:
                continue
            urls = list(matters.get(e.name, []) or [])
            self.gmail_sent_counts[e.name] = len(urls)
            self.gmail_matter_urls[e.name] = list(urls)
            if urls:
                filtered[e.name] = urls
                e.status = f"Gmail enviou {len(urls)} página(s) • abrindo Ver página…"
            else:
                e.status = "Não veio no Gmail • sem usar internet"

        self._refresh_list()
        if not filtered:
            self._branch_done(generation)
            return

        # v1.0.2: porta o CentralClippingWebResolver do Android como um lote único.
        # Cada link usa uma QWebEngineView NOVA, realmente anexada à janela (fora da tela),
        # reproduzindo o detalhe que faltava na v1.0.1.
        self.gmail_batch_resolver = ParallelCentralClippingResolver(self)
        self.gmail_batch_resolver.progress.connect(self.set_status)
        self.gmail_batch_resolver.completed.connect(
            lambda covers, errors, g=generation: self._gmail_originals_ready(covers, errors, g)
        )
        self.gmail_batch_resolver.resolve(filtered)

    def _gmail_originals_ready(self, covers, errors, generation):
        if generation != self.refresh_generation:
            return

        # IMPORTANTE v1.1.2: a revisão preserva TODAS as posições recebidas
        # do Apps Script, sem limite artificial, mesmo se uma delas não conseguir abrir o
        # original_page. O ranking automático só considera as candidatas disponíveis.
        pending = {"n": 0}

        def done_one():
            if generation != self.refresh_generation:
                return
            pending["n"] -= 1
            if pending["n"] <= 0:
                self._finish_gmail_branch(generation)

        for e in self.entries:
            if e.name not in GMAIL_PAPERS:
                continue
            sent = self.gmail_sent_counts.get(e.name, 0)
            slots = list((covers or {}).get(e.name, []) or [])
            # Garante exatamente 'sent' posições, inclusive as que não resolveram.
            by_num = {int(x.get("page_number", i+1)): x for i, x in enumerate(slots) if isinstance(x, dict)}
            e.candidates = []
            for page_number in range(1, sent + 1):
                item = by_num.get(page_number, {"page_number": page_number, "url": "", "error": "Ver página não resolvida"})
                url = str(item.get("url") or "").strip()
                if not url:
                    e.candidates.append(CandidatePage(
                        path=None, score=-9999, confidence=0, recognized_text="",
                        source_url=(self.gmail_matter_urls.get(e.name, [""]*sent)[page_number-1] if page_number-1 < len(self.gmail_matter_urls.get(e.name, [])) else ""),
                        page_number=page_number, available=False, error=str(item.get("error") or "Imagem original não aberta")
                    ))
                    continue

                # Reserva o slot agora; o worker substitui este placeholder ao concluir.
                e.candidates.append(CandidatePage(
                    path=None, score=-9999, confidence=0, recognized_text="", source_url=url,
                    page_number=page_number, available=False, error="Baixando imagem original…"
                ))
                ext = ".webp" if ".webp" in url.lower() else ".jpg"
                dest = cache_dir() / self.target_date().isoformat() / f"{safe_slug(e.name)}-{page_number}{ext}"
                w = Worker(self._download_and_score, url, dest, "", e.name, e.mastheads, page_number)
                pending["n"] += 1
                w.signals.finished.connect(
                    lambda c, en=e, g=generation, d=done_one: self._gmail_candidate_batch_ready(en, c, g, d)
                )
                w.signals.error.connect(
                    lambda m, en=e, pn=page_number, g=generation, d=done_one: self._gmail_candidate_batch_error(en, pn, m, g, d)
                )
                self._start_worker(w)

            if sent:
                opened=sum(1 for c in e.candidates if c.available)
                e.status=f"Gmail {sent} recebida(s) • preparando {sent} candidata(s)"

        self._refresh_list()
        if pending["n"] <= 0:
            self._finish_gmail_branch(generation)

    def _gmail_candidate_batch_ready(self, e, candidate, generation, done_one):
        if generation != self.refresh_generation:
            return
        # Substitui o slot correspondente, preservando ordem recebida.
        idx=max(0, candidate.page_number-1)
        if idx < len(e.candidates):
            candidate.available=True
            candidate.error=""
            e.candidates[idx]=candidate
        else:
            candidate.available=True
            e.candidates.append(candidate)
        sent = self.gmail_sent_counts.get(e.name, 0)
        opened=sum(1 for c in e.candidates if c.available)
        e.status = f"Gmail {sent} recebida(s) • {opened}/{sent} imagem(ns) aberta(s) • revisão mostra {sent}/{sent}"
        self._refresh_list()
        if self.current_entry is e:
            self._show_entry()
        done_one()

    def _gmail_candidate_batch_error(self, e, page_number, msg, generation, done_one):
        if generation != self.refresh_generation:
            return
        idx=max(0,page_number-1)
        if idx < len(e.candidates):
            e.candidates[idx].available=False
            e.candidates[idx].error=str(msg)
        sent=self.gmail_sent_counts.get(e.name,0)
        opened=sum(1 for c in e.candidates if c.available)
        e.status=f"Gmail {sent} recebida(s) • {opened}/{sent} imagem(ns) aberta(s) • revisão mostra {sent}/{sent}"
        self._refresh_list()
        if self.current_entry is e:self._show_entry()
        done_one()

    def _finish_gmail_branch(self, generation):
        if generation != self.refresh_generation:
            return
        for e in self.entries:
            if e.name not in GMAIL_PAPERS:
                continue
            sent = self.gmail_sent_counts.get(e.name, 0)
            available_indexes=[i for i,c in enumerate(e.candidates) if c.available and c.path and c.path.exists()]
            if available_indexes:
                best_index = max(
                    available_indexes,
                    key=lambda i: (e.candidates[i].score, -e.candidates[i].page_number),
                )
                e.chosen_index = best_index
                e.review_index = best_index
                e.automatic_index = best_index
                best = e.candidates[best_index]
                opened=len(available_indexes)
                e.automatic_status = (
                    f"Gmail • candidata {best.page_number}/{max(1, sent)} escolhida • "
                    f"confiança {best.confidence}% • revisão {sent}/{sent} recebida(s) • {opened} imagem(ns) aberta(s)"
                )
                e.status = e.automatic_status
            elif sent > 0:
                e.status = (
                    f"Gmail enviou {sent} página(s), mas nenhuma imagem original foi aberta • "
                    "sem usar internet"
                )
        self._refresh_list()
        self._show_entry()
        self._branch_done(generation)

    # ---------------- Valor / Washington Post ----------------
    def _start_web_branch(self, generation):
        if generation != self.refresh_generation: return
        web_entries=[]
        for e in self.entries:
            if e.name == "VALOR ECONÔMICO":
                if self.target_date().weekday() >= 5: e.status="Sem edição regular no fim de semana"
                else: e.status="Valor: procurando 3 PDFs no Gmail…"; web_entries.append(e)
            elif e.name == "THE WASHINGTON POST":
                e.status="Buscando a capa exibida atualmente no link…"; web_entries.append(e)
        self._refresh_list()
        if not web_entries: self._branch_done(generation); return
        pending={"n":len(web_entries)}
        def one_done():
            if generation != self.refresh_generation: return
            pending["n"]-=1
            if pending["n"] <= 0: self._branch_done(generation)
        for e in web_entries:
            if e.name == "VALOR ECONÔMICO":
                w=Worker(load_valor_candidates,self.settings.get("apps_script_url",""),self.target_date())
                w.signals.finished.connect(lambda cand,en=e,g=generation,d=one_done:self._valor_email_ready(en,cand,g,d))
                w.signals.error.connect(lambda msg,en=e,g=generation,d=one_done:self._valor_email_error(en,msg,g,d))
                self._start_worker(w)
            else: self._start_single_web_resolver(e,generation,one_done)

    def _valor_email_ready(self,e,candidates,generation,one_done):
        if generation != self.refresh_generation: return
        candidates=list(candidates or [])
        indexes=[i for i,c in enumerate(candidates) if c.page_number==1 and c.available and c.path and c.path.exists()]
        if indexes:
            e.candidates=candidates; idx=indexes[0]
            e.chosen_index=idx; e.review_index=idx; e.automatic_index=idx
            available=sum(1 for c in candidates if c.available and c.path and c.path.exists()); total=len(candidates)
            e.automatic_status=(f"Gmail • {available}/{total} PDF(s) do Valor no aplicativo • {total} página(s) em REVISAR CAPA • "
                                "Página 1 selecionada • cópia em Downloads/Principais Capas/Valor Economico")
            e.status=e.automatic_status; self._refresh_list()
            if self.current_entry is e: self._show_entry()
            one_done(); return
        e.status="Valor: Página 1 não veio do Gmail • usando fallback web v1.2.2…"; self._refresh_list()
        self._start_single_web_resolver(e,generation,one_done)

    def _valor_email_error(self,e,msg,generation,one_done):
        if generation != self.refresh_generation: return
        e.status=f"Valor: Gmail indisponível ({msg}) • usando fallback web v1.2.2…"; self._refresh_list()
        self._start_single_web_resolver(e,generation,one_done)

    def _start_single_web_resolver(self,e,generation,one_done,pressreader_only=False):
        resolver=Resolver(self); resolver.progress.connect(self.set_status); self.web_resolvers.append(resolver)
        cb=lambda url,err,en=e,r=resolver,g=generation:self._web_resolved(en,r,url,err,g,one_done)
        if pressreader_only: resolver.resolve_pressreader_only(cb)
        else: resolver.resolve_frontpages(e.name,cb)

    def _web_resolved(self, e, resolver, url, err, generation, one_done):
        if generation != self.refresh_generation:
            return
        if not url:
            e.status = f"Falha: Capa correta não confirmada para {e.name} ({err})"
            self._refresh_list()
            one_done()
            return

        ext = ".webp" if ".webp" in url.lower() else ".jpg"
        dest = cache_dir() / self.target_date().isoformat() / f"{safe_slug(e.name)}-web{ext}"
        referer = resolver.last_referer or (
            "https://www.frontpages.com/the-washington-post/"
            if e.name == "THE WASHINGTON POST"
            else "https://valoreconomico.pressreader.com/valor-economico"
        )
        cookie_header = getattr(resolver, "last_cookie_header", "") or ""
        w = Worker(self._download_and_score, url, dest, referer, e.name, e.mastheads, 1, cookie_header, ANDROID_FRONT_UA)
        w.signals.finished.connect(
            lambda c, en=e, r=resolver, g=generation: self._web_candidate_ready(en, r, c, g, one_done)
        )
        w.signals.error.connect(
            lambda m, en=e, r=resolver, g=generation: self._web_candidate_error(en, r, m, g, one_done)
        )
        self._start_worker(w)

    def _web_candidate_ready(self, e, resolver, candidate, generation, one_done):
        if generation != self.refresh_generation:
            return
        # v1.2.5: validação exclusiva do Valor/FrontPages da base v1.2.2.
        if e.name == "VALOR ECONÔMICO" and "frontpages.com" in candidate.source_url.lower():
            try:
                with Image.open(candidate.path) as im: w,h=im.size
                complete=w>=700 and h>=950 and h/max(1,w)>=1.34
            except Exception: complete=False
            if not complete:
                try: candidate.path.unlink(missing_ok=True)
                except Exception: pass
                e.status="Valor: FrontPages retornou capa recortada • tentando PressReader…"; self._refresh_list()
                self._start_single_web_resolver(e,generation,one_done,pressreader_only=True); return

        # Segurança extra igual ao Android: nunca aceitar Washington Post SPORTS.
        if e.name == "THE WASHINGTON POST" and "WASHINGTON POST SPORTS" in normalize(candidate.recognized_text):
            try:
                candidate.path.unlink(missing_ok=True)
            except Exception:
                pass
            e.status = "Falha: edição SPORTS rejeitada"
            self._refresh_list()
            one_done()
            return

        e.candidates = [candidate]
        e.chosen_index = 0
        e.review_index = 0
        e.automatic_index = 0
        source = "frontpages.com" if "frontpages.com" in candidate.source_url.lower() else "PressReader"
        e.status = f"Capa exibida atualmente no link • fonte {source} • confiança {candidate.confidence}%"
        e.automatic_status = e.status
        self._refresh_list()
        if self.current_entry is e:
            self._show_entry()
        one_done()

    def _web_candidate_error(self, e, resolver, msg, generation, one_done):
        if generation != self.refresh_generation:
            return
        if e.name == "VALOR ECONÔMICO" and "frontpages.com" in (resolver.last_referer or "").lower():
            e.status=f"Valor: FrontPages falhou ({msg}) • tentando PressReader…"; self._refresh_list()
            self._start_single_web_resolver(e,generation,one_done,pressreader_only=True); return
        e.status = f"Falha ao baixar capa: {msg}"
        self._refresh_list(); one_done()

    def _download_and_score(self, url, dest, referer, name, mastheads, page_number=1, cookie_header="", user_agent=""):
        download_image(url, dest, referer, cookie_header=cookie_header, user_agent=user_agent or None)
        score, conf, text = score_candidate(dest, name, mastheads, self.target_date())
        return CandidatePage(dest, score, conf, text, url, page_number)

    def _finalize_refresh(self, generation=None):
        if generation is not None and generation != self.refresh_generation:
            return
        self.set_busy(False)
        self.set_status("Atualização concluída")
        self._refresh_list()
        self._show_entry()

    def generate_pdf(self):
        try:
            p = export_pdf(self.entries, self.target_date())
            self.last_pdf = p

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("PDF gerado")
            box.setText("PDF gerado com sucesso.")
            box.setInformativeText(f"Salvo em:\n{p}")

            open_pdf_btn = box.addButton("ABRIR PDF", QMessageBox.ButtonRole.AcceptRole)
            open_folder_btn = box.addButton("ABRIR PASTA", QMessageBox.ButtonRole.ActionRole)
            box.addButton("FECHAR", QMessageBox.ButtonRole.RejectRole)
            box.exec()

            clicked = box.clickedButton()
            if clicked is open_pdf_btn:
                self.open_pdf()
            elif clicked is open_folder_btn:
                self.open_pdf_folder(p)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao gerar PDF", str(e))

    def open_pdf(self):
        p = self.last_pdf or (downloads_dir() / build_filename(self.target_date()))
        if not Path(p).exists():
            QMessageBox.warning(self, "PDF", "Nenhum PDF encontrado para a data selecionada.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def open_pdf_folder(self, pdf_path=None):
        p = Path(pdf_path or self.last_pdf or (downloads_dir() / build_filename(self.target_date())))
        folder = p.parent if p.suffix.lower() == ".pdf" else p
        if not folder.exists():
            QMessageBox.warning(self, "Pasta do PDF", "A pasta do PDF não foi encontrada.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
