from __future__ import annotations

V5_NAVY = "#052D57"
V5_NAVY_DARK = "#031F3E"
V5_INK = "#0A1F4B"
V5_MUTED = "#58739F"
V5_BG = "#F3F8FE"
V5_BORDER = "#D5E4F3"
V5_BLUE = "#087AF7"
V5_PURPLE = "#743AF3"
V5_ORANGE = "#FF820A"
V5_GREEN = "#08A86F"
V5_RED = "#D92F43"
V5_GOLD = "#F2B715"
V5_SOFT_BLUE = "#EAF4FF"

APP_STYLESHEET = f"""
QMainWindow, QWidget#root {{ background: {V5_BG}; color: {V5_INK}; }}
QWidget {{ font-family: 'Segoe UI'; font-size: 11px; color: {V5_INK}; }}
QFrame#sidebar {{ background: {V5_NAVY_DARK}; border: none; }}
QLabel#brandTitle {{ color: white; font-size: 18px; font-weight: 700; }}
QLabel#brandSub {{ color: #B9CEE6; font-size: 10px; }}
QPushButton#navButton {{ color: #D7E8F7; text-align: left; border: 0; border-radius: 9px; padding: 9px 12px; background: transparent; }}
QPushButton#navButton:hover {{ background: #123F6A; }}
QPushButton#navButton:checked {{ color: white; background: #0A5EA8; font-weight: 700; }}
QFrame#card {{ background: white; border: 1px solid {V5_BORDER}; border-radius: 11px; }}
QLabel#pageKicker {{ color: #B78900; font-size: 10px; font-weight: 700; }}
QLabel#pageTitle {{ color: {V5_INK}; font-size: 22px; font-weight: 800; }}
QLabel#pageSubtitle {{ color: {V5_MUTED}; font-size: 11px; }}
QLabel#muted {{ color: {V5_MUTED}; }}
QLabel#sectionTitle {{ color: {V5_INK}; font-size: 16px; font-weight: 700; }}
QLineEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit {{ background: white; border: 1px solid {V5_BORDER}; border-radius: 7px; padding: 7px 9px; min-height: 24px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {V5_BLUE}; }}
QPushButton {{ background: {V5_BLUE}; color: white; border: 0; border-radius: 7px; padding: 8px 12px; font-weight: 600; }}
QPushButton:hover {{ background: #096CDD; }}
QPushButton:disabled {{ background: #B9C8D8; color: #EDF3F8; }}
QPushButton[secondary='true'] {{ background: white; color: {V5_INK}; border: 1px solid {V5_BORDER}; }}
QPushButton[danger='true'] {{ background: {V5_RED}; color: white; }}
QPushButton[purple='true'] {{ background: {V5_PURPLE}; color: white; }}
QPushButton[orange='true'] {{ background: {V5_ORANGE}; color: white; }}
QPushButton[green='true'] {{ background: {V5_GREEN}; color: white; }}
QProgressBar {{ border: 1px solid {V5_BORDER}; border-radius: 4px; background: #E4EDF7; text-align: center; min-height: 8px; }}
QProgressBar::chunk {{ background: {V5_BLUE}; border-radius: 3px; }}
QListWidget, QTableWidget {{ background: white; border: 1px solid {V5_BORDER}; border-radius: 8px; alternate-background-color: #F7FAFE; }}
QHeaderView::section {{ background: #EAF4FF; color: {V5_INK}; padding: 7px; border: 0; border-bottom: 1px solid {V5_BORDER}; font-weight: 700; }}
QTabWidget::pane {{ border: 1px solid {V5_BORDER}; border-radius: 8px; background: white; }}
QTabBar::tab {{ background: #F6F9FD; padding: 8px 14px; margin-right: 3px; border-radius: 6px; }}
QTabBar::tab:selected {{ background: #EDE7FF; color: {V5_PURPLE}; font-weight: 700; }}
QScrollArea {{ border: none; background: transparent; }}
QCheckBox {{ spacing: 7px; }}
QToolTip {{ background: {V5_NAVY}; color: white; border: 0; }}
"""
