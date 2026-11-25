from __future__ import annotations

"""V157 — salvamento automático local e recuperação após encerramento inesperado.

O backup é gravado separadamente do .centralart, com gravação atômica e limite
explícito de tamanho. A recuperação só ocorre após confirmação do usuário e a
validação integral do documento, antes de substituir a sessão em memória.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import tempfile

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QMessageBox, QPushButton

from monitor_noticias.ui import art_studio_v150 as _v150

log = logging.getLogger(__name__)

_RECOVERY_SCHEMA = "central-art-studio-recovery"
_RECOVERY_VERSION = 1
_MAX_AUTOSAVE_BYTES = 160 * 1024 * 1024
_AUTOSAVE_DELAY_MS = 2200
_RECOVERY_MAX_AGE_DAYS = 14


def _recovery_path(page) -> Path:
    return Path(page.projects_dir) / ".recovery" / "autosave.json"


def _page_signature(page) -> tuple:
    pages = getattr(page, "_v150_pages", []) or []
    return (
        str(page.current_file) if getattr(page, "current_file", None) else None,
        tuple((str(p.get("id") or ""), str(p.get("name") or "")) for p in pages),
        int(getattr(page, "_v150_active_index", 0)),
    )


def _dirty_history_exists(page) -> bool:
    return bool(getattr(page, "_v157_document_dirty", False))


def _set_recovery_status(page, message: str) -> None:
    label = getattr(page, "v157_autosave_label", None)
    if label is not None:
        label.setText(message)


def _schedule_autosave(page) -> None:
    if getattr(page, "_v157_restoring", False):
        return
    if getattr(page, "_v145_history_suspended", False):
        return
    timer = getattr(page, "_v157_autosave_timer", None)
    if timer is None:
        return
    page._v157_document_dirty = True
    timer.start(_AUTOSAVE_DELAY_MS)
    _set_recovery_status(page, "Alterações detectadas · salvamento automático agendado")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if len(content.encode("utf-8")) > _MAX_AUTOSAVE_BYTES:
        raise ValueError("O backup automático ultrapassaria o limite de 160 MB.")

    fd, temporary_name = tempfile.mkstemp(
        prefix=".autosave-", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def _perform_autosave(page) -> None:
    if getattr(page, "_v157_restoring", False):
        return
    if getattr(page, "_v145_history_suspended", False):
        return
    if not _dirty_history_exists(page):
        _set_recovery_status(page, "Nenhuma alteração pendente para backup")
        return

    try:
        project = _v150._document_payload(page)
        record = {
            "schema": _RECOVERY_SCHEMA,
            "schema_version": _RECOVERY_VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "source_file": str(page.current_file) if page.current_file else None,
            "project": project,
        }
        serialized = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        path = _recovery_path(page)
        _atomic_write(path, serialized)
        stamp = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M:%S")
        _set_recovery_status(page, f"Backup automático atualizado · {stamp}")
        _update_recovery_button(page)
    except Exception as exc:
        log.exception("Falha ao criar backup automático do Estúdio de Artes")
        _set_recovery_status(page, f"Backup automático não concluído: {exc}")


def _read_recovery(page) -> dict | None:
    path = _recovery_path(page)
    try:
        if not path.is_file():
            return None
        stat = path.stat()
        if stat.st_size <= 0 or stat.st_size > _MAX_AUTOSAVE_BYTES:
            return None
        age = datetime.now().timestamp() - stat.st_mtime
        if age > _RECOVERY_MAX_AGE_DAYS * 86400:
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            return None
        if record.get("schema") != _RECOVERY_SCHEMA:
            return None
        if int(record.get("schema_version", 0)) != _RECOVERY_VERSION:
            return None
        project = record.get("project")
        if not isinstance(project, dict):
            return None
        if project.get("format") != _v150.PROJECT_FORMAT:
            return None
        return record
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        log.exception("Backup automático do Estúdio inválido ou inacessível")
        return None


def _update_recovery_button(page) -> None:
    button = getattr(page, "v157_recovery_button", None)
    if button is None:
        return
    path = _recovery_path(page)
    try:
        stat = path.stat()
        age = datetime.now().timestamp() - stat.st_mtime
        valid_size = 0 < stat.st_size <= _MAX_AUTOSAVE_BYTES
        recent = age <= _RECOVERY_MAX_AGE_DAYS * 86400
        available = path.is_file() and valid_size and recent
    except OSError:
        available = False
        stat = None
    button.setEnabled(available)
    if not available:
        button.setToolTip("Nenhum backup automático válido está disponível.")
        return
    stamp = datetime.fromtimestamp(stat.st_mtime).astimezone().strftime("%d/%m/%Y %H:%M:%S")
    button.setToolTip(f"Backup automático de {stamp}\nO conteúdo será validado antes da recuperação.")


def _clear_recovery(page) -> None:
    timer = getattr(page, "_v157_autosave_timer", None)
    if timer is not None:
        timer.stop()
    page._v157_document_dirty = False
    try:
        _recovery_path(page).unlink(missing_ok=True)
    except OSError:
        log.exception("Não foi possível remover o backup após salvar o projeto")
    _update_recovery_button(page)
    _set_recovery_status(page, "Projeto salvo · backup de recuperação removido")


def _apply_recovered_project(page, project: dict) -> None:
    pages = _v150._validate_document(page, project)
    active = max(0, min(len(pages) - 1, int(project.get("active_page_index", 0))))

    current_payload = _v150._document_payload(page)
    current_stack = page._v145_history
    old_histories = set(page._v150_page_histories.values())

    page._v157_restoring = True
    page._v145_history_suspended = True
    try:
        for stack in old_histories:
            stack.clear()
            if stack is not current_stack:
                stack.deleteLater()
        current_stack.clear()

        page._v150_pages = pages
        page._v150_active_index = active
        page._v150_page_histories = {pages[active]["id"]: current_stack}
        _v150._bind_history_stack(page, current_stack)
        page.current_file = None
        _v150._update_tabs(page)
        _v150._restore_page_data(page, pages[active]["data"], reset_history=False)
        _v150._mark_history_baseline(page)
        page._v150_update_page_chrome()
        page.project_label.setText("Sessão recuperada · salvar como novo projeto")
        page.status_label.setText(
            f"Sessão recuperada com {len(pages)} página(s). Salve o projeto para criar um novo arquivo .centralart."
        )
    except Exception:
        log.exception("Falha ao aplicar a sessão recuperada; tentando restaurar a sessão anterior")
        try:
            rollback_pages = _v150._validate_document(page, current_payload)
            rollback_active = max(
                0,
                min(len(rollback_pages) - 1, int(current_payload.get("active_page_index", 0))),
            )
            page._v150_pages = rollback_pages
            page._v150_active_index = rollback_active
            page._v150_page_histories = {rollback_pages[rollback_active]["id"]: current_stack}
            _v150._bind_history_stack(page, current_stack)
            _v150._update_tabs(page)
            _v150._restore_page_data(page, rollback_pages[rollback_active]["data"], reset_history=False)
            _v150._mark_history_baseline(page)
            page._v150_update_page_chrome()
        except Exception:
            log.exception("Falha ao restaurar também a sessão anterior")
        raise
    finally:
        page._v145_history_suspended = False
        page._v157_restoring = False

    _update_recovery_button(page)
    _set_recovery_status(page, "Backup recuperado · faça uma cópia com Salvar projeto")


def _recover_session(page) -> None:
    record = _read_recovery(page)
    if record is None:
        _update_recovery_button(page)
        QMessageBox.information(
            page,
            "Recuperação automática",
            "Não há um backup automático válido disponível. Os backups expiram após 14 dias.",
        )
        return

    saved_at = str(record.get("saved_at") or "horário desconhecido")
    source = str(record.get("source_file") or "Projeto sem nome")
    answer = QMessageBox.question(
        page,
        "Recuperar sessão anterior",
        "Foi encontrado um backup automático.\n\n"
        f"Data: {saved_at}\nOrigem: {source}\n\n"
        "A sessão aberta será substituída. Deseja recuperar o backup?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return

    try:
        _apply_recovered_project(page, record["project"])
    except Exception as exc:
        log.exception("Não foi possível recuperar o backup automático")
        QMessageBox.critical(
            page,
            "Falha na recuperação",
            f"O backup não pôde ser restaurado. A sessão aberta foi preservada.\n\n{exc}",
        )


def _install_autosave_toolbar(page) -> None:
    toolbar = page.findChild(QFrame, "artStudioToolbar")
    layout = toolbar.layout() if toolbar is not None else None
    if layout is None:
        return

    page.v157_recovery_button = QPushButton("Recuperar sessão")
    page.v157_recovery_button.setObjectName("artStudioRecoverSessionV157")
    page.v157_recovery_button.setProperty("secondary", True)
    page.v157_recovery_button.setMinimumHeight(32)
    page.v157_recovery_button.setToolTip("Recupera o último backup automático disponível.")
    page.v157_recovery_button.clicked.connect(lambda: _recover_session(page))

    save_index = layout.indexOf(page.save_button)
    layout.insertWidget(save_index if save_index >= 0 else layout.count(), page.v157_recovery_button)

    page.v157_autosave_label = QLabel("Backup automático aguardando alterações")
    page.v157_autosave_label.setObjectName("muted")
    page.v157_autosave_label.setWordWrap(False)
    layout.addWidget(page.v157_autosave_label)
    _update_recovery_button(page)
    if page.v157_recovery_button.isEnabled():
        page.v157_autosave_label.setText("Backup anterior disponível para recuperação")


def _attach_history_stack(page, stack) -> None:
    if stack is None:
        return
    attached = getattr(page, "_v157_attached_history_stacks", set())
    if id(stack) in attached:
        return
    stack.indexChanged.connect(lambda *_args: _schedule_autosave(page))
    attached.add(id(stack))
    page._v157_attached_history_stacks = attached


def enhance_art_studio_page_v157(page) -> None:
    if getattr(page, "_v157_installed", False):
        return
    page._v157_installed = True
    page._v157_restoring = False
    page._v157_document_dirty = False
    page._v157_attached_history_stacks = set()
    page._v157_autosave_timer = QTimer(page)
    page._v157_autosave_timer.setSingleShot(True)
    page._v157_autosave_timer.timeout.connect(lambda: _perform_autosave(page))

    # A cena cobre arraste, edição inline, inclusão e remoção; o histórico
    # cobre comandos que alteram propriedades sem emitir scene.changed.
    page.scene.changed.connect(lambda *_args: _schedule_autosave(page))
    pages_bar = getattr(page, "v150_pages_bar", None)
    tab_bar = getattr(page, "v150_tab_bar", None)
    if pages_bar is not None:
        for button_name in (
            "v150_add_page_button",
            "v150_duplicate_page_button",
            "v150_rename_page_button",
        ):
            button = getattr(page, button_name, None)
            if button is not None:
                button.clicked.connect(
                    lambda _checked=False: QTimer.singleShot(0, lambda: _schedule_autosave(page))
                )
    if tab_bar is not None:
        tab_bar.currentChanged.connect(
            lambda *_args: QTimer.singleShot(0, lambda: _schedule_autosave(page))
        )
        tab_bar.tabMoved.connect(
            lambda *_args: QTimer.singleShot(0, lambda: _schedule_autosave(page))
        )
        tab_bar.tabCloseRequested.connect(
            lambda *_args: QTimer.singleShot(0, lambda: _schedule_autosave(page))
        )
    history_timer = getattr(page, "_v145_history_timer", None)
    if history_timer is not None:
        history_timer.timeout.connect(lambda: _schedule_autosave(page))
    _attach_history_stack(page, getattr(page, "_v145_history", None))

    project_changed = getattr(page, "project_changed", None)
    if project_changed is not None and hasattr(project_changed, "connect"):
        project_changed.connect(lambda *_args: _clear_recovery(page))

    _install_autosave_toolbar(page)


def install_art_studio_v157() -> None:
    """Instala autosave após a V156 e acompanha os históricos de novas páginas."""
    from monitor_noticias.ui import art_studio_v150 as v150_module
    from monitor_noticias.ui.main_window import MainWindow

    if not getattr(v150_module, "_v157_history_hook_installed", False):
        original_activate = v150_module._activate_page_history

        def activate_with_autosave(page, entry):
            original_activate(page, entry)
            if getattr(page, "_v157_installed", False):
                _attach_history_stack(page, page._v145_history)

        v150_module._activate_page_history = activate_with_autosave

        original_new = v150_module._new_project
        original_open = v150_module._open_project

        def new_project_with_recovery_cleanup(page, *args, **kwargs):
            before = _page_signature(page)
            result = original_new(page, *args, **kwargs)
            if _page_signature(page) != before:
                _clear_recovery(page)
            return result

        def open_project_with_recovery_cleanup(page, *args, **kwargs):
            before = _page_signature(page)
            result = original_open(page, *args, **kwargs)
            if _page_signature(page) != before:
                _clear_recovery(page)
            return result

        v150_module._new_project = new_project_with_recovery_cleanup
        v150_module._open_project = open_project_with_recovery_cleanup
        v150_module._v157_history_hook_installed = True

    if getattr(MainWindow, "_v157_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v157(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v157(page)

    MainWindow.__init__ = init_with_v157
    MainWindow._v157_integration_installed = True
