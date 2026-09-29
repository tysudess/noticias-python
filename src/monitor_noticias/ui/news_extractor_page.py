from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from PySide6.QtCore import (
    QProcess,
    QProcessEnvironment,
    QTimer,
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
    """Extrator incorporado com worker Electron reutilizável.

    V88:
    - o Electron headless permanece aberto entre extrações;
    - o mesmo processo e as mesmas conexões de rede podem ser reaproveitados;
    - mudança de Proxy Geral reinicia automaticamente o worker;
    - uma leitura curta/suspeita pode ser repetida pelo runtime;
    - o resultado continua sendo entregue por arquivo JSON temporário.
    """

    back_requested = Signal()

    _ENV_SIGNATURE_KEYS = (
        "CENTRAL_PROXY_ENABLED",
        "CENTRAL_PROXY_HOST",
        "CENTRAL_PROXY_PORT",
        "CENTRAL_PROXY_USERNAME",
        "CENTRAL_PROXY_PASSWORD",
        "CENTRAL_NEWS_FAST_MODE",
        "CENTRAL_NEWS_NAV_TIMEOUT_MS",
        "CENTRAL_NEWS_IDLE_TIMEOUT_MS",
        "CENTRAL_NEWS_BLOCK_IMAGES",
        "CENTRAL_NEWS_BLOCK_MEDIA",
    )

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

        self._worker_signature: tuple[str, ...] | None = None
        self._stdout_buffer = ""
        self._stderr_tail = ""
        self._request_id = ""
        self._request_active = False
        self._request_started_at = 0.0

        self._result_timer = QTimer(self)
        self._result_timer.setInterval(120)
        self._result_timer.timeout.connect(
            self._poll_result_file
        )

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
            "O motor fica preparado após a primeira extração. "
            "Se o resultado vier curto ou suspeito, a Central faz "
            "uma nova leitura automaticamente antes de entregar o texto."
        )
        note.setObjectName("extractMuted")
        note.setWordWrap(True)
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

    def _environment_signature(self) -> tuple[str, ...]:
        return tuple(
            str(os.environ.get(key, ""))
            for key in self._ENV_SIGNATURE_KEYS
        )

    def _stop_worker(self) -> None:
        self._result_timer.stop()

        proc = self.process
        self.process = None
        self._worker_signature = None
        self._stdout_buffer = ""
        self._stderr_tail = ""

        if proc is None:
            return

        try:
            if proc.state() != QProcess.ProcessState.NotRunning:
                try:
                    proc.write(
                        (
                            json.dumps(
                                {"command": "shutdown"},
                                ensure_ascii=False,
                            )
                            + "\n"
                        ).encode("utf-8")
                    )
                    proc.waitForBytesWritten(250)
                except Exception:
                    pass

                if not proc.waitForFinished(1000):
                    proc.kill()
                    proc.waitForFinished(1200)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        try:
            proc.deleteLater()
        except Exception:
            pass

    def _ensure_worker(self) -> bool:
        signature = self._environment_signature()

        if (
            self.process is not None
            and self.process.state()
            != QProcess.ProcessState.NotRunning
            and self._worker_signature == signature
        ):
            return True

        self._stop_worker()

        env = QProcessEnvironment.systemEnvironment()
        env.insert("MONITOR_HEADLESS", "1")
        env.insert("MONITOR_PERSISTENT", "1")

        proc = QProcess(self)
        proc.setProcessEnvironment(env)
        proc.setProgram(str(self.exe))
        proc.setWorkingDirectory(str(self.exe.parent))
        proc.readyReadStandardOutput.connect(
            self._worker_stdout
        )
        proc.readyReadStandardError.connect(
            self._worker_stderr
        )
        proc.errorOccurred.connect(
            self._process_error
        )
        proc.finished.connect(
            self._worker_finished
        )

        self.process = proc
        self._worker_signature = signature

        self.status.setText(
            "Inicializando o motor de extração…"
        )

        proc.start()

        if not proc.waitForStarted(5000):
            self.status.setText(
                "Não foi possível iniciar o motor de extração."
            )
            self._stop_worker()
            return False

        return True

    def extract(self) -> None:
        if self._request_active:
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
            self.status.setText(
                "O link precisa começar com http:// ou https://."
            )
            return

        if not self.exe.is_file():
            self.status.setText(
                "Motor do Extrator não encontrado no portable: "
                f"{self.exe}"
            )
            return

        if not self._ensure_worker():
            return

        temp_dir = self.app_root / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        request_id = uuid.uuid4().hex
        result_file = (
            temp_dir
            / f"news-extractor-{request_id}.json"
        )

        self._request_id = request_id
        self.result_file = result_file
        self._request_active = True
        self._request_started_at = time.monotonic()
        self._stderr_tail = ""

        self.extract_button.setEnabled(False)
        self.extract_button.setText("Extraindo…")
        self.status.setText(
            "Extraindo matéria. O motor ficará pronto "
            "para reutilização na próxima URL…"
        )

        request = {
            "id": request_id,
            "url": direct,
            "resultFile": str(result_file),
        }

        try:
            written = self.process.write(
                (
                    json.dumps(
                        request,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8")
            )

            if written < 0:
                raise RuntimeError(
                    "O worker recusou a requisição."
                )

            self._result_timer.start()

        except Exception as exc:
            self._request_failed(
                "Não foi possível enviar a matéria ao motor: "
                + (str(exc) or exc.__class__.__name__)
            )
            self._stop_worker()

    def _poll_result_file(self) -> None:
        if not self._request_active:
            self._result_timer.stop()
            return

        result_file = self.result_file

        if (
            result_file is not None
            and result_file.is_file()
        ):
            self._consume_result()

    def _worker_stdout(self) -> None:
        proc = self.process

        if proc is None:
            return

        chunk = bytes(
            proc.readAllStandardOutput()
        ).decode(
            "utf-8",
            "ignore",
        )

        if not chunk:
            return

        self._stdout_buffer += chunk

        while "\n" in self._stdout_buffer:
            line, self._stdout_buffer = (
                self._stdout_buffer.split(
                    "\n",
                    1,
                )
            )

            line = line.strip()

            if not line.startswith(
                "CENTRAL_RESULT "
            ):
                continue

            payload_text = line[
                len("CENTRAL_RESULT "):
            ]

            try:
                payload = json.loads(
                    payload_text
                )
            except Exception:
                continue

            if (
                str(payload.get("id") or "")
                != self._request_id
            ):
                continue

            self._consume_result()

    def _worker_stderr(self) -> None:
        proc = self.process

        if proc is None:
            return

        text = bytes(
            proc.readAllStandardError()
        ).decode(
            "utf-8",
            "ignore",
        ).strip()

        if text:
            self._stderr_tail = text[-1200:]

    def _process_error(self, _error) -> None:
        if not self._request_active:
            return

        self._request_failed(
            "O motor de extração apresentou uma falha de processo."
        )

    def _worker_finished(
        self,
        _code=0,
        _status=None,
    ) -> None:
        if self._request_active:
            if (
                self.result_file is not None
                and self.result_file.is_file()
            ):
                self._consume_result()
            else:
                detail = self._stderr_tail.strip()
                self._request_failed(
                    detail
                    or "O motor de extração encerrou inesperadamente."
                )

        self.process = None
        self._worker_signature = None

    def _request_failed(
        self,
        message: str,
    ) -> None:
        self._result_timer.stop()
        self._request_active = False
        self.extract_button.setEnabled(True)
        self.extract_button.setText("⇩  Extrair matéria")
        self.status.setText(message)

        if self.result_file is not None:
            try:
                self.result_file.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

        self.result_file = None
        self._request_id = ""

    def _consume_result(self) -> None:
        if not self._request_active:
            return

        result_file = self.result_file

        if (
            result_file is None
            or not result_file.is_file()
        ):
            return

        try:
            result = json.loads(
                result_file.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            # O runtime grava em arquivo temporário e renomeia; este fallback
            # apenas evita tratar uma leitura antecipada como falha definitiva.
            return

        elapsed_ms = int(
            (
                time.monotonic()
                - self._request_started_at
            )
            * 1000
        )

        self._result_timer.stop()

        try:
            result_file.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        self.result_file = None
        self._request_id = ""
        self._request_active = False

        self.extract_button.setEnabled(True)
        self.extract_button.setText("⇩  Extrair matéria")

        if not isinstance(result, dict):
            self.status.setText(
                "O motor terminou sem retornar um resultado válido."
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

        formatted = str(
            result.get("formatado")
            or ""
        )
        self.text.setPlainText(formatted)

        chars = int(
            result.get("corpoCaracteres")
            or len(formatted)
        )

        engine_ms = int(
            result.get("duracaoMs")
            or elapsed_ms
        )

        retried = bool(
            result.get(
                "segundaLeituraUsada",
                False,
            )
        )

        self.counter.setText(
            (
                f"{chars:,} caracteres"
                .replace(",", ".")
                + f"  •  {engine_ms / 1000:.1f}s"
            )
        )

        retry_text = (
            " • conteúdo conferido em uma segunda leitura"
            if retried
            else ""
        )

        self.status.setText(
            "✓ Matéria extraída com sucesso"
            + retry_text
            + ". O motor permanece pronto para a próxima URL."
        )

    def clear(self) -> None:
        if self._request_active:
            return

        self.url.clear()
        self.text.clear()
        self.counter.setText(
            "Nenhuma matéria extraída"
        )

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
        folder = (
            Path.home()
            / "Downloads"
            / "ExtratorMaterias"
        )
        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(folder)
            )
        )

    def _set_idle(self) -> None:
        self.status.setText(
            "Pronto para receber um link da aba Notícias."
        )

    def shutdown(self) -> bool:
        self._request_active = False
        self._result_timer.stop()

        if self.result_file is not None:
            try:
                self.result_file.unlink(
                    missing_ok=True
                )
            except Exception:
                pass
            self.result_file = None

        self._stop_worker()
        return True
