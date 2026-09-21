from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import threading
import traceback

from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.extractor import (
    EXTRACTOR_QUALITIES,
    ExtractorEngine,
    ExtractorPortableStateStore,
    GloboplaySessionStore,
    YtDlpUpdater,
)
from monitor_noticias.extractor.login_helper import resolve_bundled_helper


class _DownloadThread(QThread):
    """Thread de download autocontida.

    A implementação antiga usava QObject + QThread + deleteLater em vários
    callbacks. Em operações longas do YouTube isso deixava a vida útil do
    worker/thread mais frágil e podia terminar o processo Qt se um QThread
    fosse destruído ainda ativo.

    Aqui a própria QThread executa o download e só é liberada depois de
    `finished`. Nenhuma exceção sai da thread.
    """

    progress = Signal(int, str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        engine: ExtractorEngine,
        url: str,
        quality_index: int,
        log_file: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.url = url
        self.quality_index = quality_index
        self.log_file = Path(log_file)

    def _write_failure_log(self, detail: str) -> None:
        try:
            self.log_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            with self.log_file.open(
                "a",
                encoding="utf-8",
                errors="replace",
            ) as handle:
                handle.write(
                    "\n\n=== FALHA NO DOWNLOAD ===\n"
                )
                handle.write(
                    f"URL: {self.url}\n"
                )
                handle.write(
                    f"Qualidade: {self.quality_index}\n"
                )
                handle.write(detail)
                handle.write("\n")
        except Exception:
            pass

    def run(self) -> None:
        try:
            result = self.engine.download(
                self.url,
                EXTRACTOR_QUALITIES[
                    self.quality_index
                ],
                "",
                lambda pct, msg: self.progress.emit(
                    int(pct),
                    str(msg),
                ),
            )
            self.succeeded.emit(result)

        except BaseException as exc:
            # BaseException também captura SystemExit ou exceções incomuns
            # disparadas dentro do worker, impedindo que escapem da thread.
            detail = (
                f"{exc.__class__.__name__}: {exc}\n"
                + traceback.format_exc()
            )
            self._write_failure_log(detail)

            message = (
                str(exc).strip()
                or "Falha no download."
            )
            self.failed.emit(message)


class _UpdaterWorker(QObject):
    status = Signal(str)
    finished = Signal(bool, str)

    def __init__(
        self,
        updater: YtDlpUpdater,
    ) -> None:
        super().__init__()
        self.updater = updater

    @Slot()
    def run(self) -> None:
        result = self.updater.update(
            lambda message: self.status.emit(
                str(message)
            )
        )
        self.finished.emit(
            result.success,
            result.message,
        )


class ExtractorPage(QWidget):
    """Workspace PySide6 do Extrator integrado ao Central."""

    login_result = Signal(bool, str)

    def __init__(
        self,
        app_root: Path,
    ) -> None:
        super().__init__()

        self.app_root = Path(app_root)
        self.engine = ExtractorEngine(
            self.app_root
        )
        self.state_store = (
            ExtractorPortableStateStore(
                self.app_root
            )
        )
        self.session_store = (
            GloboplaySessionStore(
                self.app_root
            )
        )
        self.updater = YtDlpUpdater(
            self.engine
        )

        self._operation_token = 0

        # Mantém uma referência forte até o QThread estar realmente encerrado.
        self._download_thread: (
            _DownloadThread | None
        ) = None

        # Atributo preservado por compatibilidade com versões anteriores.
        self._download_worker = None

        self._update_thread: (
            QThread | None
        ) = None

        self._login_process: (
            subprocess.Popen[object] | None
        ) = None

        self._login_waiter: (
            threading.Thread | None
        ) = None

        self._login_output: (
            Path | None
        ) = None

        self._shutting_down = False

        self._download_log = (
            self.app_root
            / "logs"
            / "extractor-video.log"
        )

        self.login_result.connect(
            self._finish_login
        )

        self._build_ui()
        self._refresh_history()
        self._refresh_session()
        self._refresh_binary_status()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(
            10,
            8,
            10,
            8,
        )
        root.setSpacing(8)

        title = QLabel(
            "EXTRATOR DE VÍDEOS"
        )
        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Fluxo direto Windows Portable v3.0.1 integrado ao Monitor"
        )
        subtitle.setObjectName(
            "pageSubtitle"
        )

        root.addWidget(title)
        root.addWidget(subtitle)

        self.tabs = QTabBar()

        for label in (
            "Download",
            "Histórico",
            "Configurações",
        ):
            self.tabs.addTab(label)

        self.tabs.currentChanged.connect(
            self._switch_tab
        )
        root.addWidget(self.tabs)

        self.stack = QStackedWidget()
        root.addWidget(
            self.stack,
            1,
        )

        self.stack.addWidget(
            self._build_download_tab()
        )
        self.stack.addWidget(
            self._build_history_tab()
        )
        self.stack.addWidget(
            self._build_settings_tab()
        )

    def _build_download_tab(
        self,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.url = QLineEdit()
        self.url.setPlaceholderText(
            "https://..."
        )
        self.url.returnPressed.connect(
            self.start_download
        )
        layout.addWidget(self.url)

        self.quality_group = QButtonGroup(
            self
        )
        self.quality_buttons: list[
            QRadioButton
        ] = []

        selected = (
            self.state_store.load_quality_index(
                1
            )
        )

        for index, quality in enumerate(
            EXTRACTOR_QUALITIES
        ):
            radio = QRadioButton(
                quality.label
            )
            self.quality_group.addButton(
                radio,
                index,
            )
            self.quality_buttons.append(
                radio
            )
            radio.toggled.connect(
                lambda checked, i=index:
                self._quality_changed(i)
                if checked
                else None
            )
            layout.addWidget(radio)

        if self.quality_buttons:
            selected = max(
                0,
                min(
                    selected,
                    len(
                        self.quality_buttons
                    )
                    - 1,
                ),
            )
            self.quality_buttons[
                selected
            ].setChecked(True)

        layout.addWidget(
            QLabel(
                "Formato de saída: MP4"
            )
        )

        self.download_button = QPushButton(
            "⇩  BAIXAR VÍDEO"
        )
        self.download_button.clicked.connect(
            self.start_download
        )
        layout.addWidget(
            self.download_button
        )

        actions = QHBoxLayout()

        self.open_videos_button = (
            QPushButton(
                "Abrir Vídeos"
            )
        )
        self.open_videos_button.clicked.connect(
            self.open_videos
        )

        self.cancel_button = QPushButton(
            "CANCELAR"
        )
        self.cancel_button.setEnabled(
            False
        )
        self.cancel_button.clicked.connect(
            self.cancel_download
        )

        actions.addWidget(
            self.open_videos_button
        )
        actions.addWidget(
            self.cancel_button
        )
        actions.addStretch()

        layout.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setRange(
            0,
            100,
        )
        self.progress.setValue(0)

        self.percent = QLabel(
            "0%"
        )

        self.status = QLabel(
            "Cole o link, escolha a qualidade e clique em BAIXAR VÍDEO."
        )
        self.status.setWordWrap(True)

        self.binary_status = QLabel()
        self.binary_status.setObjectName(
            "muted"
        )

        layout.addWidget(
            self.progress
        )
        layout.addWidget(
            self.percent
        )
        layout.addWidget(
            self.status
        )
        layout.addWidget(
            self.binary_status
        )
        layout.addStretch()

        return page

    def _build_history_tab(
        self,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(
            QLabel("HISTÓRICO")
        )

        self.clear_history_button = (
            QPushButton(
                "LIMPAR HISTÓRICO"
            )
        )
        self.clear_history_button.clicked.connect(
            self.clear_history
        )
        layout.addWidget(
            self.clear_history_button
        )

        self.history = QListWidget()
        layout.addWidget(
            self.history,
            1,
        )

        return page

    def _build_settings_tab(
        self,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(
            QLabel("CONFIGURAÇÕES")
        )
        layout.addWidget(
            QLabel("Globoplay")
        )

        self.session_status = QLabel()
        layout.addWidget(
            self.session_status
        )

        row = QHBoxLayout()

        self.login_button = QPushButton(
            "LOGIN GLOBOPLAY"
        )
        self.login_button.clicked.connect(
            self.open_globoplay_login
        )

        self.delete_session_button = (
            QPushButton(
                "APAGAR SESSÃO"
            )
        )
        self.delete_session_button.clicked.connect(
            self.delete_session
        )

        row.addWidget(
            self.login_button
        )
        row.addWidget(
            self.delete_session_button
        )
        row.addStretch()

        layout.addLayout(row)

        help_text = QLabel(
            "O login usa o helper oficial empacotado da release. "
            "A senha não é armazenada; somente os cookies da sessão "
            "são protegidos pelo Windows."
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        layout.addWidget(
            QLabel("yt-dlp")
        )

        self.update_button = QPushButton(
            "ATUALIZAR YT-DLP"
        )
        self.update_button.clicked.connect(
            self.update_ytdlp
        )
        layout.addWidget(
            self.update_button
        )

        self.settings_status = QLabel()
        self.settings_status.setWordWrap(
            True
        )
        layout.addWidget(
            self.settings_status
        )

        layout.addStretch()

        return page

    def _switch_tab(
        self,
        index: int,
    ) -> None:
        self.stack.setCurrentIndex(
            index
        )

        if index == 1:
            self._refresh_history()

        elif index == 2:
            self._refresh_session()

    def _quality_changed(
        self,
        index: int,
    ) -> None:
        cancel_button = getattr(
            self,
            "cancel_button",
            None,
        )

        if (
            cancel_button is None
            or not cancel_button.isEnabled()
        ):
            self.state_store.save_quality_index(
                index
            )

    def _quality_index(self) -> int:
        index = (
            self.quality_group.checkedId()
        )

        return (
            index
            if (
                0
                <= index
                < len(
                    EXTRACTOR_QUALITIES
                )
            )
            else 1
        )

    def start_download(self) -> None:
        """Inicia sem deixar exceções/threads encerrarem o Central."""

        clean_url = self.url.text().strip()

        current = self._download_thread

        if (
            not clean_url
            or (
                current is not None
                and current.isRunning()
            )
        ):
            return

        # Impede iniciar sobre uma thread antiga que ainda esteja finalizando.
        if (
            current is not None
            and not current.isFinished()
        ):
            self.status.setText(
                "Aguarde o download anterior encerrar completamente."
            )
            return

        self._operation_token += 1
        token = self._operation_token

        index = self._quality_index()
        self.state_store.save_quality_index(
            index
        )

        self.progress.setValue(0)
        self.percent.setText("0%")

        if (
            "youtube.com" in clean_url.lower()
            or "youtu.be" in clean_url.lower()
        ):
            if not self.engine.deno.exists():
                self.status.setText(
                    "Deno não encontrado no portable. "
                    "O YouTube atual requer runtime JavaScript; "
                    "use o build com deno.exe incluído."
                )
                self._refresh_binary_status()
                return

        self.status.setText(
            "Iniciando download direto em "
            f"{EXTRACTOR_QUALITIES[index].label}..."
        )

        self._set_busy(True)

        try:
            thread = _DownloadThread(
                self.engine,
                clean_url,
                index,
                self._download_log,
                self,
            )

            thread.progress.connect(
                lambda pct, msg, t=token:
                self._download_progress(
                    t,
                    pct,
                    msg,
                )
            )

            thread.succeeded.connect(
                lambda path, t=token:
                self._download_success(
                    t,
                    path,
                )
            )

            thread.failed.connect(
                lambda message, t=token:
                self._download_failure(
                    t,
                    message,
                )
            )

            # Só limpamos a referência quando QThread.finished foi emitido.
            # Não usamos deleteLater no QThread ativo.
            thread.finished.connect(
                lambda t=thread:
                self._clear_download_thread(
                    t
                )
            )

            self._download_thread = thread
            thread.start()

        except BaseException as exc:
            self._download_thread = None
            self._set_busy(False)

            try:
                self._download_log.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                with self._download_log.open(
                    "a",
                    encoding="utf-8",
                    errors="replace",
                ) as handle:
                    handle.write(
                        "\n\n=== FALHA AO CRIAR THREAD ===\n"
                    )
                    handle.write(
                        traceback.format_exc()
                    )
            except Exception:
                pass

            self.status.setText(
                "Não foi possível iniciar o download, "
                "mas o Central foi mantido aberto. "
                f"Detalhe: {exc}"
            )

    def _set_busy(
        self,
        busy: bool,
    ) -> None:
        self.download_button.setEnabled(
            not busy
        )

        # O botão Cancelar só fica ativo durante operação real.
        self.cancel_button.setEnabled(
            busy
        )

        self.login_button.setEnabled(
            not busy
        )

        self.update_button.setEnabled(
            not busy
            and self._update_thread is None
        )

        for radio in (
            self.quality_buttons
        ):
            radio.setEnabled(
                not busy
            )

    def _download_progress(
        self,
        token: int,
        pct: int,
        message: str,
    ) -> None:
        if (
            token
            != self._operation_token
            or self._shutting_down
        ):
            return

        value = max(
            0,
            min(
                100,
                int(pct),
            ),
        )

        self.progress.setValue(
            value
        )
        self.percent.setText(
            f"{value}%"
        )

        if message:
            self.status.setText(
                message
            )

    def _download_success(
        self,
        token: int,
        path: object,
    ) -> None:
        if (
            token
            != self._operation_token
            or self._shutting_down
        ):
            return

        file = Path(
            str(path)
        )

        self.progress.setValue(
            100
        )
        self.percent.setText(
            "100%"
        )
        self.status.setText(
            f"Download concluído: {file.name}"
        )

        self.state_store.add_history(
            str(
                file.resolve()
            )
        )
        self._refresh_history()

        # A thread ainda pode estar saindo do run(). Mantemos busy até
        # receber QThread.finished em _clear_download_thread.
        self.cancel_button.setEnabled(
            False
        )

    def _download_failure(
        self,
        token: int,
        message: str,
    ) -> None:
        if (
            token
            != self._operation_token
            or self._shutting_down
        ):
            return

        self.status.setText(
            message
            or "Falha no download."
        )

        self.cancel_button.setEnabled(
            False
        )

    def _clear_download_thread(
        self,
        thread: QThread,
    ) -> None:
        if (
            self._download_thread
            is thread
        ):
            self._download_thread = None
            self._download_worker = None

        if self._shutting_down:
            return

        self._set_busy(False)
        self._refresh_binary_status()

    def cancel_download(self) -> None:
        thread = self._download_thread

        if (
            thread is None
            or not thread.isRunning()
        ):
            return

        # Invalida sinais de progresso/resultado da operação cancelada.
        self._operation_token += 1

        self.status.setText(
            "Cancelando download com segurança..."
        )

        # Não libera o botão BAIXAR enquanto o worker ainda está saindo,
        # evitando dois downloads simultâneos no mesmo ExtractorEngine.
        self.cancel_button.setEnabled(
            False
        )
        self.download_button.setEnabled(
            False
        )

        self.engine.cancel()

    def open_videos(self) -> None:
        self.engine.videos_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        if os.name == "nt":
            os.startfile(  # type: ignore[attr-defined]
                str(
                    self.engine.videos_dir
                )
            )
        else:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(
                        self.engine.videos_dir
                    )
                )
            )

    def _refresh_history(self) -> None:
        items = (
            self.state_store.load_history()
        )

        self.history.clear()
        self.history.addItems(items)

        self.clear_history_button.setEnabled(
            bool(items)
        )

    def clear_history(self) -> None:
        self.state_store.clear_history()
        self._refresh_history()

    def _refresh_session(self) -> None:
        saved = (
            self.session_store.has_saved_session()
        )

        self.session_status.setText(
            "Sessão protegida salva neste usuário do Windows (DPAPI)."
            if saved
            else "Nenhuma sessão Globoplay salva."
        )

        self.delete_session_button.setEnabled(
            saved
        )

    def delete_session(self) -> None:
        deleted = (
            self.session_store.delete_saved_session()
        )

        self._refresh_session()

        self.settings_status.setText(
            "Sessão Globoplay apagada."
            if deleted
            else "Não foi possível apagar a sessão Globoplay."
        )

    def open_globoplay_login(
        self,
    ) -> None:
        try:
            helper = resolve_bundled_helper(
                self.app_root
            )
        except Exception as exc:
            self.settings_status.setText(
                "Navegador interno do Globoplay não encontrado no pacote: "
                f"{exc}"
            )
            return

        data_dir = (
            self.app_root
            / "data"
            / "extractor"
        )
        profile = (
            data_dir
            / "globoplay-web-profile"
        )

        data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        profile.mkdir(
            parents=True,
            exist_ok=True,
        )

        fd, name = tempfile.mkstemp(
            prefix="globoplay-session-",
            suffix=".cookies",
            dir=data_dir,
        )
        os.close(fd)

        output = Path(name)

        self.settings_status.setText(
            "Abrindo login oficial do Globoplay..."
        )

        try:
            process = subprocess.Popen(
                [
                    str(helper),
                    "--output",
                    str(output),
                    "--profile-dir",
                    str(profile),
                ],
                cwd=str(
                    self.app_root
                ),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
        except Exception as exc:
            output.unlink(
                missing_ok=True
            )
            self.settings_status.setText(
                "Não foi possível abrir o navegador interno do Globoplay: "
                f"{exc}"
            )
            return

        self._login_process = process
        self._login_output = output

        def wait_login() -> None:
            try:
                exit_code = (
                    process.wait()
                )

                if exit_code != 0:
                    if not self._shutting_down:
                        self.login_result.emit(
                            False,
                            "Login do Globoplay cancelado ou não concluído.",
                        )
                    return

                if (
                    not output.is_file()
                    or output.stat().st_size
                    <= 0
                ):
                    if not self._shutting_down:
                        self.login_result.emit(
                            False,
                            "O navegador interno não retornou cookies da sessão.",
                        )
                    return

                netscape = output.read_text(
                    encoding="utf-8",
                    errors="replace",
                )

                count = sum(
                    1
                    for line
                    in netscape.splitlines()
                    if (
                        line.strip()
                        and not line.startswith(
                            "#"
                        )
                    )
                )

                if count <= 0:
                    if not self._shutting_down:
                        self.login_result.emit(
                            False,
                            "Nenhum cookie Globo/Globoplay foi capturado.",
                        )
                    return

                self.session_store.save_netscape_cookies(
                    netscape
                )

                if not self._shutting_down:
                    self.login_result.emit(
                        True,
                        "Sessão Globoplay salva com segurança "
                        f"({count} cookies).",
                    )

            except Exception as exc:
                if not self._shutting_down:
                    self.login_result.emit(
                        self.session_store.has_saved_session(),
                        "Falha ao salvar sessão Globoplay: "
                        f"{exc}",
                    )

            finally:
                if (
                    self._login_process
                    is process
                ):
                    self._login_process = None

                if (
                    self._login_output
                    == output
                ):
                    self._login_output = None

                output.unlink(
                    missing_ok=True
                )

        waiter = threading.Thread(
            target=wait_login,
            name="globoplay-login-waiter",
            daemon=True,
        )

        self._login_waiter = waiter
        waiter.start()

    @Slot(bool, str)
    def _finish_login(
        self,
        _saved: bool,
        message: str,
    ) -> None:
        if self._shutting_down:
            return

        self._refresh_session()
        self.settings_status.setText(
            message
        )

    def update_ytdlp(self) -> None:
        if (
            self._update_thread
            is not None
            or (
                self._download_thread
                is not None
                and self._download_thread.isRunning()
            )
        ):
            return

        self.update_button.setEnabled(
            False
        )
        self.update_button.setText(
            "ATUALIZANDO..."
        )
        self.settings_status.setText(
            "Preparando atualização do yt-dlp..."
        )

        thread = QThread(self)
        worker = _UpdaterWorker(
            self.updater
        )

        worker.moveToThread(thread)
        thread.started.connect(
            worker.run
        )
        worker.status.connect(
            self.settings_status.setText
        )
        worker.finished.connect(
            self._update_finished
        )
        worker.finished.connect(
            thread.quit
        )
        thread.finished.connect(
            worker.deleteLater
        )
        thread.finished.connect(
            lambda t=thread:
            self._clear_update_thread(t)
        )

        self._update_thread = thread
        thread.start()

    def _update_finished(
        self,
        _success: bool,
        message: str,
    ) -> None:
        if self._shutting_down:
            return

        self.settings_status.setText(
            message
        )
        self._refresh_binary_status()

    def _clear_update_thread(
        self,
        thread: QThread,
    ) -> None:
        if (
            self._update_thread
            is thread
        ):
            self._update_thread = None

        if self._shutting_down:
            return

        self.update_button.setText(
            "ATUALIZAR YT-DLP"
        )
        self.update_button.setEnabled(
            not (
                self._download_thread
                is not None
                and self._download_thread.isRunning()
            )
        )

    def shutdown(
        self,
        timeout_ms: int = 7000,
    ) -> bool:
        """Cancela subprocessos e aguarda a thread realmente encerrar."""

        self._shutting_down = True
        self._operation_token += 1

        self.engine.cancel()

        process = self._login_process

        if process is not None:
            self.engine.runner.destroy_tree(
                process
            )

        deadline = max(
            0,
            int(timeout_ms),
        )

        download = self._download_thread

        if (
            download is not None
            and download.isRunning()
        ):
            download.requestInterruption()

            if not download.wait(
                deadline
            ):
                self._shutting_down = False
                return False

        update = self._update_thread

        if (
            update is not None
            and update.isRunning()
        ):
            update.requestInterruption()
            update.quit()

            if not update.wait(
                deadline
            ):
                self._shutting_down = False
                return False

        waiter = self._login_waiter

        if (
            waiter is not None
            and waiter.is_alive()
        ):
            waiter.join(
                timeout=max(
                    0.0,
                    deadline
                    / 1000.0,
                )
            )

            if waiter.is_alive():
                self._shutting_down = False
                return False

        output = self._login_output

        if output is not None:
            output.unlink(
                missing_ok=True
            )
            self._login_output = None

        return True

    def _refresh_binary_status(
        self,
    ) -> None:
        youtube_ready = (
            self.engine.yt_dlp.exists()
            and self.engine.ffmpeg.exists()
            and self.engine.deno.exists()
        )

        self.binary_status.setText(
            "Binários: "
            f"yt-dlp={self.engine.yt_dlp.exists()} • "
            f"stable={self.engine.yt_dlp_stable.exists()} • "
            f"ffmpeg={self.engine.ffmpeg.exists()} • "
            f"ffprobe={self.engine.ffprobe.exists()} • "
            f"deno={self.engine.deno.exists()} • "
            f"YouTube pronto={youtube_ready}"
        )

    def refresh(
        self,
        _state=None,
    ) -> None:
        self._refresh_binary_status()
