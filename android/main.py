from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


class AppBridge(QObject):
    sectionChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._section = "Início"

    @Property(str, notify=sectionChanged)
    def currentSection(self) -> str:
        return self._section

    @Slot(str)
    def openSection(self, section: str) -> None:
        section = section.strip() or "Início"
        if section == self._section:
            return
        self._section = section
        self.sectionChanged.emit()

    @Slot(result=str)
    def versionLabel(self) -> str:
        return "Android MVP 0.1"


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Central Inteligente de Mídia")
    app.setApplicationDisplayName("Central Inteligente de Mídia")
    app.setOrganizationName("Central Inteligente de Mídia")

    engine = QQmlApplicationEngine()
    bridge = AppBridge()
    engine.rootContext().setContextProperty("appBridge", bridge)

    root = Path(__file__).resolve().parent
    qml_file = root / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
