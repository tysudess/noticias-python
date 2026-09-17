from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractButton, QAbstractItemView, QFrame, QHeaderView, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QRadioButton, QTableWidget, QVBoxLayout, QWidget,
)


def _prop(widget: QWidget | None, name: str, value) -> None:
    if widget is None:
        return
    widget.setProperty(name, value)


def _secondary(button: QAbstractButton | None) -> None:
    if button is not None:
        _prop(button, "secondary", True)


def _decorate_home(page) -> None:
    for key, value in getattr(page, "metric_labels", {}).items():
        value.setObjectName("metricValue")
        parent = value.parentWidget()
        if isinstance(parent, QFrame):
            parent.setObjectName("metricCard")

    for name in ("home_buscar_demandas", "home_buscar_vídeos", "home_termos_de_busca"):
        button = page.findChild(QPushButton, name)
        if button:
            _secondary(button)


def _news_metric(title: str, value: str, accent: str) -> tuple[QFrame, QLabel]:
    box = QFrame()
    box.setStyleSheet(
        "QFrame{background:#FFFFFF;border:0;border-right:1px solid #E3EDF8;}"
        "QLabel{border:0;background:transparent;}"
    )
    lay = QVBoxLayout(box)
    lay.setContentsMargins(14, 8, 14, 8)
    lay.setSpacing(1)
    val = QLabel(value)
    val.setAlignment(Qt.AlignmentFlag.AlignCenter)
    val.setStyleSheet(f"font-size:20px;font-weight:900;color:{accent};")
    lab = QLabel(title)
    lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lab.setStyleSheet("font-size:10px;color:#58729B;")
    lay.addWidget(val)
    lay.addWidget(lab)
    return box, val


def _decorate_news(page, window) -> None:
    if getattr(page, "_reference_news_done", False):
        return
    page._reference_news_done = True

    page.root.setContentsMargins(0, 0, 0, 0)
    page.root.setSpacing(12)

    # Banner superior da referência.
    hero = QFrame()
    hero.setObjectName("newsHero")
    hero.setStyleSheet(
        "QFrame#newsHero{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        "stop:0 #F8FCFF,stop:0.62 #F1F8FF,stop:1 #EAF4FF);"
        "border:1px solid #D6E7F8;border-radius:13px;}"
    )
    hero_row = QHBoxLayout(hero)
    hero_row.setContentsMargins(18, 12, 18, 12)
    hero_row.setSpacing(18)

    texts = QVBoxLayout()
    texts.setSpacing(1)
    kicker = QLabel("CENTRAL DE INTELIGÊNCIA DE MÍDIA")
    kicker.setStyleSheet("color:#087AF7;font-size:10px;font-weight:900;")
    title = QLabel("Notícias")
    title.setStyleSheet("color:#08245F;font-size:28px;font-weight:900;")
    subtitle = QLabel("Acompanhe matérias em tempo real e transforme\ninformação em decisões estratégicas.")
    subtitle.setStyleSheet("color:#5874A0;font-size:12px;")
    texts.addWidget(kicker)
    texts.addWidget(title)
    texts.addWidget(subtitle)
    hero_row.addLayout(texts, 2)
    hero_row.addStretch(2)
    globe = QLabel("◯   ◌   ▤")
    globe.setAlignment(Qt.AlignmentFlag.AlignCenter)
    globe.setStyleSheet("color:#BFD9F6;font-size:52px;font-weight:300;")
    hero_row.addWidget(globe, 1)
    page.root.insertWidget(0, hero)

    # Caixa de filtros.
    top = getattr(page, "query", None)
    if top is not None:
        top.setMinimumHeight(40)
        top.setStyleSheet(
            "QLineEdit{background:#FFFFFF;border:1px solid #C9DDF5;border-radius:9px;"
            "padding:8px 12px;color:#173A70;}"
        )

    page.search24.setText("↻  Buscar últimas 24h")
    page.search24.setMinimumHeight(40)
    page.search24.setStyleSheet(
        "QPushButton{background:#0B7EF5;color:white;border:0;border-radius:9px;"
        "padding:8px 18px;font-weight:800;} QPushButton:hover{background:#076CDA;}"
    )
    page.only_demands.setStyleSheet("color:#173A70;font-weight:600;padding-left:6px;")

    for button in page.findChildren(QPushButton):
        text = button.text().strip().lower()
        if text in ("hoje", "24 horas", "7 dias", "30 dias"):
            button.setMinimumHeight(34)
            button.setStyleSheet(
                "QPushButton{background:#FFFFFF;color:#173A70;border:1px solid #C6DAEF;"
                "border-radius:8px;padding:6px 16px;font-weight:700;}"
                "QPushButton:hover{background:#EEF6FF;border-color:#1684F8;}"
            )
            if text == "hoje":
                button.setStyleSheet(
                    "QPushButton{background:#EAF4FF;color:#087AF7;border:1px solid #1684F8;"
                    "border-radius:8px;padding:6px 16px;font-weight:800;}"
                )

    page.custom.setText("▣  Período personalizado")
    page.custom.setMinimumHeight(34)
    page.custom.setStyleSheet(
        "QPushButton{background:#FFFFFF;color:#173A70;border:1px solid #C6DAEF;"
        "border-radius:8px;padding:6px 16px;font-weight:700;}"
        "QPushButton:checked{background:#EAF4FF;border-color:#1684F8;color:#087AF7;}"
    )

    # Área de andamento + métricas, lado a lado como na referência.
    exec_panel = getattr(page, "exec", None)
    if isinstance(exec_panel, QFrame):
        page.root.removeWidget(exec_panel)
        exec_panel.setStyleSheet(
            "QFrame{background:#FFFFFF;border:1px solid #D6E7F8;border-radius:12px;}"
            "QLabel{border:0;background:transparent;}"
            "QProgressBar{border:1px solid #C9DDF0;border-radius:5px;background:#E9F2FA;"
            "text-align:center;color:#4E668D;}"
            "QProgressBar::chunk{background:#12B886;border-radius:4px;}"
        )

        wrap = QFrame()
        wrap.setStyleSheet("QFrame{background:transparent;border:0;}")
        wr = QHBoxLayout(wrap)
        wr.setContentsMargins(0, 0, 0, 0)
        wr.setSpacing(12)
        wr.addWidget(exec_panel, 3)

        stats = QFrame()
        stats.setStyleSheet(
            "QFrame{background:#FFFFFF;border:1px solid #D6E7F8;border-radius:12px;}"
        )
        sr = QHBoxLayout(stats)
        sr.setContentsMargins(8, 8, 8, 8)
        sr.setSpacing(0)
        specs = [
            ("conclusion", "Conclusão", "0%", "#09A66E"),
            ("found", "Encontradas", "0", "#F2A600"),
            ("fresh", "Novas", "0", "#8C3CF6"),
            ("errors", "Falhas", "0", "#EF3158"),
            ("steps", "Etapas", "0/0", "#087AF7"),
            ("time", "Tempo", "00:00", "#038FDB"),
        ]
        page._news_ref_metrics = {}
        for key, label, value, accent in specs:
            box, val = _news_metric(label, value, accent)
            sr.addWidget(box, 1)
            page._news_ref_metrics[key] = val
        wr.addWidget(stats, 2)
        page.root.insertWidget(3, wrap)

    page.stop.setText("■  Parar busca")
    page.stop.setStyleSheet(
        "QPushButton{background:#FFF1F4;color:#E7335B;border:1px solid #FFADC0;"
        "border-radius:8px;padding:7px 14px;font-weight:700;}"
    )
    page.stop.setMaximumWidth(145)

    page.count.setStyleSheet("color:#08245F;font-size:17px;font-weight:900;padding:4px 2px;")

    table = getattr(page, "table", None)
    if isinstance(table, QTableWidget):
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.setWordWrap(True)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setStyleSheet(
            "QTableWidget{background:transparent;border:0;gridline-color:transparent;}"
            "QTableWidget::item{background:#FFFFFF;border-top:1px solid #DFEAF6;"
            "border-bottom:1px solid #DFEAF6;padding:8px;color:#173A70;}"
        )
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

    original_refresh = page.refresh

    def refreshed(state):
        original_refresh(state)

        metrics = getattr(page, "_news_ref_metrics", {})
        progress = state.news_progress
        fraction = max(0.0, min(1.0, float(getattr(progress, "fraction", 0.0))))
        pct = round(fraction * 100) if state.news_busy else 100
        found = getattr(progress, "found", len(state.news))
        errors = getattr(progress, "errors", 0)
        completed = getattr(progress, "completed", 0)
        total = getattr(progress, "total", 0)
        seconds = max(0, int(state.last_news_duration_ms // 1000))

        values = {
            "conclusion": f"{pct}%",
            "found": str(found),
            "fresh": str(len(state.new_news_links)),
            "errors": str(errors),
            "steps": f"{completed}/{total}",
            "time": f"{seconds // 60:02d}:{seconds % 60:02d}",
        }
        for key, value in values.items():
            if key in metrics:
                metrics[key].setText(value)

        rows = page._rows(state)
        page.count.setText(f"▣  Notícias encontradas    {len(rows)} resultado(s) para o período selecionado")

        if isinstance(page.table, QTableWidget):
            for row_index, news in enumerate(rows):
                page.table.setRowHeight(row_index, 64)
                title_item = page.table.item(row_index, 2)
                if title_item is not None:
                    font = title_item.font()
                    font.setBold(True)
                    title_item.setFont(font)

                actions = page.table.cellWidget(row_index, 5)
                if actions is not None and actions.layout() is not None:
                    lay = actions.layout()
                    for i in range(lay.count()):
                        w = lay.itemAt(i).widget()
                        if isinstance(w, QPushButton):
                            label = w.text().lower()
                            if "whatsapp" in label:
                                w.setStyleSheet(
                                    "QPushButton{background:#EAF9F1;color:#078B5F;border:1px solid #BFEBD7;"
                                    "border-radius:7px;padding:6px 10px;font-weight:700;}"
                                )
                            else:
                                w.setStyleSheet(
                                    "QPushButton{background:#FFFFFF;color:#173A70;border:1px solid #C8DBEF;"
                                    "border-radius:7px;padding:6px 10px;font-weight:700;}"
                                )

                    if not getattr(actions, "_extract_added", False):
                        extract = QPushButton("⇩  Extrair matéria")
                        extract.setStyleSheet(
                            "QPushButton{background:#F4EBFF;color:#8437E8;border:1px solid #DEC9FA;"
                            "border-radius:7px;padding:6px 10px;font-weight:700;}"
                        )

                        def open_extractor(_checked=False, url=news.link):
                            for section, target in getattr(window, "pages", {}).items():
                                if getattr(section, "name", "") == "EXTRACTOR":
                                    if hasattr(target, "url"):
                                        target.url.setText(url)
                                    window.navigate(section)
                                    break

                        extract.clicked.connect(open_extractor)
                        lay.addWidget(extract)
                        actions._extract_added = True

    page.refresh = refreshed


def _decorate_videos(page) -> None:
    _secondary(getattr(page, "stop", None))
    table = getattr(page, "table", None)
    if isinstance(table, QTableWidget):
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)


def _decorate_demands(page) -> None:
    _secondary(getattr(page, "all", None))
    status = getattr(page, "status", None)
    if isinstance(status, QLabel):
        status.setStyleSheet(
            "background:#ECFBF4;border:1px solid #B8EBD4;border-radius:12px;"
            "padding:16px;color:#086C50;font-weight:700;"
        )
    table = getattr(page, "table", None)
    if isinstance(table, QTableWidget):
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)


def _decorate_settings(page) -> None:
    _secondary(getattr(page, "test_proxy", None))
    proxy = getattr(page, "proxy_frame", None)
    if isinstance(proxy, QFrame):
        proxy.setObjectName("card")


def _decorate_extractor(page) -> None:
    button = getattr(page, "download_button", None)
    if isinstance(button, QPushButton):
        _prop(button, "gold", True)
        button.setMinimumHeight(54)

    for attr in ("open_videos_button", "cancel_button", "clear_history_button",
                 "delete_session_button", "login_button", "update_button"):
        _secondary(getattr(page, attr, None))

    progress = getattr(page, "progress", None)
    if isinstance(progress, QProgressBar):
        progress.setTextVisible(True)

    for radio in page.findChildren(QRadioButton):
        radio.setMinimumHeight(34)


def _decorate_pdf(page) -> None:
    for button in page.findChildren(QPushButton):
        text = button.text().lower()
        if any(x in text for x in ("voltar", "limpar", "selecionar", "trocar", "abrir")):
            _secondary(button)
        if "gerar pdf" in text:
            _prop(button, "green", True)
            button.setMinimumHeight(46)


def _decorate_video_editor(page) -> None:
    for button in page.findChildren(QPushButton):
        text = button.text().lower()
        if any(x in text for x in ("voltar", "abrir", "limpar")):
            _secondary(button)


def apply_reference_layout(window) -> None:
    """Aplica a camada visual às páginas existentes sem mexer nas regras de negócio."""
    pages = getattr(window, "pages", {})

    for section, page in pages.items():
        name = getattr(section, "name", "")
        if name == "HOME":
            _decorate_home(page)
        elif name == "NEWS":
            _decorate_news(page, window)
        elif name == "VIDEOS":
            _decorate_videos(page)
        elif name == "DEMANDS":
            _decorate_demands(page)
        elif name == "SETTINGS":
            _decorate_settings(page)
        elif name == "EXTRACTOR":
            _decorate_extractor(page)
        elif name == "PDF_EDITOR":
            _decorate_pdf(page)
        elif name == "VIDEO_EDITOR":
            _decorate_video_editor(page)

    for table in window.findChildren(QTableWidget):
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
