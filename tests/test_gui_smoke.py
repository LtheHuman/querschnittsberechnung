"""Smoke-Test der Oberfläche ohne Bildschirm (QT_QPA_PLATFORM=offscreen)."""

import os
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Einstellungen (QSettings) in ein temporäres Verzeichnis umleiten,
# damit Tests nie das echte Benutzerprofil verändern.
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="querschnitt-test-")
pytest.importorskip("PySide6")

import matplotlib  # noqa: E402

matplotlib.use("QtAgg")

from PySide6.QtWidgets import QApplication  # noqa: E402

from querschnitt.project import Project, Vertex  # noqa: E402


@pytest.fixture(scope="module")
def window():
    app = QApplication.instance() or QApplication([])
    from querschnitt.ui.main_window import MainWindow
    w = MainWindow()
    w.show()
    yield w
    w._dirty = False
    w.close()
    app.processEvents()


def wait_for(cond, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        QApplication.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_example_is_calculated(window):
    assert wait_for(lambda: window._current is not None)
    names, res, num, stress = window._current
    assert names == ["A", "B", "C", "D", "E"]
    assert num.A == pytest.approx(36.0)
    assert stress.sigma_max == pytest.approx(23.5974676, rel=1e-6)


def test_invalid_input_shows_error(window):
    window.b_edit.setText("abc")
    assert wait_for(lambda: window.pill.property("state") == "error")
    assert window._current is None
    window.b_edit.setText("2")
    assert wait_for(lambda: window._current is not None)


def test_clockwise_input_is_flagged(window):
    window._load_project(Project(vertices=[Vertex("A", "0", "0"), Vertex("B", "0", "h"),
                                           Vertex("C", "b", "h"), Vertex("D", "b", "0")]),
                         None)
    assert wait_for(lambda: window._current is not None and window._current[1].reversed_input)
    assert "Uhrzeigersinn" in window.results.notice.text()


def test_save_load_and_pdf(window, tmp_path):
    window._load_project(Project.example(), None)
    assert wait_for(lambda: window._current is not None and len(window._current[0]) == 5)
    path = tmp_path / "q.json"
    assert window._write(path)
    window.open_path(str(path))
    assert window.title_edit.text() == "BM2 Aufgabe 2026"

    from querschnitt.report import export_pdf, text_report
    pdf = tmp_path / "bericht.pdf"
    export_pdf(str(pdf), "Test", *window._current)
    assert pdf.read_bytes()[:4] == b"%PDF"
    assert "σ_max = +23,5975" in text_report("Test", *window._current)
