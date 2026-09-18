from __future__ import annotations

V5_NAVY = "#063D78"
V5_NAVY_DARK = "#032F61"
V5_INK = "#08245F"
V5_MUTED = "#5C73A4"
V5_BG = "#F4F9FF"
V5_BORDER = "#CFE0F5"
V5_BLUE = "#087AF7"
V5_PURPLE = "#8B3CF6"
V5_ORANGE = "#F2A60C"
V5_GREEN = "#08A66B"
V5_RED = "#EA3158"
V5_GOLD = "#F4B719"
V5_SOFT_BLUE = "#EAF4FF"

APP_STYLESHEET = f"""
QMainWindow, QWidget#root {{
    background: {V5_BG};
    color: {V5_INK};
}}
QWidget {{
    font-family: "Segoe UI";
    font-size: 12px;
    color: {V5_INK};
}}

QFrame#sidebar {{
    background: #F7FBFF;
    border: 0;
    border-right: 1px solid {V5_BORDER};
}}
QFrame#sidebar[dark="true"] {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #05366F,stop:1 #064D91);
    border-right: 0;
}}
QLabel#brandTitle {{
    color: {V5_INK};
    font-size: 18px;
    font-weight: 800;
}}
QLabel#brandSub {{
    color: {V5_MUTED};
    font-size: 10px;
}}
QFrame#sidebar[dark="true"] QLabel#brandTitle {{
    color: white;
}}
QFrame#sidebar[dark="true"] QLabel#brandSub {{
    color: #D8E8FB;
}}

QPushButton#navButton {{
    color: #274879;
    text-align: left;
    border: 0;
    border-radius: 9px;
    padding: 10px 12px;
    background: transparent;
    min-height: 29px;
}}
QPushButton#navButton:hover {{
    background: #E8F3FF;
}}
QPushButton#navButton:checked {{
    color: white;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0B79F7,stop:1 #2497FF);
    font-weight: 700;
}}
QFrame#sidebar[dark="true"] QPushButton#navButton {{
    color: #E8F4FF;
}}
QFrame#sidebar[dark="true"] QPushButton#navButton:hover {{
    background: #0C5B9F;
}}
QFrame#sidebar[dark="true"] QPushButton#navButton:checked {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0A71E7,stop:1 #1097FF);
}}

QFrame#card, QFrame#topCard, QFrame#statusCard {{
    background: rgba(255,255,255,245);
    border: 1px solid {V5_BORDER};
    border-radius: 12px;
}}
QFrame#metricCard {{
    background: white;
    border: 1px solid #D6E6F7;
    border-radius: 14px;
}}
QFrame#successCard {{
    background: #ECFBF4;
    border: 1px solid #B8EBD4;
    border-radius: 12px;
}}
QFrame#dangerCard {{
    background: #FFF1F4;
    border: 1px solid #FFC9D5;
    border-radius: 12px;
}}

QLabel#pageKicker {{
    color: #087AF7;
    font-size: 10px;
    font-weight: 800;
}}
QLabel#pageTitle {{
    color: {V5_INK};
    font-size: 26px;
    font-weight: 800;
}}
QLabel#pageSubtitle {{
    color: {V5_MUTED};
    font-size: 12px;
}}
QLabel#muted {{
    color: {V5_MUTED};
}}
QLabel#sectionTitle {{
    color: #08245F;
    font-size: 16px;
    font-weight: 900;
}}
QLabel#metricValue {{
    color: #071D55;
    font-size: 28px;
    font-weight: 900;
}}
QLabel#chipGreen {{
    background: #ECFBF4;
    color: #078B5F;
    border: 1px solid #C3EFDD;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 700;
}}
QLabel#chipBlue {{
    background: #F5FAFF;
    color: #0A5BB8;
    border: 1px solid #D4E6FA;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 700;
}}
QLabel#clockCard {{
    background: white;
    border: 1px solid {V5_BORDER};
    border-radius: 12px;
    padding: 8px 14px;
    color: {V5_INK};
    font-size: 15px;
    font-weight: 800;
}}

QLineEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit {{
    background: white;
    border: 1px solid #C9DDF5;
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 26px;
    selection-background-color: #B9D9FF;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
    border: 1px solid {V5_BLUE};
}}

QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0A7BF7,stop:1 #198CFF);
    color: white;
    border: 0;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 700;
    min-height: 25px;
}}
QPushButton:hover {{
    background: #066DDF;
}}
QPushButton:disabled {{
    background: #C7D4E5;
    color: #F4F7FB;
}}
QPushButton[secondary="true"] {{
    background: white;
    color: {V5_INK};
    border: 1px solid #BED5EE;
}}
QPushButton[secondary="true"]:hover {{
    background: #F0F7FF;
    border-color: #95BFEA;
}}
QPushButton[danger="true"] {{
    background: #FFF1F4;
    color: {V5_RED};
    border: 1px solid #FFABC0;
}}
QPushButton[purple="true"] {{
    background: #F4ECFF;
    color: {V5_PURPLE};
    border: 1px solid #DFC6FF;
}}
QPushButton[orange="true"] {{
    background: #FFF4D9;
    color: #9A6300;
    border: 1px solid #FFD46E;
}}
QPushButton[green="true"] {{
    background: #E8FAF2;
    color: #04845A;
    border: 1px solid #B8EAD5;
}}
QPushButton[gold="true"] {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FFCB2D,stop:1 #FFD83D);
    color: #09245F;
    border: 1px solid #F5B914;
    font-size: 15px;
    font-weight: 900;
}}

QProgressBar {{
    border: 1px solid #C8DDF2;
    border-radius: 5px;
    background: #EAF1F9;
    text-align: center;
    min-height: 8px;
    max-height: 12px;
    color: {V5_MUTED};
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0A7CF6,stop:1 #13B6E9);
    border-radius: 4px;
}}

QListWidget, QTableWidget {{
    background: white;
    border: 1px solid {V5_BORDER};
    border-radius: 10px;
    alternate-background-color: #F8FBFF;
    gridline-color: #E7F0FA;
}}
QHeaderView::section {{
    background: #F0F7FF;
    color: {V5_INK};
    padding: 8px;
    border: 0;
    border-bottom: 1px solid {V5_BORDER};
    font-weight: 800;
}}

QTabWidget::pane {{
    border: 1px solid {V5_BORDER};
    border-radius: 10px;
    background: white;
}}
QTabBar::tab {{
    background: #F8FBFF;
    color: #315783;
    padding: 10px 18px;
    margin-right: 3px;
    border: 1px solid #D5E5F5;
    border-radius: 8px;
    min-width: 110px;
}}
QTabBar::tab:selected {{
    background: #0A7DF8;
    color: white;
    border-color: #0A7DF8;
    font-weight: 800;
}}
QRadioButton, QCheckBox {{
    spacing: 7px;
    min-height: 24px;
}}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 18px;
    height: 18px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QToolTip {{
    background: {V5_NAVY};
    color: white;
    border: 0;
}}

/* HOME */
QLabel#metricTitle {{
    color: #173E75;
    font-size: 12px;
    font-weight: 700;
}}
QLabel#metricSubtitle {{
    color: #6B81A7;
    font-size: 10px;
}}
QLabel#metricDelta {{
    color: #00A96E;
    font-size: 11px;
    font-weight: 800;
}}
QLabel#metricIcon, QLabel#scheduleIcon {{
    border-radius: 12px;
    font-size: 24px;
    font-weight: 900;
}}
QLabel#metricIcon[tone="blue"], QLabel#scheduleIcon[tone="blue"] {{
    background: #DDEEFF;
    color: #0C77F5;
}}
QLabel#metricIcon[tone="purple"], QLabel#scheduleIcon[tone="purple"] {{
    background: #EFE2FF;
    color: #743AF3;
}}
QLabel#metricIcon[tone="green"], QLabel#scheduleIcon[tone="green"] {{
    background: #DDF8EC;
    color: #049E68;
}}
QLabel#metricIcon[tone="orange"], QLabel#scheduleIcon[tone="orange"] {{
    background: #FFF0C9;
    color: #E69A00;
}}
QLabel#metricIcon[tone="pink"] {{
    background: #FFE1ED;
    color: #C4005C;
}}
QFrame#heroCard, QFrame#homeCard, QFrame#quickCard, QFrame#tipCard {{
    background: white;
    border: 1px solid #D6E6F7;
    border-radius: 14px;
}}
QLabel#heroRadioIcon {{
    background: #E9F4FF;
    color: #0B79F6;
    border-radius: 35px;
    font-size: 42px;
    font-weight: 900;
}}
QLabel#heroTitle {{
    color: #08245F;
    font-size: 24px;
    font-weight: 900;
}}
QLabel#heroSubtitle {{
    color: #5E79A6;
    font-size: 12px;
}}
QFrame#readyCard {{
    background: #EAF9F2;
    border: 1px solid #C2ECDB;
    border-radius: 10px;
}}
QLabel#readyTitle {{
    color: #078B5F;
    font-size: 14px;
    font-weight: 900;
}}
QLabel#readyText {{
    color: #3F6B60;
    font-size: 11px;
}}
QFrame#monitorVisual {{
    background: #F4F9FF;
    border: 0;
    border-radius: 18px;
}}
QLabel#monitorScreen {{
    color: #0B4D9C;
    font-size: 86px;
    font-weight: 900;
}}
QLabel#monitorLines {{
    color: #72A9E8;
    font-size: 16px;
    font-weight: 700;
}}
QLabel#sectionSubtitle {{
    color: #6A80A5;
    font-size: 10px;
}}
QPushButton#quickPrimary {{
    text-align: left;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0A75EA,stop:1 #0B8EFF);
    color: white;
    border: 0;
    border-radius: 10px;
    padding: 10px 18px;
    font-size: 12px;
    font-weight: 800;
}}
QPushButton#quickSecondary {{
    text-align: left;
    background: #F8FBFF;
    color: #0A3A79;
    border: 1px solid #D4E4F5;
    border-radius: 10px;
    padding: 10px 18px;
    font-size: 12px;
    font-weight: 800;
}}
QPushButton#quickSecondary:hover {{
    background: #EEF6FF;
}}
QFrame#scheduleBox {{
    background: #F8FBFF;
    border: 1px solid #DFEBF7;
    border-radius: 10px;
}}
QLabel#scheduleTitle {{
    color: #0A326D;
    font-size: 11px;
    font-weight: 800;
}}
QLabel#scheduleDetail {{
    color: #526E9B;
    font-size: 10px;
}}
QLabel#smallPill {{
    background: #F8FBFF;
    color: #365D8F;
    border: 1px solid #D6E5F4;
    border-radius: 8px;
    padding: 6px 10px;
}}
QFrame#graphFrame {{
    background: white;
    border: 0;
}}
QLabel#graphText {{
    color: #7EA8DD;
    font-family: "Consolas";
    font-size: 10px;
}}
QLabel#graphLegend {{
    color: #426891;
    font-size: 10px;
}}
QPushButton#linkButton {{
    background: transparent;
    color: #087AF7;
    border: 0;
    padding: 2px 4px;
    min-height: 18px;
    font-weight: 700;
}}
QPushButton#linkButton:hover {{
    color: #075FC0;
    background: transparent;
}}
QLabel#listText {{
    color: #244B7B;
    font-size: 10px;
}}
QFrame#tipCard {{
    background: #FFFFFF;
}}
QLabel#tipText {{
    background: #EDF7FF;
    color: #355D89;
    border-radius: 10px;
    padding: 12px;
    font-size: 11px;
}}
QLabel#dots {{
    color: #0A7BF7;
    font-size: 12px;
}}

/* REFINO GLOBAL V13 */
QAbstractScrollArea {
    outline: 0;
}

QScrollBar:vertical {
    background: #EDF4FB;
    width: 10px;
    margin: 2px 1px 2px 1px;
    border: 0;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #91B8E3;
    min-height: 42px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #6FA5DD;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #EDF4FB;
    height: 10px;
    margin: 1px 2px 1px 2px;
    border: 0;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #91B8E3;
    min-width: 48px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #6FA5DD;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover,
QDateEdit:hover,
QTimeEdit:hover {
    border-color: #A7C9EA;
}

QListWidget::item {
    border-radius: 7px;
    padding: 3px;
}
QListWidget::item:selected {
    background: #E7F3FF;
    color: #08245F;
    border: 1px solid #8EC2F4;
}

QPushButton:focus {
    outline: none;
}
QPushButton[secondary="true"]:focus {
    border-color: #7DB4E9;
}

QMenu {
    background: #FFFFFF;
    color: #08245F;
    border: 1px solid #CFE0F5;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item {
    padding: 7px 20px 7px 10px;
    border-radius: 6px;
}
QMenu::item:selected {
    background: #EAF4FF;
    color: #087AF7;
}

"""

def repolish(widget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
