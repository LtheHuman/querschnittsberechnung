"""Info-/Hilfe-Dialog und Fehlerdialog für unerwartete Ausnahmen."""

from __future__ import annotations

import traceback
from importlib.resources import files

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
                               QScrollArea, QVBoxLayout, QWidget)

from .. import __version__

REPO_URL = "https://github.com/LtheHuman/querschnittsberechnung"
ISSUES_URL = REPO_URL + "/issues/new/choose"
RELEASES_URL = REPO_URL + "/releases/latest"


def app_icon() -> QIcon:
    res = files("querschnitt") / "resources"
    icon = QIcon()
    for name in ("icon.svg", "icon.png"):
        path = res / name
        if path.is_file():
            icon.addFile(str(path))
    return icon


HELP_HTML = f"""
<h3 style="margin-bottom:4px">Kurzanleitung</h3>
<ol style="margin-top:0">
  <li><b>Eckpunkte</b> gegen den Uhrzeigersinn eingeben. Erlaubt sind Zahlen und Ausdrücke
      in <code>b</code> und <code>h</code>, z. B. <code>3*b/2</code>, <code>h/3</code>,
      <code>1,5*b</code>, <code>sqrt(2)*h</code>. Rein numerische Querschnitte gehen auch.</li>
  <li><b>Parameter</b> b und h eingeben.</li>
  <li><b>Schnittgrößen</b> M<sub>y</sub>, M<sub>z</sub> und N eingeben.</li>
  <li>Die Ergebnisse aktualisieren sich sofort. <b>PDF-Bericht</b> exportiert alles.</li>
</ol>
<p>Rechtsklick auf ein Diagramm speichert es als Bild. Fahre mit der Maus über einen
Zahlenwert, um die exakte Formel zu sehen.</p>

<h3 style="margin-bottom:4px">Einheiten</h3>
<p style="margin-top:0">Die Rechnung selbst ist einheitenfrei. Die Beschriftung geht von
<b>m</b> und <b>MN</b> aus (σ in MN/m² = N/mm²). Wer konsequent andere Einheiten verwendet,
z. B. cm und kN, erhält σ in kN/cm².</p>

<h3 style="margin-bottom:4px">Konventionen</h3>
<ul style="margin-top:0">
  <li>y nach rechts, z nach oben; alle Momente bezogen auf den Schwerpunkt S</li>
  <li>I<sub>yz</sub> = +∫ y·z dA</li>
  <li>M<sub>y</sub> &gt; 0 → Druck bei z &gt; z<sub>S</sub>;
      M<sub>z</sub> &gt; 0 → Zug bei y &gt; y<sub>S</sub>; N &gt; 0 → Zug</li>
  <li>tan 2θ = 2·I<sub>yz</sub> / (I<sub>y</sub> − I<sub>z</sub>), θ = ½·arctan(tan 2θ)</li>
  <li>σ = N/A + (M<sub>z</sub>I<sub>y</sub> + M<sub>y</sub>I<sub>yz</sub>)/D · ỹ
      − (M<sub>y</sub>I<sub>z</sub> + M<sub>z</sub>I<sub>yz</sub>)/D · z̃,
      &nbsp;D = I<sub>y</sub>I<sub>z</sub> − I<sub>yz</sub>²</li>
</ul>
<p>Prüfe, ob diese Konventionen zu deiner Lehrveranstaltung passen – andere Lehrbücher
verwenden z. B. z nach unten oder ein anderes Vorzeichen für I<sub>yz</sub>.</p>

<h3 style="margin-bottom:4px">Hinweis</h3>
<p style="margin-top:0">Dieses Programm ist ein privates Studierendenprojekt und
<b>kein offizielles Angebot der TU Graz</b>. Es dient zur Kontrolle eigener Rechnungen.
Alle Ergebnisse ohne Gewähr – bitte selbst nachvollziehen.</p>

<p>Fehler gefunden oder Idee? <a href="{ISSUES_URL}">Auf GitHub melden</a> ·
<a href="{RELEASES_URL}">Neueste Version</a></p>
<p style="color:gray">Version {__version__} · MIT-Lizenz · © 2026 LtheHuman ·
<a href="{REPO_URL}">Quellcode</a><br>
Verwendet Qt/PySide6 (LGPL), SymPy, NumPy und matplotlib.</p>
"""


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Info & Hilfe")
        self.resize(560, 640)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(14)
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(56, 56))
        head.addWidget(icon, 0, Qt.AlignTop)
        title = QLabel(f"<div style='font-size:17px; font-weight:600'>Querschnittsberechnung</div>"
                       f"<div style='color:gray'>Version {__version__} · Querschnittswerte und "
                       f"Normalspannungen beliebiger Polygone</div>")
        title.setWordWrap(True)
        head.addWidget(title, 1)
        lay.addLayout(head)

        body = QLabel(HELP_HTML)
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setOpenExternalLinks(True)
        body.setTextInteractionFlags(Qt.TextBrowserInteraction)
        body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 8, 0)
        wl.addWidget(body)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(wrap)
        lay.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)


def show_exception(exc_type, exc, tb, parent=None) -> None:
    """Zeigt unerwartete Fehler an, statt das Programm still abstürzen zu lassen."""
    details = "".join(traceback.format_exception(exc_type, exc, tb))
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle("Unerwarteter Fehler")
    box.setTextFormat(Qt.RichText)
    box.setText(f"<b>Es ist ein unerwarteter Fehler aufgetreten.</b><br><br>{exc_type.__name__}: "
                f"{str(exc)[:300]}<br><br>Die Eingaben bleiben erhalten. Wenn das öfter passiert, "
                f"<a href='{ISSUES_URL}'>melde den Fehler bitte auf GitHub</a> und füge die "
                f"Details (unten) bei.")
    box.setDetailedText(details)
    box.exec()
