"""Minimal PySide6/QML test app for qt-pilot end-to-end testing."""

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from qt_pilot import install


def main():
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    qml_file = Path(__file__).parent / "test_app.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        print("ERROR: failed to load QML", file=sys.stderr)
        sys.exit(1)

    install(engine)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
