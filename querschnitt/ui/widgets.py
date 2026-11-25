"""Wiederverwendbare Widgets: Karten, Formelanzeige, validierte Eingaben, Punkttabelle."""

from __future__ import annotations

import io
from functools import lru_cache

from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QPushButton, QSizePolicy, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from ..core import InputError, parse_expr, parse_number
from ..project import Vertex


# ─── Layout-Bausteine ───────────────────────────────────────────────────────

class Card(QFrame):
    """Abgerundete Fläche mit Überschrift in Kapitälchen."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(14, 12, 14, 14)
        self.body.setSpacing(8)
        if title:
            head = QHBoxLayout()
            head.setSpacing(6)
            self.title_label = QLabel(title.upper())
            self.title_label.setObjectName("CardTitle")
            head.addWidget(self.title_label)
            head.addStretch(1)
            self.header = head
            self.body.addLayout(head)


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("Divider")
    return line


def hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Hint")
    lbl.setWordWrap(True)
    return lbl


def themed_icon(*names: str) -> QIcon:
    """Icon aus dem System-Theme (z. B. Papirus), erster Treffer gewinnt."""
    for n in names:
        icon = QIcon.fromTheme(n)
        if not icon.isNull():
            return icon
    return QIcon()


# ─── Formeln ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=256)
def render_math(tex: str, color: str, size: float = 11.0, dpr: float = 2.0) -> QPixmap:
    """Rendert LaTeX (matplotlib-mathtext) als QPixmap in hoher Auflösung."""
    buf = io.BytesIO()
    fig = Figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${tex}$", fontsize=size, color=color, math_fontfamily="dejavusans")
    fig.savefig(buf, dpi=72 * dpr, format="png", transparent=True,
                bbox_inches="tight", pad_inches=0.02)
    pix = QPixmap()
    pix.loadFromData(buf.getvalue(), "PNG")
    pix.setDevicePixelRatio(dpr)
    return pix


class MathLabel(QLabel):
    """Label, das einen LaTeX-Ausdruck anzeigt und bei Bedarf herunterskaliert."""

    def __init__(self, parent=None, max_width: int = 220):
        super().__init__(parent)
        self._tex = ""
        self._color = "#000"
        self._max_width = max_width
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def set_math(self, tex: str, color: str) -> None:
        self._tex, self._color = tex, color
        if not tex:
            self.clear()
            return
        try:
            pix = render_math(tex, color, 12.0, max(2.0, self.devicePixelRatioF()))
        except Exception:  # Formel nicht darstellbar → Klartext
            self.setText(tex)
            return
        logical_w = pix.width() / pix.devicePixelRatio()
        if logical_w > self._max_width:
            ratio = self._max_width / logical_w
            pix = pix.scaled(int(pix.width() * ratio), int(pix.height() * ratio),
                             Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(pix)


# ─── Eingabefelder ──────────────────────────────────────────────────────────

class NumberEdit(QLineEdit):
    """Eingabe einer Zahl (Komma oder Punkt, auch Ausdrücke wie 3/2)."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.textChanged.connect(self._validate)
        self._validate()

    def value(self) -> float:
        return parse_number(self.text())

    def is_valid(self) -> bool:
        try:
            self.value()
            return True
        except InputError:
            return False

    def _validate(self) -> None:
        try:
            self.value()
            self.setProperty("invalid", False)
            self.setToolTip("")
        except InputError as exc:
            self.setProperty("invalid", True)
            self.setToolTip(str(exc))
        self.style().unpolish(self)
        self.style().polish(self)


# ─── Punkttabelle ───────────────────────────────────────────────────────────

class PointsTable(QWidget):
    """Tabelle der Eckpunkte mit Hinzufügen/Entfernen/Verschieben."""

    changed = Signal()

    COL_NAME, COL_Y, COL_Z = range(3)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._danger = QColor("#c62f3c")
        self._updating = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Punkt", "y", "z"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(self.COL_NAME, QHeaderView.Fixed)
        hh.setSectionResizeMode(self.COL_Y, QHeaderView.Stretch)
        hh.setSectionResizeMode(self.COL_Z, QHeaderView.Stretch)
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setColumnWidth(self.COL_NAME, 62)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.table.setMinimumHeight(200)
        self.table.itemChanged.connect(self._on_item_changed)
        lay.addWidget(self.table, 1)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.btn_add = QPushButton(themed_icon("list-add"), " Punkt")
        self.btn_add.setToolTip("Punkt nach der markierten Zeile einfügen")
        self.btn_remove = QPushButton(themed_icon("list-remove"), "")
        self.btn_remove.setToolTip("Markierten Punkt entfernen")
        self.btn_up = QPushButton(themed_icon("go-up"), "")
        self.btn_up.setToolTip("Nach oben verschieben")
        self.btn_down = QPushButton(themed_icon("go-down"), "")
        self.btn_down.setToolTip("Nach unten verschieben")
        for b in (self.btn_remove, self.btn_up, self.btn_down):
            b.setObjectName("IconButton")
            if b.icon().isNull():
                b.setText({self.btn_remove: "−", self.btn_up: "↑", self.btn_down: "↓"}[b])
        self.btn_add.clicked.connect(self.add_after_current)
        self.btn_remove.clicked.connect(self.remove_current)
        self.btn_up.clicked.connect(lambda: self.move_current(-1))
        self.btn_down.clicked.connect(lambda: self.move_current(+1))
        bar.addWidget(self.btn_add)
        bar.addStretch(1)
        for b in (self.btn_up, self.btn_down, self.btn_remove):
            bar.addWidget(b)
        lay.addLayout(bar)

    # ── Daten ───────────────────────────────────────────────────────────────

    def set_danger_color(self, color: str) -> None:
        self._danger = QColor(color)
        self._revalidate_all()

    def set_vertices(self, vertices: list[Vertex]) -> None:
        self._updating = True
        self.table.setRowCount(0)
        for v in vertices:
            self._insert_row(self.table.rowCount(), v)
        self._updating = False
        self._revalidate_all()
        self.changed.emit()

    def vertices(self) -> list[Vertex]:
        out = []
        for r in range(self.table.rowCount()):
            out.append(Vertex(*(self._text(r, c) for c in range(3))))
        return out

    def _text(self, row: int, col: int) -> str:
        item = self.table.item(row, col)
        return item.text().strip() if item else ""

    def _insert_row(self, row: int, v: Vertex) -> None:
        self.table.insertRow(row)
        for col, text in enumerate((v.name, v.y, v.z)):
            item = QTableWidgetItem(text)
            if col == self.COL_NAME:
                item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, item)

    def _next_name(self) -> str:
        used = {self._text(r, 0) for r in range(self.table.rowCount())}
        for i in range(26):
            n = chr(ord("A") + i)
            if n not in used:
                return n
        i = 1
        while f"P{i}" in used:
            i += 1
        return f"P{i}"

    # ── Aktionen ────────────────────────────────────────────────────────────

    def add_after_current(self) -> None:
        row = self.table.currentRow()
        row = self.table.rowCount() if row < 0 else row + 1
        self._updating = True
        self._insert_row(row, Vertex(self._next_name(), "", ""))
        self._updating = False
        self.table.setCurrentCell(row, self.COL_Y)
        self.table.editItem(self.table.item(row, self.COL_Y))
        self._revalidate_all()
        self.changed.emit()

    def remove_current(self) -> None:
        row = self.table.currentRow()
        if row < 0 and self.table.rowCount():
            row = self.table.rowCount() - 1
        if row >= 0:
            self.table.removeRow(row)
            self.changed.emit()

    def move_current(self, delta: int) -> None:
        row = self.table.currentRow()
        target = row + delta
        if row < 0 or not (0 <= target < self.table.rowCount()):
            return
        self._updating = True
        a = [self._text(row, c) for c in range(3)]
        b = [self._text(target, c) for c in range(3)]
        for c in range(3):
            self.table.item(row, c).setText(b[c])
            self.table.item(target, c).setText(a[c])
        self._updating = False
        self.table.setCurrentCell(target, self.table.currentColumn())
        self._revalidate_all()
        self.changed.emit()

    # ── Validierung ─────────────────────────────────────────────────────────

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return
        self._validate_item(item)
        self.changed.emit()

    def _revalidate_all(self) -> None:
        self._updating = True
        for r in range(self.table.rowCount()):
            for c in (self.COL_Y, self.COL_Z):
                item = self.table.item(r, c)
                if item:
                    self._validate_item(item)
        self._updating = False

    def _validate_item(self, item: QTableWidgetItem) -> None:
        if item.column() == self.COL_NAME:
            return
        was = self._updating
        self._updating = True
        try:
            parse_expr(item.text())
            item.setData(Qt.ForegroundRole, None)
            item.setToolTip("Ausdruck in b und h, z. B. 3*b/2 oder h/3")
        except InputError as exc:
            item.setForeground(self._danger)
            item.setToolTip(str(exc))
        self._updating = was

    def invalid_cells(self) -> list[str]:
        errs = []
        for r in range(self.table.rowCount()):
            name = self._text(r, 0) or f"Zeile {r + 1}"
            for c, axis in ((self.COL_Y, "y"), (self.COL_Z, "z")):
                try:
                    parse_expr(self._text(r, c))
                except InputError as exc:
                    errs.append(f"{name}, {axis}: {exc}")
        return errs
