from __future__ import annotations

import json
import uuid
from pathlib import Path

from PySide6.QtCore import (
    QProcess,
    QProcessEnvironment,
    QUrl,
    Qt,
    Signal,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.url_tools import resolve_article_url


class NewsExtractorPage(QWidget):
    """Extrator de matérias realmente incorporado ao Monitor.

    A interface é PySide6 e vive diretamente no QStackedWidget.
    O Electron fica somente como motor headless durante a extração e não
    cria BrowserWindow nem aparece fora do programa.
    """

    back_requested = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()

        self.app_root = Path(app_root)
        self.exe = (
            self.app_root
            / "tools"
            / "news_extractor"
            / "ExtratorMateriasPortable-V1.25.19.exe"
        )

        self.process: QProcess | None = None
        self.result_file: Path | None = None

        self._build_ui()
        self._set_idle()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        input_card = QFrame()
        input_card.setObjectName("extractCard")

        il = QVBoxLayout(input_card)
        il.setContentsMargins(18, 16, 18, 16)
        il.setSpacing(9)

        kicker = QLabel("NOVA EXTRAÇÃO")
        kicker.setObjectName("extractKicker")
        il.addWidget(kicker)

        title = QLabel("Cole o link da matéria")
        title.setObjectName("extractTitle")
        il.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.url = QLineEdit()
        self.url.setObjectName("extractUrl")
        self.url.setPlaceholderText(
            "https://veiculo.com.br/noticia/materia-completa"
        )
        self.url.returnPressed.connect(self.extract)
        row.addWidget(self.url, 1)

        self.extract_button = QPushButton("⇩  Extrair matéria")
        self.extract_button.setObjectName("extractPrimary")
        self.extract_button.clicked.connect(self.extract)
        row.addWidget(self.extract_button)

        il.addLayout(row)

        note = QLabel(
            "O link recebido da aba Notícias usa o mesmo endereço direto "
            "de “Abrir matéria” e “Copiar link”."
        )
        note.setObjectName("extractMuted")
        il.addWidget(note)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        clear = QPushButton("×  Limpar")
        clear.clicked.connect(self.clear)
        actions.addWidget(clear)

        folder = QPushButton("▣  Abrir pasta")
        folder.clicked.connect(self.open_folder)
        actions.addWidget(folder)

        copy = QPushButton("▣  Copiar texto")
        copy.clicked.connect(self.copy_text)
        actions.addWidget(copy)

        actions.addStretch(1)
        il.addLayout(actions)

        root.addWidget(input_card)

        self.status_card = QFrame()
        self.status_card.setObjectName("statusCardNative")
        sl = QHBoxLayout(self.status_card)
        sl.setContentsMargins(14, 9, 14, 9)

        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDot")
        sl.addWidget(self.status_dot)

        self.status = QLabel()
        self.status.setObjectName("extractStatus")
        self.status.setWordWrap(True)
        sl.addWidget(self.status, 1)

        root.addWidget(self.status_card)

        result = QHBoxLayout()
        result.setSpacing(10)

        meta_card = QFrame()
        meta_card.setObjectName("extractCard")
        meta_card.setMinimumWidth(330)
        meta_card.setMaximumWidth(430)

        ml = QVBoxLayout(meta_card)
        ml.setContentsMargins(16, 14, 16, 14)
        ml.setSpacing(9)

        mh = QLabel("Dados identificados")
        mh.setObjectName("extractTitleSmall")
        ml.addWidget(mh)

        self.meta_labels = {}

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(7)

        for r, (key, label) in enumerate(
            (
                ("title", "TÍTULO"),
                ("source", "VEÍCULO"),
                ("date", "DATA"),
                ("author", "AUTOR"),
                ("subtitle", "SUBTÍTULO"),
            )
        ):
            cap = QLabel(label)
            cap.setObjectName("metaCaption")

            value = QLabel("—")
            value.setObjectName("metaValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

            grid.addWidget(cap, r * 2, 0)
            grid.addWidget(value, r * 2 + 1, 0)
            self.meta_labels[key] = value

        ml.addLayout(grid)
        ml.addStretch(1)
        result.addWidget(meta_card, 1)

        text_card = QFrame()
        text_card.setObjectName("extractCard")

        tl = QVBoxLayout(text_card)
        tl.setContentsMargins(16, 14, 16, 14)
        tl.setSpacing(8)

        th = QHBoxLayout()

        text_title = QLabel("Texto da matéria")
        text_title.setObjectName("extractTitleSmall")
        th.addWidget(text_title)

        th.addStretch(1)

        self.counter = QLabel("Nenhuma matéria extraída")
        self.counter.setObjectName("extractMuted")
        th.addWidget(self.counter)

        tl.addLayout(th)

        self.text = QPlainTextEdit()
        self.text.setObjectName("extractText")
        self.text.setPlaceholderText(
            "O conteúdo extraído aparecerá aqui."
        )
        tl.addWidget(self.text, 1)

        result.addWidget(text_card, 2)
        root.addLayout(result, 1)

        self.setStyleSheet(
            """
            QFrame#extractCard {
                background:#FFFFFF;
                border:1px solid #D6E6F7;
                border-radius:12px;
            }
            QLabel#extractKicker {
                color:#087AF7;
                font-size:10px;
                font-weight:900;
            }
            QLabel#extractTitle {
                color:#08245F;
                font-size:18px;
                font-weight:900;
            }
            QLabel#extractTitleSmall {
                color:#08245F;
                font-size:15px;
                font-weight:900;
            }
            QLabel#extractMuted {
                color:#6079A5;
                font-size:10px;
            }
            QLineEdit#extractUrl {
                min-height:42px;
                padding:0 13px;
                background:#FFFFFF;
                color:#08245F;
                border:1px solid #BED6EE;
                border-radius:9px;
                font-size:12px;
            }
            QPushButton#extractPrimary {
                min-height:42px;
                min-width:180px;
                background:#087AF7;
                color:#FFFFFF;
                border:0;
                border-radius:9px;
                padding:0 18px;
                font-weight:900;
                font-size:12px;
            }
            QPushButton#extractPrimary:disabled {
                background:#9FC7F2;
            }
            QFrame#statusCardNative {
                background:#EAF9F2;
                border:1px solid #BFE8D5;
                border-radius:10px;
            }
            QLabel#statusDot {
                color:#08A66B;
                font-size:15px;
            }
            QLabel#extractStatus {
                color:#087A59;
                font-size:11px;
                font-weight:700;
            }
            QLabel#metaCaption {
                color:#087AF7;
                font-size:9px;
                font-weight:900;
            }
            QLabel#metaValue {
                color:#08245F;
                font-size:11px;
                padding:3px 0 7px 0;
            }
            QPlainTextEdit#extractText {
                background:#F8FBFF;
                color:#102A55;
                border:1px solid #D5E4F4;
                border-radius:9px;
                padding:10px;
                font-family:'Segoe UI';
                font-size:11px;
                selection-background-color:#1689F8;
            }
            QPushButton {
                background:#FFFFFF;
                color:#0C3974;
                border:1px solid #C9DDF2;
                border-radius:8px;
                padding:7px 12px;
                font-weight:700;
            }
            QPushButton:hover {
                background:#EDF6FF;
            }
            """
        )

    def refresh(self, _state=None) -> None:
        pass

    def open_url(self, url: str) -> None:
        raw = str(url or "").strip()

        if not raw:
            self.url.clear()
            return

        self.status.setText("Resolvendo link direto do veículo…")
        QApplication.processEvents()

        direct = resolve_article_url(raw)
        direct = str(direct or raw).strip()

        self.url.setText(direct)
        self.url.setCursorPosition(len(direct))
        self.url.setFocus()

        self.status.setText(
            "Link direto do veículo recebido. Clique em “Extrair matéria”."
        )

    def extract(self) -> None:
        if self.process is not None:
            return

        raw = self.url.text().strip()

        if not raw:
            self.status.setText("Informe o link da matéria.")
            self.url.setFocus()
            return

        direct = resolve_article_url(raw)
        direct = str(direct or raw).strip()
        self.url.setText(direct)

        if not direct.lower().startswith(("http://", "https://")):
            self.status.setText("O link precisa começar com http:// ou https://.")
            return

        if not self.exe.is_file():
            self.status.setText(
                "Motor do Extrator não encontrado no portable: "
                f"{self.exe}"
            )
            return

        temp_dir = self.app_root / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        self.result_file = (
            temp_dir
            / f"news-extractor-{uuid.uuid4().hex}.json"
        )

        env = QProcessEnvironment.systemEnvironment()
        env.insert("MONITOR_HEADLESS", "1")
        env.insert("MONITOR_NEWS_URL", direct)
        env.insert(
            "MONITOR_RESULT_FILE",
            str(self.result_file),
        )

        proc = QProcess(self)
        proc.setProcessEnvironment(env)
        proc.setProgram(str(self.exe))
        proc.setWorkingDirectory(str(self.exe.parent))
        proc.finished.connect(self._finished)
        proc.errorOccurred.connect(self._process_error)

        self.process = proc

        self.extract_button.setEnabled(False)
        self.extract_button.setText("Extraindo…")
        self.status.setText(
            "Extraindo matéria dentro do Monitor. Aguarde…"
        )

        proc.start()

    def _process_error(self, _error) -> None:
        if self.process is None:
            return

        self.status.setText(
            "Não foi possível iniciar o motor de extração."
        )

    def _finished(self, _code=0, _status=None) -> None:
        proc = self.process
        self.process = None

        self.extract_button.setEnabled(True)
        self.extract_button.setText("⇩  Extrair matéria")

        result = None

        if (
            self.result_file is not None
            and self.result_file.is_file()
        ):
            try:
                result = json.loads(
                    self.result_file.read_text(
                        encoding="utf-8"
                    )
                )
            except Exception as exc:
                self.status.setText(
                    f"Resultado da extração inválido: {exc}"
                )

            try:
                self.result_file.unlink(missing_ok=True)
            except Exception:
                pass

        self.result_file = None

        if not isinstance(result, dict):
            if proc is not None:
                err = bytes(proc.readAllStandardError()).decode(
                    "utf-8",
                    "ignore",
                ).strip()
            else:
                err = ""

            self.status.setText(
                err
                or "O motor terminou sem retornar o resultado."
            )
            return

        if not result.get("ok"):
            self.status.setText(
                str(
                    result.get("erro")
                    or "Não foi possível extrair a matéria."
                )
            )
            return

        self.meta_labels["title"].setText(
            str(result.get("titulo") or "—")
        )
        self.meta_labels["source"].setText(
            str(result.get("veiculo") or "—")
        )
        self.meta_labels["date"].setText(
            str(result.get("data") or "—")
        )
        self.meta_labels["author"].setText(
            str(result.get("autor") or "—")
        )
        self.meta_labels["subtitle"].setText(
            str(result.get("subtitulo") or "—")
        )

        formatted = str(result.get("formatado") or "")
        self.text.setPlainText(formatted)

        chars = int(
            result.get("corpoCaracteres")
            or len(formatted)
        )

        self.counter.setText(
            f"{chars:,} caracteres".replace(",", ".")
        )

        self.status.setText(
            "✓ Matéria extraída com sucesso. "
            "O conteúdo pode ser revisado e editado nesta tela."
        )

    def clear(self) -> None:
        if self.process is not None:
            return

        self.url.clear()
        self.text.clear()
        self.counter.setText("Nenhuma matéria extraída")

        for label in self.meta_labels.values():
            label.setText("—")

        self._set_idle()

    def copy_text(self) -> None:
        text = self.text.toPlainText()

        if text:
            QApplication.clipboard().setText(text)
            self.status.setText(
                "Texto da matéria copiado para a área de transferência."
            )

    def open_folder(self) -> None:
        folder = Path.home() / "Downloads" / "ExtratorMaterias"
        folder.mkdir(parents=True, exist_ok=True)

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(folder))
        )

    def _set_idle(self) -> None:
        self.status.setText(
            "Pronto para receber um link da aba Notícias."
        )

    def shutdown(self) -> bool:
        if self.process is not None:
            try:
                self.process.kill()
                self.process.waitForFinished(1500)
            except Exception:
                pass
            self.process = None

        return True
