"""Startpunkt der Anwendung:  python -m querschnitt [datei.json]"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv

    import matplotlib
    matplotlib.use("QtAgg")

    from PySide6.QtWidgets import QApplication

    from . import __version__
    from .ui.main_window import MainWindow

    app = QApplication(argv)
    app.setApplicationName("Querschnittsberechnung")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("querschnittsberechnung")

    window = MainWindow()
    if len(argv) > 1:
        window.open_path(argv[1])
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
