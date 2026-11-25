from __future__ import annotations

"""V155 — transações de inserção não destrutivas e recuperação de camadas.

Substitui a cadeia de wrappers de criação V148/V153 por uma inserção transacional:
1) serializa as camadas existentes antes de inserir;
2) usa diretamente o método-base da ArtStudioPage;
3) confere os identificadores das camadas depois da inserção;
4) restaura qualquer camada ausente a partir do snapshot serializado;
5) cancela a nova inserção se não conseguir restaurar o conteúdo anterior.

Também procura uma posição livre no canvas e, quando não existe espaço sem
sobreposição, deixa a nova camada atrás das camadas que já estavam no local.
Inclui recuperação manual do snapshot anterior à última inserção.
Não altera o formato .centralart nem acrescenta dependências.
"""

from copy import deepcopy
import logging
import math
import uuid

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from monitor_noticias.ui.art_studio_page import (
    ArtStudioPage,
    CANVAS_BG_KEY,
    ITEM_KIND_KEY,
    ITEM_NAME_KEY,
)
from monitor_noticias.ui.art_studio_v145 import HISTORY_ID_KEY
from monitor_noticias.ui.art_studio_v147 import _promote_text_item

log = logging.getLogger(__name__)


def _active_page_id(page) -> str | None:
    pages = getattr(page, "_v150_pages", None)
    index = getattr(page, "_v150_active_index", 0)
    if not pages or not 0 <= index < len(pages):
        return None
    return str(pages[index].get("id") or "") or None


def _top_level_objects(page) -> list:
    try:
        return [
            item for item in page._content_items()
            if item.parentItem() is None
            and item.data(ITEM_KIND_KEY) != CANVAS_BG_KEY
        ]
    except Exception:
        log.exception("Não foi possível enumerar as camadas do Estúdio")
        return []


def _identity(item) -> str:
    value = item.data(HISTORY_ID_KEY)
    if not value:
        value = uuid.uuid4().hex
        item.setData(HISTORY_ID_KEY, value)
    return str(value)


def _capture_scene(page) -> list[dict]:
    """Captura snapshots independentes dos objetos antes da inserção."""
    snapshots: list[dict] = []
    for item in _top_level_objects(page):
        identity = _identity(item)
        try:
            data = deepcopy(page._serialize_item(item))
        except Exception as exc:
            raise RuntimeError(
                f"A camada '{item.data(ITEM_NAME_KEY) or 'Objeto'}' não pôde ser protegida: {exc}"
            ) from exc
        data["history_id"] = identity
        snapshots.append(data)
    return snapshots


def _scene_identity_map(page) -> dict[str, object]:
    result: dict[str, object] = {}
    for item in _top_level_objects(page):
        try:
            result[_identity(item)] = item
        except RuntimeError:
            continue
    return result


def _restore_missing(page, snapshots: list[dict]) -> tuple[int, list[str]]:
    """Reconstrói objetos ausentes sem depender de wrappers C++ antigos."""
    present = _scene_identity_map(page)
    restored = 0
    failures: list[str] = []
    for data in snapshots:
        identity = str(data.get("history_id") or "")
        if not identity or identity in present:
            continue
        try:
            item = page._build_item_from_data(deepcopy(data))
            item.setData(HISTORY_ID_KEY, identity)
            if item.data(ITEM_KIND_KEY) is None:
                item.setData(ITEM_KIND_KEY, data.get("kind", "object"))
            page.scene.addItem(item)
            # O construtor de texto antigo pode não receber a referência da página.
            if hasattr(item, "_v148_page"):
                item._v148_page = page
            present[identity] = item
            restored += 1
        except Exception as exc:
            failures.append(str(data.get("name") or identity))
            log.exception("Falha ao recuperar a camada %s", data.get("name") or identity)
    return restored, failures


def _move_scene_delta(item, dx: float, dy: float) -> None:
    parent = item.parentItem()
    delta = QPointF(float(dx), float(dy))
    if parent is None:
        item.setPos(item.pos() + delta)
        return
    origin = parent.mapFromScene(QPointF(0.0, 0.0))
    target = parent.mapFromScene(delta)
    item.setPos(item.pos() + (target - origin))


def _intersection_area(first: QRectF, second: QRectF) -> float:
    intersection = first.intersected(second)
    if intersection.isEmpty():
        return 0.0
    return max(0.0, intersection.width()) * max(0.0, intersection.height())


def _candidate_axis_positions(start: float, end: float, size: float, existing, axis: str) -> list[float]:
    padding = 12.0
    low = start + padding
    high = end - size - padding
    if high < low:
        return [start + (end - start - size) / 2.0]

    values = {low, high, (low + high) / 2.0}
    # Varredura de 17 posições cobre áreas livres que a amostragem antiga 4x4
    # não alcançava. Os limites dos objetos acrescentam posições adjacentes.
    for step in range(17):
        values.add(low + (high - low) * step / 16.0)
    gap = 16.0
    for rect in existing:
        if axis == "x":
            proposed = (rect.left() - size - gap, rect.right() + gap, rect.center().x() - size / 2.0)
        else:
            proposed = (rect.top() - size - gap, rect.bottom() + gap, rect.center().y() - size / 2.0)
        for value in proposed:
            values.add(max(low, min(high, float(value))))
    return sorted(values)


def _place_new_object(page, item, previous_ids: set[str]) -> str:
    """Procura área livre; se não houver, preserva a visibilidade das camadas antigas."""
    if item.scene() is not page.scene or item.parentItem() is not None:
        return ""

    canvas = page.scene.sceneRect()
    original = item.sceneBoundingRect()
    width = max(1.0, original.width())
    height = max(1.0, original.height())
    old_x, old_y = original.left(), original.top()

    current = _scene_identity_map(page)
    previous = [
        other for identity, other in current.items()
        if identity in previous_ids and other is not item and other.isVisible()
    ]
    existing_rects = [(other, other.sceneBoundingRect()) for other in previous]

    x_values = _candidate_axis_positions(canvas.left(), canvas.right(), width, [r for _, r in existing_rects], "x")
    y_values = _candidate_axis_positions(canvas.top(), canvas.bottom(), height, [r for _, r in existing_rects], "y")

    area = max(1.0, width * height)
    best_score = math.inf
    best_rect = QRectF(old_x, old_y, width, height)
    best_overlap: list[object] = []
    best_outside = area

    for x in x_values:
        for y in y_values:
            candidate = QRectF(float(x), float(y), width, height)
            inside = _intersection_area(candidate, canvas)
            outside = max(0.0, area - inside)
            overlaps: list[object] = []
            overlap_area = 0.0
            for other, other_rect in existing_rects:
                amount = _intersection_area(candidate, other_rect)
                if amount > 1.0:
                    overlap_area += amount
                    overlaps.append(other)
            distance = math.hypot(float(x) - old_x, float(y) - old_y)
            # Prioridade absoluta: caber no canvas, evitar cobrir camadas antigas,
            # só então minimizar a distância em relação à posição inicial.
            score = outside * 1_000_000_000.0 + overlap_area * 100_000.0 + distance
            if score < best_score:
                best_score = score
                best_rect = candidate
                best_overlap = overlaps
                best_outside = outside

    dx = best_rect.left() - old_x
    dy = best_rect.top() - old_y
    if abs(dx) > 0.01 or abs(dy) > 0.01:
        _move_scene_delta(item, dx, dy)

    if best_overlap:
        lower_z = min(float(other.zValue()) for other in best_overlap)
        item.setZValue(min(float(item.zValue()), lower_z - 0.01))
        return "overlap"
    if best_outside > 1.0:
        return "outside"
    if abs(dx) > 0.01 or abs(dy) > 0.01:
        return "moved"
    return "free"


def _schedule_history(page) -> None:
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None and not getattr(page, "_v145_history_suspended", False):
        timer.start()


def _refresh_after_insert(page, item, restored: int, placement: str) -> None:
    if hasattr(page, "_refresh_layers"):
        page._refresh_layers(select_item=item)
    if hasattr(page, "_update_selection_controls"):
        page._update_selection_controls(item)
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()
    if hasattr(page, "_v148_update_dimensions"):
        page._v148_update_dimensions()
    if hasattr(page, "_v149_sync_controls"):
        page._v149_sync_controls()
    if hasattr(page, "_v154_layer_selection"):
        page._v154_layer_selection = [item]
    _schedule_history(page)

    if restored:
        message = f"Objeto inserido. {restored} camada(s) anterior(es) foram recuperadas automaticamente."
    elif placement == "overlap":
        message = (
            "As camadas anteriores foram preservadas. Como não havia espaço livre, "
            "o novo objeto ficou atrás das camadas sobrepostas; selecione-o no painel para trazê-lo à frente."
        )
    elif placement == "moved":
        message = "Objeto inserido em uma área livre para manter os elementos anteriores visíveis."
    elif placement == "outside":
        message = "Objeto maior que a área disponível; as camadas anteriores foram mantidas à frente."
    else:
        message = "Objeto inserido. As camadas anteriores foram preservadas."
    page.status_label.setText(message)


def _transactional_make_movable(page, item, kind: str, name: str):
    """Inserção transacional. Não chama os wrappers antigos V148/V153."""
    if kind == "text":
        item = _promote_text_item(item)

    try:
        snapshots = _capture_scene(page)
    except Exception as exc:
        page.status_label.setText(
            f"Inserção cancelada para proteger a arte existente: {exc}"
        )
        log.exception("A inserção foi cancelada porque não foi possível proteger as camadas")
        return None

    previous_ids = {str(data.get("history_id") or "") for data in snapshots}
    page._v155_last_safe_snapshot = deepcopy(snapshots)
    page._v155_recovery_page_id = _active_page_id(page)

    try:
        # Chama o método original da classe, ignorando as cadeias de wrappers
        # antigas que tentavam restaurar objetos por referências Qt temporárias.
        ArtStudioPage._make_movable(page, item, kind, name)
        new_identity = _identity(item)
        restored, failures = _restore_missing(page, snapshots)
        current_ids = set(_scene_identity_map(page))
        missing = previous_ids - current_ids
        if missing or failures:
            # Segunda tentativa após sincronizar a cena. Se qualquer camada
            # continuar ausente, remove apenas o objeto novo e falha de forma segura.
            more_restored, more_failures = _restore_missing(page, snapshots)
            restored += more_restored
            failures = more_failures
            current_ids = set(_scene_identity_map(page))
            missing = previous_ids - current_ids
            if missing or failures:
                if item.scene() is page.scene:
                    page.scene.removeItem(item)
                raise RuntimeError(
                    f"{len(missing)} camada(s) anterior(es) não puderam ser recuperadas. "
                    "A nova inserção foi cancelada para evitar perda de conteúdo."
                )

        placement = _place_new_object(page, item, previous_ids)
        item.setData(HISTORY_ID_KEY, new_identity)
        _refresh_after_insert(page, item, restored, placement)
        integrity_label = getattr(page, "v155_integrity_label", None)
        if integrity_label is not None:
            integrity_label.setText(
                f"Camadas atuais: {len(_top_level_objects(page))} · "
                f"Proteção da última inserção: {len(snapshots)} camada(s)"
            )
        return item
    except Exception as exc:
        try:
            if item.scene() is page.scene:
                page.scene.removeItem(item)
        except RuntimeError:
            pass
        try:
            _restore_missing(page, snapshots)
            page._refresh_layers()
        except Exception:
            log.exception("Falha na recuperação após erro de inserção")
        page.status_label.setText(
            f"Nova inserção cancelada para preservar as camadas anteriores: {exc}"
        )
        log.exception("Falha na inserção transacional de objeto")
        return None


def _recovery_candidates(page) -> list[dict]:
    if getattr(page, "_v155_recovery_page_id", None) != _active_page_id(page):
        return []
    snapshots = getattr(page, "_v155_last_safe_snapshot", None) or []
    present = set(_scene_identity_map(page))
    return [
        data for data in snapshots
        if str(data.get("history_id") or "") not in present
    ]


def _recover_previous_layers(page) -> None:
    snapshots = getattr(page, "_v155_last_safe_snapshot", None) or []
    if not snapshots or getattr(page, "_v155_recovery_page_id", None) != _active_page_id(page):
        QMessageBox.information(
            page,
            "Recuperação de camadas",
            "Não existe um ponto de recuperação da página atual. Ele é criado automaticamente antes de cada nova inserção.",
        )
        return

    missing = _recovery_candidates(page)
    if not missing:
        QMessageBox.information(
            page,
            "Verificação concluída",
            f"Nenhuma camada anterior está ausente. As {len(snapshots)} camada(s) protegida(s) continuam presentes.",
        )
        return

    answer = QMessageBox.question(
        page,
        "Recuperar camadas anteriores",
        f"Foram encontradas {len(missing)} camada(s) ausente(s) do ponto de recuperação da última inserção. Deseja restaurá-las?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return

    restored, failures = _restore_missing(page, snapshots)
    page._refresh_layers()
    _schedule_history(page)
    if failures:
        QMessageBox.warning(
            page,
            "Recuperação parcial",
            f"{restored} camada(s) recuperada(s). Não foi possível reconstruir: {', '.join(failures)}",
        )
    else:
        QMessageBox.information(
            page,
            "Camadas recuperadas",
            f"{restored} camada(s) restaurada(s) com sucesso.",
        )
    page.v155_integrity_label.setText(
        f"Camadas atuais: {len(_top_level_objects(page))} · Proteção: {len(snapshots)}"
    )


def _install_integrity_panel(page) -> None:
    scroll = page.findChild(QScrollArea, "artStudioLayersScroll")
    content = scroll.widget() if scroll is not None else None
    layout = content.layout() if content is not None else None
    if layout is None:
        return

    panel = QFrame(content)
    panel.setObjectName("artStudioIntegrityPanelV155")
    box = QVBoxLayout(panel)
    box.setContentsMargins(8, 8, 8, 8)
    box.setSpacing(5)

    title = QLabel("PROTEÇÃO DE CAMADAS")
    title.setObjectName("artSmallLabel")
    box.addWidget(title)

    page.v155_integrity_label = QLabel("Camadas atuais: 0 · proteção ativa antes de cada inserção")
    page.v155_integrity_label.setObjectName("muted")
    page.v155_integrity_label.setWordWrap(True)
    box.addWidget(page.v155_integrity_label)

    button = QPushButton("Verificar / recuperar camadas")
    button.setProperty("secondary", True)
    button.setMinimumHeight(32)
    button.setToolTip(
        "Verifica as camadas existentes antes da última inserção e recupera as que estiverem ausentes."
    )
    button.clicked.connect(lambda: _recover_previous_layers(page))
    box.addWidget(button)
    page.v155_recovery_button = button

    layer_index = layout.indexOf(page.layers)
    layout.insertWidget(layer_index + 1 if layer_index >= 0 else layout.count(), panel)
    page.v155_integrity_panel = panel


def enhance_art_studio_page_v155(page) -> None:
    if getattr(page, "_v155_installed", False):
        return
    page._v155_installed = True

    # Substitui a cadeia de criação V148/V153 por uma única transação verificável.
    page._make_movable = lambda item, kind, name: _transactional_make_movable(
        page, item, kind, name
    )
    page._v155_last_safe_snapshot = None
    page._v155_recovery_page_id = None
    _install_integrity_panel(page)

    page.status_label.setText(
        "V155: inserção transacional de objetos, verificação de integridade, recuperação de camadas e posicionamento que evita ocultar elementos anteriores."
    )


def install_art_studio_v155() -> None:
    """Instala V155 após a inicialização das camadas V148–V154."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v155_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v155(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v155(page)

    MainWindow.__init__ = init_with_v155
    MainWindow._v155_integration_installed = True
