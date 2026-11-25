"""Startpunkt der Anwendung:  python -m querschnitt [datei.json]"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    # --selftest: startet, rechnet das Beispiel und beendet sich (für CI-Builds)
    selftest = "--selftest" in argv
    if selftest:
        argv.remove("--selftest")

    import matplotlib
    matplotlib.use("QtAgg")

    from PySide6.QtWidgets import QApplication

    from . import __version__
    from .ui.about import app_icon, show_exception
    from .ui.main_window import MainWindow

    app = QApplication(argv)
    app.setApplicationName("Querschnittsberechnung")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("querschnittsberechnung")
    app.setWindowIcon(app_icon())

    window = MainWindow()
    # Unerwartete Fehler anzeigen statt still abzustürzen (wichtig für die .exe/.app)
    sys.excepthook = lambda t, e, tb: show_exception(t, e, tb, window)
    if selftest:
        _run_selftest(app, window)
    if len(argv) > 1:
        window.open_path(argv[1])
    window.show()
    return app.exec()


def _run_selftest(app, window) -> None:
    import time
    import traceback

    from PySide6.QtCore import QTimer

    def fail(t, e, tb):
        traceback.print_exception(t, e, tb)
        app.exit(2)

    sys.excepthook = fail
    start = time.monotonic()

    def check():
        if window._current is not None:
            import os
            import tempfile

            from .report import export_pdf
            names, _res, num, stress = window._current
            pdf = os.path.join(tempfile.mkdtemp(), "selftest.pdf")
            export_pdf(pdf, "Selbsttest", *window._current)
            with open(pdf, "rb") as fh:
                pdf_ok = fh.read(4) == b"%PDF"
            icon_ok = not app.windowIcon().isNull()
            print(f"selftest: A = {num.A}, sigma_max = {stress.sigma_max}, "
                  f"pdf = {pdf_ok}, icon = {icon_ok}", flush=True)
            window._dirty = False
            app.exit(0 if (pdf_ok and icon_ok and abs(num.A - 36) < 1e-9) else 3)
        elif time.monotonic() - start > 60:
            print("selftest: timeout", flush=True)
            app.exit(1)
        else:
            QTimer.singleShot(100, check)

    QTimer.singleShot(100, check)


if __name__ == "__main__":
    raise SystemExit(main())
