"""Ergebnisanzeige: Querschnittswerte mit Formeln und Normalspannungen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget)

from ..core import NumericSection, SectionResult, StressResult
from ..formatting import fmt, to_latex
from .theme import Theme
from .widgets import Card, MathLabel, divider, hint

# (Schlüssel, Symbol als Rich-Text, Einheit, Formel anzeigen?)
ROWS = [
    [("A", "A", "m²", True)],
    [("y_S", "y<sub>S</sub>", "m", True), ("z_S", "z<sub>S</sub>", "m", True)],
    [("I_y", "I<sub>y</sub>", "m⁴", True), ("I_z", "I<sub>z</sub>", "m⁴", True),
     ("I_yz", "I<sub>yz</sub>", "m⁴", True)],
    [("I_1", "I<sub>1</sub>", "m⁴", False), ("I_2", "I<sub>2</sub>", "m⁴", False),
     ("tan_2theta", "tan 2θ", "", True), ("theta", "θ", "°", False)],
]


class ResultsPanel(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._last = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        self.notice = QLabel()
        self.notice.setObjectName("Notice")
        self.notice.setWordWrap(True)
        self.notice.hide()
        lay.addWidget(self.notice)

        # ── Querschnittswerte ───────────────────────────────────────────────
        card = Card("Querschnittswerte")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(7)
        grid.setColumnStretch(1, 1)
        self._cells: dict[str, tuple[MathLabel, QLabel]] = {}
        row = 0
        for gi, group in enumerate(ROWS):
            if gi:
                grid.addWidget(divider(), row, 0, 1, 4)
                row += 1
            for key, sym, unit, show_formula in group:
                s = QLabel(sym)
                s.setObjectName("Symbol")
                s.setTextFormat(Qt.RichText)
                formula = MathLabel(max_width=190)
                if not show_formula:
                    formula.setVisible(False)
                val = QLabel("–")
                val.setObjectName("Value")
                val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                val.setTextInteractionFlags(Qt.TextSelectableByMouse)
                u = QLabel(unit)
                u.setObjectName("Unit")
                grid.addWidget(s, row, 0, Qt.AlignLeft | Qt.AlignVCenter)
                grid.addWidget(formula, row, 1, Qt.AlignLeft | Qt.AlignVCenter)
                grid.addWidget(val, row, 2)
                grid.addWidget(u, row, 3)
                self._cells[key] = (formula, val)
                row += 1
        card.body.addLayout(grid)
        card.body.addWidget(hint("Formeln in b und h, Zahlenwerte für die eingegebenen "
                                 "Parameter. Alle Momente bezogen auf den Schwerpunkt S. "
                                 "tan 2θ = 2·I<sub>yz</sub> / (I<sub>y</sub> − I<sub>z</sub>)."))
        lay.addWidget(card)

        # ── Spannungen ──────────────────────────────────────────────────────
        scard = Card("Normalspannungen")
        top = QHBoxLayout()
        top.setSpacing(12)
        self.max_box, self.max_val, self.max_at = self._big("σ<sub>max</sub>", "Tension")
        self.min_box, self.min_val, self.min_at = self._big("σ<sub>min</sub>", "Compression")
        top.addWidget(self.max_box, 1)
        top.addWidget(self.min_box, 1)
        scard.body.addLayout(top)
        scard.body.addWidget(divider())
        self.vertex_grid = QGridLayout()
        self.vertex_grid.setHorizontalSpacing(12)
        self.vertex_grid.setVerticalSpacing(4)
        self.vertex_grid.setColumnStretch(3, 1)
        scard.body.addLayout(self.vertex_grid)
        self.stress_hint = hint("")
        scard.body.addWidget(self.stress_hint)
        lay.addWidget(scard)
        lay.addStretch(1)

    def _big(self, title: str, obj: str):
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        t = QLabel(title)
        t.setObjectName("Hint")
        t.setTextFormat(Qt.RichText)
        val = QLabel("–")
        val.setObjectName(obj)
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        at = QLabel("")
        at.setObjectName("Hint")
        v.addWidget(t)
        v.addWidget(val)
        v.addWidget(at)
        return box, val, at

    # ── Aktualisieren ───────────────────────────────────────────────────────

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        if self._last:
            self.show_results(*self._last)

    def clear(self) -> None:
        self._last = None
        for formula, val in self._cells.values():
            formula.set_math("", self.theme.muted)
            val.setText("–")
        self.max_val.setText("–")
        self.min_val.setText("–")
        self.max_at.setText("")
        self.min_at.setText("")
        self._clear_vertices()
        self.notice.hide()

    def show_notice(self, text: str) -> None:
        self.notice.setText(text)
        self.notice.setVisible(bool(text))

    def show_results(self, names: list[str], res: SectionResult, num: NumericSection,
                     stress: StressResult | None) -> None:
        self._last = (names, res, num, stress)
        for key, (formula, val) in self._cells.items():
            if key == "theta":
                val.setText(fmt(num.theta_deg, 5))
                continue
            expr = getattr(res, key)
            if not formula.isHidden():
                formula.set_math(to_latex(expr) + r"\ =", self.theme.muted)
            val.setText(fmt(getattr(num, key)))
            val.setToolTip(str(expr))

        self._clear_vertices()
        if stress is None:
            self.max_val.setText("–")
            self.min_val.setText("–")
            return
        i_max = stress.vertex_sigma.index(stress.sigma_max)
        i_min = stress.vertex_sigma.index(stress.sigma_min)
        for lbl, val in ((self.max_val, stress.sigma_max), (self.min_val, stress.sigma_min)):
            lbl.setText(fmt(val, 5, signed=True))
            lbl.setObjectName("Tension" if val > 0 else "Compression" if val < 0 else "BigValue")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
        self.max_at.setText(f"MN/m² · im Punkt {names[i_max]}")
        self.min_at.setText(f"MN/m² · im Punkt {names[i_min]}")

        heads = ["Punkt", "y [m]", "z [m]", "σ [MN/m²]"]
        for c, txt in enumerate(heads):
            h = QLabel(txt)
            h.setObjectName("Hint")
            h.setAlignment(Qt.AlignRight if c else Qt.AlignLeft)
            self.vertex_grid.addWidget(h, 0, c)
        for r, (name, (y, z), s) in enumerate(zip(names, num.points, stress.vertex_sigma), 1):
            cells = [name, fmt(y, 5), fmt(z, 5), fmt(s, 5, signed=True)]
            for c, txt in enumerate(cells):
                lbl = QLabel(txt)
                lbl.setAlignment(Qt.AlignRight if c else Qt.AlignLeft)
                if c == 3:
                    col = (self.theme.tension if s > 0 else
                           self.theme.compression if s < 0 else self.theme.muted)
                    weight = 600 if r - 1 in (i_max, i_min) else 400
                    lbl.setStyleSheet(f"color: {col}; font-weight: {weight};")
                self.vertex_grid.addWidget(lbl, r, c)
        self.stress_hint.setText(
            f"M<sub>y</sub> = {fmt(stress.M_y)} MNm, M<sub>z</sub> = {fmt(stress.M_z)} MNm, "
            f"N = {fmt(stress.N)} MN. Rot = Zug (σ &gt; 0), blau = Druck (σ &lt; 0). "
            f"Bei linearem Spannungsverlauf "
            f"liegen die Extremwerte immer in Eckpunkten.")

    def _clear_vertices(self) -> None:
        while self.vertex_grid.count():
            w = self.vertex_grid.takeAt(0).widget()
            if w:
                w.deleteLater()
