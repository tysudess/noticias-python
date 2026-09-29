from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from monitor_noticias.diagnostics import (
    DiagnosticReport,
    SystemDiagnostics,
    build_diagnostic_package,
)
from monitor_noticias.ui.sections import Section


class _DiagnosticsWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, runner: SystemDiagnostics) -> None:
        super().__init__()
        self.runner = runner

    def run(self) -> None:
        try:
            self.completed.emit(self.runner.run())
        except Exception as exc:
            self.failed.emit(str(exc) or exc.__class__.__name__)
        finally:
            self.finished.emit()


class DiagnosticsDialog(QDialog):
    def __init__(self, paths, controller, auth_runtime=None, parent=None) -> None:
        super().__init__(parent)
        self.paths = paths
        self.controller = controller
        self.auth_runtime = auth_runtime
        self.report: DiagnosticReport | None = None
        self._thread: QThread | None = None
        self._worker: _DiagnosticsWorker | None = None

        self.setWindowTitle("Diagnóstico do Sistema")
        self.resize(860, 650)
        self.setMinimumSize(720, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        title = QLabel("Diagnóstico do Sistema")
        title.setObjectName("diagTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "Verifica componentes locais, Proxy Geral, Apps Script e a validação real da sessão. "
            "Nenhuma senha ou token é exibido no relatório."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("diagMuted")
        root.addWidget(subtitle)

        self.summary = QLabel("Clique em “Executar diagnóstico completo”.")
        self.summary.setObjectName("diagSummary")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Os resultados aparecerão aqui.")
        root.addWidget(self.output, 1)

        buttons = QHBoxLayout()
        self.run_button = QPushButton("▶  Executar diagnóstico completo")
        self.run_button.setObjectName("diagPrimary")
        self.run_button.clicked.connect(self._run)
        buttons.addWidget(self.run_button)

        self.package_button = QPushButton("▣  Gerar ZIP de diagnóstico")
        self.package_button.setObjectName("diagSecondary")
        self.package_button.setEnabled(False)
        self.package_button.clicked.connect(self._package)
        buttons.addWidget(self.package_button)

        buttons.addStretch(1)

        self.close_button = QPushButton("Fechar")
        self.close_button.setObjectName("diagSecondary")
        self.close_button.clicked.connect(self.reject)
        buttons.addWidget(self.close_button)

        root.addLayout(buttons)

        self.setStyleSheet(
            """
            QDialog { background:#F4F8FD; }
            QLabel#diagTitle {
                color:#08245F;
                font-size:23px;
                font-weight:900;
            }
            QLabel#diagMuted {
                color:#6079A5;
                font-size:11px;
            }
            QLabel#diagSummary {
                background:#FFFFFF;
                color:#173E75;
                border:1px solid #D4E4F5;
                border-radius:10px;
                padding:10px 12px;
                font-weight:800;
            }
            QPlainTextEdit {
                background:#FFFFFF;
                color:#173E75;
                border:1px solid #D4E4F5;
                border-radius:10px;
                padding:10px;
                font-family:'Consolas';
                font-size:10px;
            }
            QPushButton#diagPrimary {
                background:#0A7DF8;
                color:#FFFFFF;
                border:0;
                border-radius:9px;
                padding:10px 15px;
                font-weight:900;
            }
            QPushButton#diagSecondary {
                background:#FFFFFF;
                color:#0C3974;
                border:1px solid #C9DDF2;
                border-radius:9px;
                padding:10px 15px;
                font-weight:800;
            }
            """
        )

    def _set_busy(self, busy: bool) -> None:
        self.run_button.setEnabled(not busy)
        self.close_button.setEnabled(not busy)
        if busy:
            self.package_button.setEnabled(False)

    def reject(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            self.summary.setText(
                "Aguarde o diagnóstico terminar antes de fechar esta janela."
            )
            return
        super().reject()

    def _run(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return

        self.report = None
        self.output.clear()
        self.summary.setText("Executando testes…")
        self._set_busy(True)

        runner = SystemDiagnostics(
            self.paths,
            self.controller,
            self.auth_runtime,
        )
        thread = QThread(self)
        worker = _DiagnosticsWorker(runner)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.completed.connect(self._completed)
        worker.failed.connect(self._failed)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)

        def cleanup():
            self._set_busy(False)
            self._thread = None
            self._worker = None

        thread.finished.connect(cleanup)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker
        thread.start()

    def _completed(self, report: DiagnosticReport) -> None:
        self.report = report

        lines: list[str] = []
        icon = {
            "ok": "✓",
            "warning": "⚠",
            "error": "✕",
        }

        for item in report.items:
            timing = f" • {item.duration_ms} ms" if item.duration_ms else ""
            lines.append(
                f"{icon.get(item.status, '•')} {item.label}{timing}\n"
                f"   {item.detail}\n"
            )

        self.output.setPlainText("\n".join(lines))

        if report.errors:
            self.summary.setText(
                f"Diagnóstico concluído: {report.errors} erro(s) e "
                f"{report.warnings} aviso(s)."
            )
        elif report.warnings:
            self.summary.setText(
                f"Diagnóstico concluído sem erros críticos; "
                f"{report.warnings} aviso(s)."
            )
        else:
            self.summary.setText("✓ Diagnóstico concluído sem falhas detectadas.")

        self.package_button.setEnabled(True)

    def _failed(self, message: str) -> None:
        self.summary.setText("Falha ao executar diagnóstico.")
        self.output.setPlainText(message)

    def _package(self) -> None:
        if self.report is None:
            return

        try:
            target = build_diagnostic_package(self.paths, self.report)
        except Exception as exc:
            self.summary.setText(
                "Não foi possível gerar o ZIP: "
                + (str(exc) or exc.__class__.__name__)
            )
            return

        self.summary.setText(f"✓ ZIP gerado em: {target}")



def install_diagnostics_panel(window, auth_runtime=None) -> None:
    pages = getattr(window, "pages", None)

    if not isinstance(pages, dict):
        return

    page = pages.get(Section.SETTINGS)

    if page is None or getattr(page, "_diagnostics_v90_installed", False):
        return

    root = getattr(page, "root", None)

    if root is None:
        return

    card = QFrame()
    card.setObjectName("settingsCard")
    card.setMinimumHeight(82)

    row = QHBoxLayout(card)
    row.setContentsMargins(16, 12, 16, 12)
    row.setSpacing(12)

    icon = QLabel("✓")
    icon.setObjectName("settingsBlueIcon")
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon.setFixedSize(48, 48)
    row.addWidget(icon)

    text = QVBoxLayout()
    title = QLabel("Diagnóstico do sistema")
    title.setObjectName("settingsTitle")
    subtitle = QLabel(
        "Teste login, Proxy Geral, bancos, armazenamento e ferramentas do Portable."
    )
    subtitle.setObjectName("settingsMuted")
    subtitle.setWordWrap(True)
    text.addWidget(title)
    text.addWidget(subtitle)
    row.addLayout(text, 1)

    button = QPushButton("Executar diagnóstico")
    button.setObjectName("settingsSecondary")
    row.addWidget(button)

    def open_dialog() -> None:
        dialog = DiagnosticsDialog(
            page.controller.paths,
            page.controller,
            auth_runtime,
            parent=window,
        )
        dialog.exec()

    button.clicked.connect(open_dialog)

    insert_at = max(0, root.count() - 1)
    root.insertWidget(insert_at, card)
    page._diagnostics_v90_installed = True
