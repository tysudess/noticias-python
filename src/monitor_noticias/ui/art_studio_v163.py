from __future__ import annotations

"""V163 — biblioteca profissional de componentes gráficos editáveis.

Acrescenta uma biblioteca pesquisável de blocos vetoriais prontos para uso.
Cada bloco é composto exclusivamente por texto, retângulos e elipses já
suportados pelo serializador de grupos do Estúdio. A inserção usa o mecanismo
transacional V155, histórico e autosave V157, sem alterar o formato .centralart.
"""

from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsRectItem,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.art_studio_page import ITEM_KIND_KEY, ITEM_NAME_KEY
from monitor_noticias.ui.art_studio_v147 import InlineTextItem
from monitor_noticias.ui.art_studio_v150 import MAX_ITEMS_PER_PAGE
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave


@dataclass(frozen=True)
class _Element:
    kind: str
    x: float
    y: float
    width: float
    height: float
    value: str
    color: str
    font_size: int = 0
    bold: bool = False


@dataclass(frozen=True)
class _Template:
    key: str
    title: str
    category: str
    icon: str
    description: str
    width: int
    height: int
    elements: tuple[_Element, ...]


PALETTES: dict[str, dict[str, str]] = {
    "institucional": {
        "primary": "#102A43", "accent": "#D6B66D", "secondary": "#315B78",
        "surface": "#F1F5F8", "ink": "#17344A", "muted": "#AFC3D2",
        "white": "#FFFFFF", "danger": "#8C2735",
    },
    "oceano": {
        "primary": "#0E4D64", "accent": "#3AAFA9", "secondary": "#28758B",
        "surface": "#EAF6F5", "ink": "#123B4B", "muted": "#5C858C",
        "white": "#FFFFFF", "danger": "#9C3B3B",
    },
    "urgente": {
        "primary": "#8C1C13", "accent": "#F2C14E", "secondary": "#C44B32",
        "surface": "#FFF4E8", "ink": "#54221C", "muted": "#A66C52",
        "white": "#FFFFFF", "danger": "#8C1C13",
    },
    "neutro": {
        "primary": "#293241", "accent": "#98C1D9", "secondary": "#3D5A80",
        "surface": "#F4F1DE", "ink": "#293241", "muted": "#64748B",
        "white": "#FFFFFF", "danger": "#9B2226",
    },
}


def _r(x: float, y: float, width: float, height: float, color: str) -> _Element:
    return _Element("rect", x, y, width, height, "", color)


def _e(x: float, y: float, width: float, height: float, color: str) -> _Element:
    return _Element("ellipse", x, y, width, height, "", color)


def _t(
    x: float,
    y: float,
    width: float,
    height: float,
    value: str,
    color: str,
    font_size: int,
    bold: bool = False,
) -> _Element:
    return _Element("text", x, y, width, height, value, color, font_size, bold)


TEMPLATES: tuple[_Template, ...] = (
    _Template(
        "lower-third", "Tarja de notícia", "Notícias", "▰",
        "Tarja de vídeo com selo, manchete e linha fina.", 920, 190,
        (
            _r(0, 0, 920, 190, "primary"), _r(0, 0, 15, 190, "accent"),
            _t(48, 24, 820, 28, "ÚLTIMA HORA", "accent", 19, True),
            _t(48, 61, 830, 58, "TÍTULO DA NOTÍCIA", "white", 42, True),
            _t(50, 130, 820, 34, "Linha fina ou resumo da informação", "muted", 22, False),
        ),
    ),
    _Template(
        "info-card", "Card informativo", "Informativos", "▤",
        "Card completo para explicar um assunto ou apresentar uma informação.", 720, 480,
        (
            _r(0, 0, 720, 480, "surface"), _r(0, 0, 720, 14, "accent"),
            _t(48, 48, 620, 28, "INFORMAÇÃO", "secondary", 19, True),
            _t(48, 102, 620, 64, "Título do conteúdo", "primary", 43, True),
            _t(50, 192, 610, 112, "Escreva aqui uma explicação breve com os principais dados e contexto.", "ink", 25, False),
            _r(48, 374, 250, 62, "primary"),
            _t(72, 390, 210, 32, "SAIBA MAIS", "white", 21, True),
        ),
    ),
    _Template(
        "quote-card", "Cartão de citação", "Informativos", "❞",
        "Composição de citação com autoria ou fonte em destaque.", 760, 420,
        (
            _r(0, 0, 760, 420, "primary"), _r(0, 0, 12, 420, "accent"),
            _t(52, 18, 100, 110, "“", "accent", 104, True),
            _t(76, 116, 620, 150, "Escreva aqui uma frase ou declaração importante.", "white", 34, True),
            _r(76, 326, 78, 5, "accent"),
            _t(76, 350, 610, 32, "NOME / FONTE DA CITAÇÃO", "accent", 18, True),
        ),
    ),
    _Template(
        "stat-card", "Indicador numérico", "Informativos", "％",
        "Card de estatística com número, descrição e contexto.", 520, 340,
        (
            _r(0, 0, 520, 340, "surface"), _r(0, 0, 520, 13, "accent"),
            _t(42, 64, 440, 110, "85%", "primary", 82, True),
            _t(46, 192, 430, 40, "INDICADOR EM DESTAQUE", "secondary", 21, True),
            _t(46, 248, 430, 58, "Descreva o dado e seu significado.", "ink", 18, False),
        ),
    ),
    _Template(
        "urgent-alert", "Alerta de destaque", "Notícias", "⚠",
        "Bloco de alerta para avisos e informações prioritárias.", 760, 220,
        (
            _r(0, 0, 760, 220, "danger"), _r(0, 0, 14, 220, "accent"),
            _t(48, 25, 650, 28, "ATENÇÃO", "white", 19, True),
            _t(48, 68, 660, 58, "TÍTULO DO AVISO", "white", 39, True),
            _t(50, 145, 650, 42, "Inclua uma orientação ou informação complementar.", "accent", 19, False),
        ),
    ),
    _Template(
        "agenda-card", "Agenda e evento", "Informativos", "▦",
        "Card para evento, agenda, prazo ou compromisso.", 720, 380,
        (
            _r(0, 0, 720, 380, "surface"), _r(0, 0, 190, 380, "primary"),
            _t(30, 102, 130, 95, "26", "white", 76, True),
            _t(48, 215, 100, 38, "NOV", "accent", 26, True),
            _t(232, 54, 440, 58, "NOME DO EVENTO", "primary", 35, True),
            _t(234, 135, 430, 95, "Horário, local e informações principais do compromisso.", "ink", 22, False),
            _r(234, 280, 80, 5, "accent"),
            _t(234, 305, 420, 30, "DATA  ·  HORÁRIO  ·  LOCAL", "secondary", 17, True),
        ),
    ),
    _Template(
        "comparison", "Comparativo duplo", "Informativos", "⇄",
        "Dois blocos lado a lado para comparação de dados ou cenários.", 900, 360,
        (
            _r(0, 0, 900, 360, "surface"),
            _r(0, 0, 438, 360, "primary"), _r(462, 0, 438, 360, "secondary"),
            _t(38, 42, 360, 32, "CENÁRIO A", "accent", 20, True),
            _t(38, 102, 360, 72, "DADO PRINCIPAL", "white", 36, True),
            _t(38, 204, 360, 95, "Explique o primeiro cenário ou resultado.", "white", 20, False),
            _t(500, 42, 360, 32, "CENÁRIO B", "white", 20, True),
            _t(500, 102, 360, 72, "DADO PRINCIPAL", "white", 36, True),
            _t(500, 204, 360, 95, "Explique o segundo cenário ou resultado.", "white", 20, False),
        ),
    ),
    _Template(
        "cta-button", "Botão de chamada", "Elementos", "➜",
        "Botão gráfico para chamadas, links ou ações em uma peça.", 480, 130,
        (
            _r(0, 0, 480, 130, "accent"),
            _t(52, 37, 370, 54, "SAIBA MAIS", "primary", 35, True),
        ),
    ),
    _Template(
        "official-seal", "Selo de destaque", "Elementos", "✦",
        "Selo circular para marcar conteúdo, edição especial ou prioridade.", 300, 300,
        (
            _e(0, 0, 300, 300, "primary"), _e(16, 16, 268, 268, "accent"),
            _e(28, 28, 244, 244, "primary"),
            _t(58, 92, 185, 42, "SELO", "accent", 29, True),
            _t(48, 145, 205, 62, "ESPECIAL", "white", 34, True),
        ),
    ),
    _Template(
        "source-line", "Crédito e fonte", "Elementos", "≡",
        "Identificação de fonte, autoria, crédito ou referência.", 800, 120,
        (
            _r(0, 0, 800, 120, "surface"), _r(0, 0, 9, 120, "accent"),
            _t(36, 24, 720, 30, "FONTE / CRÉDITO", "secondary", 18, True),
            _t(36, 62, 720, 35, "Nome da publicação · autoria · data", "ink", 20, False),
        ),
    ),
    _Template(
        "report-cover", "Capa de relatório", "Informativos", "▧",
        "Abertura editorial para relatório, apresentação ou documento.", 800, 560,
        (
            _r(0, 0, 800, 560, "primary"), _r(0, 0, 800, 18, "accent"),
            _r(54, 92, 96, 7, "accent"),
            _t(54, 128, 690, 38, "RELATÓRIO  ·  2026", "accent", 22, True),
            _t(54, 202, 700, 142, "TÍTULO PRINCIPAL DO DOCUMENTO", "white", 48, True),
            _t(56, 382, 680, 64, "Subtítulo, unidade responsável ou descrição do conteúdo.", "muted", 23, False),
            _t(56, 492, 670, 28, "UNIDADE / ORGANIZAÇÃO  ·  DATA", "accent", 17, True),
        ),
    ),
    _Template(
        "three-points", "Três pontos", "Informativos", "☷",
        "Três colunas para etapas, vantagens, resultados ou recomendações.", 900, 400,
        (
            _r(0, 0, 900, 400, "surface"), _r(0, 0, 900, 14, "primary"),
            _t(42, 38, 810, 46, "TRÊS PONTOS PRINCIPAIS", "primary", 31, True),
            _e(50, 142, 76, 76, "accent"), _e(335, 142, 76, 76, "accent"), _e(620, 142, 76, 76, "accent"),
            _t(75, 160, 30, 34, "1", "primary", 27, True),
            _t(360, 160, 30, 34, "2", "primary", 27, True),
            _t(645, 160, 30, 34, "3", "primary", 27, True),
            _t(40, 248, 230, 44, "PRIMEIRO", "secondary", 20, True),
            _t(40, 288, 235, 75, "Descreva o primeiro ponto.", "ink", 17, False),
            _t(325, 248, 230, 44, "SEGUNDO", "secondary", 20, True),
            _t(325, 288, 235, 75, "Descreva o segundo ponto.", "ink", 17, False),
            _t(610, 248, 230, 44, "TERCEIRO", "secondary", 20, True),
            _t(610, 288, 235, 75, "Descreva o terceiro ponto.", "ink", 17, False),
        ),
    ),
    _Template(
        "section-banner", "Faixa de seção", "Elementos", "━",
        "Faixa horizontal para dividir ou identificar uma seção.", 820, 150,
        (
            _r(0, 0, 820, 150, "secondary"), _r(0, 0, 12, 150, "accent"),
            _t(48, 34, 720, 42, "TÍTULO DA SEÇÃO", "white", 34, True),
            _t(50, 88, 710, 30, "Descrição curta ou identificação complementar", "white", 18, False),
        ),
    ),
)


def _build_group(page, template: _Template, palette: dict[str, str]) -> QGraphicsItemGroup:
    children: list[QGraphicsItem] = []
    try:
        for index, element in enumerate(template.elements, start=1):
            color = QColor(palette[element.color])
            if element.kind == "rect":
                item: QGraphicsItem = QGraphicsRectItem(
                    QRectF(element.x, element.y, element.width, element.height)
                )
                item.setBrush(QBrush(color))
                item.setPen(QPen(Qt.PenStyle.NoPen))
                item.setData(ITEM_KIND_KEY, "shape")
                item.setData(ITEM_NAME_KEY, f"{template.title} · forma {index}")
            elif element.kind == "ellipse":
                item = QGraphicsEllipseItem(
                    QRectF(element.x, element.y, element.width, element.height)
                )
                item.setBrush(QBrush(color))
                item.setPen(QPen(Qt.PenStyle.NoPen))
                item.setData(ITEM_KIND_KEY, "shape")
                item.setData(ITEM_NAME_KEY, f"{template.title} · círculo {index}")
            elif element.kind == "text":
                item = InlineTextItem(element.value)
                item._v148_page = page
                item.setFont(_font(element.font_size, element.bold))
                item.setDefaultTextColor(color)
                item.setTextWidth(element.width)
                item.setData(ITEM_KIND_KEY, "text")
                item.setData(ITEM_NAME_KEY, f"{template.title} · texto {index}")
                item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
                item.setPos(element.x, element.y)
            else:
                raise ValueError(f"Componente gráfico não suportado: {element.kind}")

            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
            if element.kind != "text":
                item.setPos(element.x, element.y)
            page.scene.addItem(item)
            children.append(item)

        group = page.scene.createItemGroup(children)
        group.setData(ITEM_KIND_KEY, "group")
        group.setData(ITEM_NAME_KEY, template.title)
        group.setTransformOriginPoint(group.boundingRect().center())
        group.setPos(
            (float(page._width) - group.boundingRect().width()) / 2.0,
            (float(page._height) - group.boundingRect().height()) / 2.0,
        )
        return group
    except Exception:
        for item in children:
            try:
                if item.scene() is page.scene:
                    page.scene.removeItem(item)
            except RuntimeError:
                pass
        raise


def _font(pixel_size: int, bold: bool) -> QFont:
    font = QFont("Segoe UI")
    font.setPixelSize(max(8, int(pixel_size)))
    font.setBold(bool(bold))
    return font


def _insert_template(page, key: str) -> None:
    template = next((item for item in TEMPLATES if item.key == key), None)
    if template is None:
        page.status_label.setText("O componente selecionado não está disponível.")
        return
    try:
        current_count = len(page._content_items())
    except Exception:
        current_count = 0
    if current_count >= MAX_ITEMS_PER_PAGE:
        page.status_label.setText(
            f"Limite de {MAX_ITEMS_PER_PAGE} objetos por página atingido."
        )
        return

    palette_key = str(page.v163_palette_combo.currentData() or "institucional")
    palette = PALETTES.get(palette_key, PALETTES["institucional"])
    group = None
    try:
        group = _build_group(page, template, palette)
        inserted = page._make_movable(group, "group", template.title)
        if inserted is None:
            page.status_label.setText(
                "A inserção foi cancelada para proteger as camadas existentes."
            )
            return
        if hasattr(page, "_v148_sync_handles"):
            page._v148_sync_handles()
        _schedule_autosave(page)
        page.status_label.setText(
            f"{template.title} inserido. Desagrupe para editar textos e formas separadamente."
        )
    except Exception as exc:
        if group is not None:
            try:
                if group.scene() is page.scene:
                    page.scene.removeItem(group)
            except RuntimeError:
                pass
        page.status_label.setText(f"Não foi possível inserir o componente: {exc}")


def _refresh_template_cards(page) -> None:
    query = page.v163_search.text().strip().casefold()
    category = str(page.v163_category_combo.currentData() or "all")
    visible = 0
    for button in page.v163_template_buttons:
        key = str(button.property("templateKey") or "")
        template = next((item for item in TEMPLATES if item.key == key), None)
        if template is None:
            button.hide()
            continue
        matches_query = not query or query in (
            template.title + " " + template.description + " " + template.category
        ).casefold()
        matches_category = category == "all" or template.category == category
        button.setVisible(matches_query and matches_category)
        visible += int(matches_query and matches_category)
    page.v163_results_label.setText(
        f"{visible} componente(s) disponível(is)"
        if visible else "Nenhum componente corresponde à busca."
    )


def _restyle_template_cards(page) -> None:
    palette_key = str(page.v163_palette_combo.currentData() or "institucional")
    palette = PALETTES.get(palette_key, PALETTES["institucional"])
    for button in getattr(page, "v163_template_buttons", []):
        button.setStyleSheet(
            "QPushButton#artStudioTemplateCardV163 {"
            f"background:{palette['surface']};color:{palette['ink']};"
            f"border:1px solid {palette['secondary']};border-left:4px solid {palette['accent']};"
            "border-radius:8px;text-align:left;padding:7px 10px;font-size:10px;font-weight:800;}"
            "QPushButton#artStudioTemplateCardV163:hover {"
            f"background:{palette['white']};border:1px solid {palette['accent']};border-left:4px solid {palette['accent']};}}"
        )


def _install_component_library(page) -> None:
    if getattr(page, "_v163_library_installed", False):
        return
    tabs = getattr(page, "_v161_left_tabs", None)
    if tabs is None or tabs.count() < 1:
        return
    insert_page = tabs.widget(0)
    layout = insert_page.layout() if insert_page is not None else None
    if layout is None:
        return

    panel = QFrame(insert_page)
    panel.setObjectName("artStudioComponentLibraryV163")
    box = QVBoxLayout(panel)
    box.setContentsMargins(9, 10, 9, 10)
    box.setSpacing(7)

    title = QLabel("BIBLIOTECA DE COMPONENTES", panel)
    title.setObjectName("artSmallLabel")
    box.addWidget(title)

    hint = QLabel(
        "Blocos editáveis para acelerar a criação. Insira e desagrupe para personalizar cada parte.",
        panel,
    )
    hint.setObjectName("artStudioSectionHint")
    hint.setWordWrap(True)
    box.addWidget(hint)

    page.v163_search = QLineEdit(panel)
    page.v163_search.setObjectName("artStudioComponentSearchV163")
    page.v163_search.setPlaceholderText("⌕  Buscar componente…")
    page.v163_search.setClearButtonEnabled(True)
    page.v163_search.setToolTip("Filtra a biblioteca pelo nome, categoria ou descrição.")
    box.addWidget(page.v163_search)

    page.v163_category_combo = QComboBox(panel)
    page.v163_category_combo.setObjectName("artStudioComponentCategoryV163")
    page.v163_category_combo.addItem("Todas as categorias", "all")
    for category in ("Notícias", "Informativos", "Elementos"):
        page.v163_category_combo.addItem(category, category)
    box.addWidget(page.v163_category_combo)

    page.v163_palette_combo = QComboBox(panel)
    page.v163_palette_combo.setObjectName("artStudioComponentPaletteV163")
    page.v163_palette_combo.addItem("Paleta institucional · Marinho e dourado", "institucional")
    page.v163_palette_combo.addItem("Paleta oceano · Azul e turquesa", "oceano")
    page.v163_palette_combo.addItem("Paleta urgente · Vermelho e âmbar", "urgente")
    page.v163_palette_combo.addItem("Paleta neutra · Grafite e azul", "neutro")
    page.v163_palette_combo.setToolTip("Escolha as cores usadas nos próximos componentes inseridos.")
    box.addWidget(page.v163_palette_combo)

    page.v163_template_buttons = []
    grid = QGridLayout()
    grid.setContentsMargins(0, 2, 0, 0)
    grid.setHorizontalSpacing(5)
    grid.setVerticalSpacing(5)
    for index, template in enumerate(TEMPLATES):
        button = QPushButton(f"{template.icon}  {template.title}", panel)
        button.setObjectName("artStudioTemplateCardV163")
        button.setProperty("templateKey", template.key)
        button.setProperty("secondary", True)
        button.setMinimumHeight(38)
        button.setToolTip(
            f"{template.description}\n\nTamanho do bloco: {template.width} × {template.height} px."
        )
        button.clicked.connect(
            lambda _checked=False, key=template.key: _insert_template(page, key)
        )
        grid.addWidget(button, index, 0)
        page.v163_template_buttons.append(button)
    box.addLayout(grid)

    page.v163_results_label = QLabel("13 componentes disponíveis", panel)
    page.v163_results_label.setObjectName("muted")
    page.v163_results_label.setWordWrap(True)
    box.addWidget(page.v163_results_label)

    page.v163_search.textChanged.connect(lambda _value: _refresh_template_cards(page))
    page.v163_category_combo.currentIndexChanged.connect(
        lambda _index: _refresh_template_cards(page)
    )
    page.v163_palette_combo.currentIndexChanged.connect(
        lambda _index: _restyle_template_cards(page)
    )
    page.v163_component_panel = panel
    page.v163_search.setMinimumHeight(32)
    page.v163_category_combo.setMinimumHeight(32)
    page.v163_palette_combo.setMinimumHeight(32)
    # A V161 já deixa um stretch ao final da página; inserir antes dele evita
    # empurrar a biblioteca para o rodapé da coluna.
    insert_at = max(0, layout.count() - 1)
    layout.insertWidget(insert_at, panel)
    page._v163_library_installed = True
    _restyle_template_cards(page)
    _refresh_template_cards(page)


def enhance_art_studio_page_v163(page) -> None:
    if getattr(page, "_v163_installed", False):
        return
    _install_component_library(page)
    if getattr(page, "_v163_library_installed", False):
        page._v163_installed = True


def install_art_studio_v163() -> None:
    """Instala a biblioteca profissional depois da V162."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v163_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v163(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v163(page)

    MainWindow.__init__ = init_with_v163
    MainWindow._v163_integration_installed = True
