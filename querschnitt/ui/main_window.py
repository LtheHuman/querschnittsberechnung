"""Hauptfenster der Anwendung."""

from __future__ import annotations

from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QObject, QRunnable, QSettings, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMenu, QMessageBox,
                               QScrollArea, QSizePolicy, QSplitter, QTabWidget, QToolBar,
                               QToolButton, QVBoxLayout, QWidget)

from ..core import (InputError, SectionResult, b_sym, compute_section, compute_stress, h_sym,
                    parse_expr, signed_area)
from ..plotting import draw_placeholder, draw_section, draw_stress
from ..project import Project
from ..report import export_pdf, text_report
from .about import AboutDialog
from .theme import DARK, LIGHT, Theme, apply_theme
from .results import ResultsPanel
from .widgets import Card, NumberEdit, PointsTable, hint, themed_icon

FILE_FILTER = "Querschnitt (*.json);;Alle Dateien (*)"


# ─── Hintergrund-Berechnung ─────────────────────────────────────────────────

class _Signals(QObject):
    done = Signal(int, object)
    failed = Signal(int, str)


class _SectionJob(QRunnable):
    def __init__(self, gen, points, check_values):
        super().__init__()
        self.gen, self.points, self.check_values = gen, points, check_values
        self.signals = _Signals()

    def run(self):
        try:
            res = compute_section(self.points, check_values=self.check_values)
            self.signals.done.emit(self.gen, res)
        except InputError as exc:
            self.signals.failed.emit(self.gen, str(exc))
        except Exception as exc:  # unerwartet – trotzdem sauber anzeigen
            self.signals.failed.emit(self.gen, f"Berechnung fehlgeschlagen: {exc}")


# ─── Diagramm-Fläche ────────────────────────────────────────────────────────

class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(6, 5), dpi=100)
        super().__init__(self.figure)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    def _menu(self, pos):
        menu = QMenu(self)
        menu.addAction("Bild speichern …", self._save_image)
        menu.exec(self.mapToGlobal(pos))

    def _save_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Bild speichern", "querschnitt.png",
                                              "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)")
        if path:
            self.figure.savefig(path, dpi=200)


# ─── Hauptfenster ───────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("querschnitt", "Querschnittsberechnung")
        self.theme: Theme = self._initial_theme()
        apply_theme(QApplication.instance(), self.theme)

        self._path: Path | None = None
        self._dirty = False
        self._loading = False
        self._gen = 0
        self._cache: dict[tuple, SectionResult] = {}
        self._jobs: dict[int, tuple] = {}
        self._current = None   # (names, res, num, stress)
        self._title = ""

        self._timer = QTimer(self, singleShot=True, interval=250)
        self._timer.timeout.connect(self._recompute)

        self._build_ui()
        self._load_project(Project.example(), path=None)
        self.resize(1440, 880)
        geo = self.settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)

        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._on_system_scheme)

    # ── Aufbau ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_toolbar()

        root = QWidget()
        root.setObjectName("Root")
        outer = QHBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 12)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(12)
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter)
        self.setCentralWidget(root)

        splitter.addWidget(self._scroll(self._build_inputs(), 330))
        splitter.addWidget(self._build_plots())
        self.results = ResultsPanel(self.theme)
        splitter.addWidget(self._scroll(self.results, 380))
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([340, 700, 400])

        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        self.pill = QLabel()
        self.pill.setObjectName("Pill")
        sb.addPermanentWidget(self.pill)
        self._set_state("busy", "Bereit")

    def _scroll(self, widget, min_width):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(widget)
        area.setMinimumWidth(min_width)
        return area

    def _action(self, text, icons, slot, shortcut=None, tip=None):
        act = QAction(themed_icon(*icons), text, self)
        act.triggered.connect(slot)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.setToolTip(f"{tip or text.replace('&&', '&')}" + (f"  ({QKeySequence(shortcut).toString()})"
                                           if shortcut else ""))
        return act

    def _build_toolbar(self):
        tb = QToolBar("Werkzeuge")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        tb.setContextMenuPolicy(Qt.PreventContextMenu)
        self.addToolBar(Qt.TopToolBarArea, tb)

        title = QLabel("Querschnittsberechnung")
        title.setObjectName("AppTitle")
        tb.addWidget(title)
        tb.addSeparator()

        self.act_new = self._action("Neu", ["document-new"], self._new, "Ctrl+N",
                                    "Leeren Querschnitt anlegen")
        self.act_open = self._action("Öffnen", ["document-open"], self._open, "Ctrl+O")
        self.act_save = self._action("Speichern", ["document-save"], self._save, "Ctrl+S")
        self.act_save_as = self._action("Speichern unter …", ["document-save-as"],
                                        self._save_as, "Ctrl+Shift+S")
        self.act_example = self._action("Beispiel", ["help-about", "dialog-information"],
                                        self._load_example, None,
                                        "Querschnitt der BM2-Aufgabe 2026 laden")
        self.act_pdf = self._action("PDF-Bericht", ["application-pdf", "x-office-document"],
                                    self._export_pdf, "Ctrl+P",
                                    "Bericht mit Ergebnissen und Diagrammen als PDF speichern")
        self.act_copy = self._action("Kopieren", ["edit-copy"], self._copy, "Ctrl+Shift+C",
                                     "Ergebnisse als Text in die Zwischenablage")
        for a in (self.act_new, self.act_open, self.act_save):
            tb.addAction(a)
        self.addAction(self.act_save_as)
        tb.addSeparator()
        tb.addAction(self.act_example)
        tb.addSeparator()
        tb.addAction(self.act_pdf)
        tb.addAction(self.act_copy)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        self.act_help = self._action("Info && Hilfe", ["help-browser", "help-contents"],
                                     lambda: AboutDialog(self).exec(), "F1",
                                     "Kurzanleitung, Konventionen und Lizenz")
        tb.addAction(self.act_help)

        self.theme_btn = QToolButton()
        self.theme_btn.setToolTip("Hell / Dunkel umschalten")
        self.theme_btn.clicked.connect(self._toggle_theme)
        tb.addWidget(self.theme_btn)
        self._update_theme_button()

    def _build_inputs(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 4, 0)
        lay.setSpacing(12)

        # Titel
        tcard = Card("Projekt")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Bezeichnung, z. B. Übung 3 – Trapez")
        self.title_edit.textChanged.connect(self._on_title_changed)
        tcard.body.addWidget(self.title_edit)
        lay.addWidget(tcard)

        # Eckpunkte
        pcard = Card("Eckpunkte")
        pcard.body.addWidget(hint("Gegen den Uhrzeigersinn eingeben. Ausdrücke in b und h, "
                                  "z. B. <code>3*b/2</code> oder <code>h/3</code>."))
        self.points = PointsTable()
        self.points.set_danger_color(self.theme.danger)
        self.points.changed.connect(self._on_input_changed)
        pcard.body.addWidget(self.points, 1)
        lay.addWidget(pcard, 1)

        # Parameter
        prm = Card("Parameter")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        self.b_edit = self._num_row(form, "b", "m")
        self.h_edit = self._num_row(form, "h", "m")
        prm.body.addLayout(form)
        lay.addWidget(prm)

        # Schnittgrößen
        ld = Card("Schnittgrößen")
        form2 = QFormLayout()
        form2.setHorizontalSpacing(12)
        form2.setVerticalSpacing(8)
        self.my_edit = self._num_row(form2, "M<sub>y</sub>", "MNm")
        self.mz_edit = self._num_row(form2, "M<sub>z</sub>", "MNm")
        self.n_edit = self._num_row(form2, "N", "MN")
        ld.body.addLayout(form2)
        ld.body.addWidget(hint("M<sub>y</sub> &gt; 0: Druck bei z &gt; z<sub>S</sub> · "
                               "M<sub>z</sub> &gt; 0: Zug bei y &gt; y<sub>S</sub> · "
                               "N &gt; 0: Zug"))
        lay.addWidget(ld)

        # Ergebnisse aktualisieren sich automatisch; Ctrl+Enter erzwingt eine Neuberechnung.
        act = QAction(self)
        act.setShortcuts([QKeySequence("Ctrl+Return"), QKeySequence("Ctrl+Enter")])
        act.triggered.connect(self._recompute)
        self.addAction(act)
        return w

    def _num_row(self, form: QFormLayout, label: str, unit: str) -> NumberEdit:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        edit = NumberEdit()
        edit.textChanged.connect(self._on_input_changed)
        u = QLabel(unit)
        u.setObjectName("Unit")
        u.setMinimumWidth(34)
        h.addWidget(edit, 1)
        h.addWidget(u)
        lbl = QLabel(label)
        lbl.setTextFormat(Qt.RichText)
        lbl.setObjectName("Symbol")
        lbl.setMinimumWidth(28)
        form.addRow(lbl, row)
        return edit

    def _build_plots(self) -> QWidget:
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)
        self.section_canvas = PlotCanvas()
        self.stress_canvas = PlotCanvas()
        for canvas, name in ((self.section_canvas, "Querschnitt"),
                             (self.stress_canvas, "Spannungsverteilung")):
            page = QWidget()
            v = QVBoxLayout(page)
            v.setContentsMargins(8, 8, 8, 8)
            v.addWidget(canvas)
            self.tabs.addTab(page, name)
        return self.tabs

    # ── Theme ───────────────────────────────────────────────────────────────

    def _initial_theme(self) -> Theme:
        pref = self.settings.value("theme", "system")
        if pref == "dark":
            return DARK
        if pref == "light":
            return LIGHT
        return DARK if self._system_is_dark() else LIGHT

    @staticmethod
    def _system_is_dark() -> bool:
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorScheme"):
            return hints.colorScheme() == Qt.ColorScheme.Dark
        return False

    def _on_system_scheme(self, *_):
        if self.settings.value("theme", "system") == "system":
            self._set_theme(DARK if self._system_is_dark() else LIGHT)

    def _toggle_theme(self):
        new = LIGHT if self.theme.is_dark else DARK
        self.settings.setValue("theme", new.name)
        self._set_theme(new)

    def _set_theme(self, theme: Theme):
        self.theme = theme
        apply_theme(QApplication.instance(), theme)
        self.points.set_danger_color(theme.danger)
        self.results.set_theme(theme)
        self._update_theme_button()
        self._redraw()

    def _update_theme_button(self):
        dark = self.theme.is_dark
        icon = themed_icon("weather-clear" if dark else "weather-clear-night")
        self.theme_btn.setIcon(icon)
        self.theme_btn.setText("" if not icon.isNull() else ("☀" if dark else "☾"))

    # ── Status ──────────────────────────────────────────────────────────────

    def _set_state(self, state: str, text: str):
        self.pill.setText(text)
        self.pill.setProperty("state", state)
        self.pill.style().unpolish(self.pill)
        self.pill.style().polish(self.pill)

    # ── Eingaben → Berechnung ───────────────────────────────────────────────

    def _on_title_changed(self, text):
        self._title = text
        if not self._loading:
            self._mark_dirty()

    def _on_input_changed(self, *_):
        if self._loading:
            return
        self._mark_dirty()
        self._set_state("busy", "Rechnet …")
        self._timer.start()

    def _collect(self):
        """Liest alle Eingaben; wirft InputError mit verständlicher Meldung."""
        errs = self.points.invalid_cells()
        if errs:
            raise InputError(errs[0])
        verts = self.points.vertices()
        if len(verts) < 3:
            raise InputError("Mindestens 3 Eckpunkte eingeben.")
        try:
            b, h = self.b_edit.value(), self.h_edit.value()
        except InputError as exc:
            raise InputError(f"Parameter: {exc}") from exc
        if b <= 0 or h <= 0:
            raise InputError("b und h müssen positiv sein.")
        names = [v.name or f"P{i + 1}" for i, v in enumerate(verts)]
        exprs = [(parse_expr(v.y), parse_expr(v.z)) for v in verts]
        return names, exprs, b, h

    def _loads(self):
        try:
            return self.my_edit.value(), self.mz_edit.value(), self.n_edit.value()
        except InputError:
            return None

    def _recompute(self):
        self._timer.stop()
        self._gen += 1
        gen = self._gen
        try:
            names, exprs, b, h = self._collect()
        except InputError as exc:
            self._show_error(str(exc))
            return

        subs = {b_sym: b, h_sym: h}
        coords = [(float(y.subs(subs)), float(z.subs(subs))) for y, z in exprs]
        orientation = signed_area(coords) >= 0
        key = (tuple((str(y), str(z)) for y, z in exprs), orientation)

        # Sofort-Vorschau der Geometrie, solange symbolisch gerechnet wird
        if key not in self._cache:
            draw_section(self.section_canvas.figure, self.theme, names, coords)
            self.section_canvas.draw_idle()

        if key in self._cache:
            self._finish(gen, names, b, h, self._cache[key])
            return

        self._set_state("busy", "Rechnet …")
        job = _SectionJob(gen, exprs, (b, h))
        # Gebundene Methoden (nicht Lambdas) → Qt stellt die Signale im GUI-Thread zu.
        job.signals.done.connect(self._on_job_done)
        job.signals.failed.connect(self._on_job_failed)
        job.setAutoDelete(False)
        self._jobs[gen] = (job, key, names, b, h)
        QThreadPool.globalInstance().start(job)

    def _on_job_done(self, gen, res):
        _job, key, names, b, h = self._jobs.pop(gen, (None, None, None, None, None))
        if key is None:
            return
        self._cache[key] = res
        if gen == self._gen:
            self._finish(gen, names, b, h, res)

    def _on_job_failed(self, gen, msg):
        self._jobs.pop(gen, None)
        if gen == self._gen:
            self._show_error(msg)

    def _finish(self, gen, names, b, h, res: SectionResult):
        if res.reversed_input:
            names = list(reversed(names))
        num = res.numeric(b, h)
        stress, notes = None, []
        loads = self._loads()
        if loads is None:
            notes.append("Schnittgrößen ungültig – Spannungen werden nicht berechnet.")
        else:
            try:
                stress = compute_stress(num, *loads)
            except InputError as exc:
                notes.append(str(exc))
        if res.reversed_input:
            notes.insert(0, "Die Punkte wurden im Uhrzeigersinn eingegeben und für die "
                            "Berechnung automatisch umgedreht.")
        self._current = (names, res, num, stress)
        self.results.show_results(names, res, num, stress)
        self.results.show_notice("\n".join(notes))
        self._redraw()
        self._set_state("ok", "✓ Berechnet")
        self.statusBar().showMessage(
            f"A = {num.A:.4g} m²   ·   {len(names)} Eckpunkte   ·   b = {b:g} m, h = {h:g} m"
            .replace(".", ","))

    def _show_error(self, msg: str):
        self._current = None
        self.results.clear()
        self.results.show_notice(msg)
        self._set_state("error", "Eingabe prüfen")
        self.statusBar().showMessage(msg)
        draw_placeholder(self.section_canvas.figure, self.theme, msg)
        draw_placeholder(self.stress_canvas.figure, self.theme, msg)
        self.section_canvas.draw_idle()
        self.stress_canvas.draw_idle()

    def _redraw(self):
        if not self._current:
            self._recompute()
            return
        names, res, num, stress = self._current
        draw_section(self.section_canvas.figure, self.theme, names, num.points, num)
        if stress is not None:
            draw_stress(self.stress_canvas.figure, self.theme, names, num, stress)
        else:
            draw_placeholder(self.stress_canvas.figure, self.theme,
                             "Keine gültigen Schnittgrößen")
        self.section_canvas.draw_idle()
        self.stress_canvas.draw_idle()

    # ── Projekt / Dateien ───────────────────────────────────────────────────

    def _project(self) -> Project:
        return Project(title=self.title_edit.text().strip(),
                       b=self.b_edit.text(), h=self.h_edit.text(),
                       M_y=self.my_edit.text(), M_z=self.mz_edit.text(), N=self.n_edit.text(),
                       vertices=self.points.vertices())

    def _load_project(self, p: Project, path: Path | None):
        self._loading = True
        self.title_edit.setText(p.title)
        self.b_edit.setText(p.b)
        self.h_edit.setText(p.h)
        self.my_edit.setText(p.M_y)
        self.mz_edit.setText(p.M_z)
        self.n_edit.setText(p.N)
        self.points.set_vertices(p.vertices)
        self._loading = False
        self._path = path
        self._dirty = False
        self._update_title()
        self._recompute()

    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True
            self._update_title()

    def _update_title(self):
        name = self._path.name if self._path else "Unbenannt"
        self.setWindowTitle(f"{'• ' if self._dirty else ''}{name} – Querschnittsberechnung")

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        btn = QMessageBox.question(
            self, "Änderungen speichern?",
            "Der aktuelle Querschnitt wurde geändert. Änderungen speichern?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if btn == QMessageBox.Save:
            return self._save()
        return btn == QMessageBox.Discard

    def _new(self):
        if self._confirm_discard():
            self._load_project(Project(vertices=[]), None)
            self.points.add_after_current()

    def _load_example(self):
        if self._confirm_discard():
            self._load_project(Project.example(), None)

    def _start_dir(self) -> str:
        return str(self.settings.value("last_dir", str(Path.home())))

    def _open(self):
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Querschnitt öffnen", self._start_dir(),
                                              FILE_FILTER)
        if path:
            self.open_path(path)

    def open_path(self, path: str):
        try:
            project = Project.load(path)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Datei konnte nicht geöffnet werden", str(exc))
            return
        self.settings.setValue("last_dir", str(Path(path).parent))
        self._load_project(project, Path(path))

    def _save(self) -> bool:
        if self._path is None:
            return self._save_as()
        return self._write(self._path)

    def _save_as(self) -> bool:
        suggested = Path(self._start_dir()) / ((self.title_edit.text().strip() or "querschnitt")
                                               + ".json")
        path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", str(suggested),
                                              FILE_FILTER)
        if not path:
            return False
        if not path.lower().endswith(".json"):
            path += ".json"
        return self._write(Path(path))

    def _write(self, path: Path) -> bool:
        try:
            self._project().save(path)
        except OSError as exc:
            QMessageBox.critical(self, "Speichern fehlgeschlagen", str(exc))
            return False
        self._path = path
        self._dirty = False
        self.settings.setValue("last_dir", str(path.parent))
        self._update_title()
        self.statusBar().showMessage(f"Gespeichert: {path}", 4000)
        return True

    def _export_pdf(self):
        if not self._current:
            QMessageBox.information(self, "PDF-Bericht", "Es liegen noch keine Ergebnisse vor.")
            return
        base = self._path.stem if self._path else (self.title_edit.text().strip() or "querschnitt")
        path, _ = QFileDialog.getSaveFileName(self, "PDF-Bericht speichern",
                                              str(Path(self._start_dir()) / f"{base}.pdf"),
                                              "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            export_pdf(path, self.title_edit.text().strip(), *self._current)
        except Exception as exc:
            QMessageBox.critical(self, "Export fehlgeschlagen", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(f"PDF gespeichert: {path}", 5000)

    def _copy(self):
        if not self._current:
            return
        QApplication.clipboard().setText(text_report(self.title_edit.text().strip(),
                                                     *self._current))
        self.statusBar().showMessage("Ergebnisse in die Zwischenablage kopiert.", 3000)

    def closeEvent(self, event):
        if self._confirm_discard():
            self.settings.setValue("geometry", self.saveGeometry())
            event.accept()
        else:
            event.ignore()
