# Querschnittsberechnung

[![Tests](https://github.com/LtheHuman/querschnittsberechnung/actions/workflows/tests.yml/badge.svg)](https://github.com/LtheHuman/querschnittsberechnung/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Qt](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt%206-41cd52)

Desktop-App zur **symbolischen und numerischen Berechnung von Querschnittswerten**
beliebiger Polygone samt **Normalspannungen bei schiefer Biegung mit Normalkraft**
– entstanden für *Baumechanik 2* an der TU Graz.

![Screenshot (hell)](docs/screenshot-hell.png)

## Funktionen

- **Eckpunkte als Ausdrücke** in `b` und `h` (z. B. `3*b/2`, `h/3`, auch `1,5*b`)
- **Live-Berechnung** während der Eingabe – kein „Berechnen“-Knopf nötig
- Querschnittswerte **als Formel und Zahl**: A, y<sub>S</sub>, z<sub>S</sub>,
  I<sub>y</sub>, I<sub>z</sub>, I<sub>yz</sub>, I<sub>1</sub>, I<sub>2</sub>, tan 2θ, θ
- **Diagramm** des Querschnitts mit Schwerpunkt und Hauptachsen ξ₁ / ξ₂
- **Spannungsverteilung** als Farbkarte mit Nulllinie und Werten an allen Eckpunkten,
  σ<sub>max</sub> / σ<sub>min</sub> hervorgehoben
- **PDF-Bericht** (Eingabe, Formeln, Ergebnisse, Diagramme) und Ergebnisse als Text kopieren
- Prüft die Eingabe: Fehler werden direkt am Feld markiert, Selbstüberschneidungen erkannt,
  Eingabe im Uhrzeigersinn wird automatisch umgedreht
- **Hell- und Dunkelmodus** (folgt dem System, umschaltbar)
- Speichern/Laden als JSON (kompatibel mit Dateien der alten Version)

![Screenshot (dunkel, Spannungsverteilung)](docs/screenshot-dunkel.png)

## Installation

Voraussetzung: Python 3.10 oder neuer.

```bash
git clone https://github.com/LtheHuman/querschnittsberechnung.git
cd querschnittsberechnung
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

## Starten

```bash
querschnitt                        # oder: python -m querschnitt
querschnitt examples/l_profil.json # Datei direkt öffnen
```

## Bedienung

1. **Eckpunkte** gegen den Uhrzeigersinn eintragen (Ausdrücke mit `b` und `h`).
   Mit den Pfeiltasten unter der Tabelle lassen sich Punkte umsortieren.
2. **Parameter** b und h in Metern eingeben.
3. **Schnittgrößen** M<sub>y</sub>, M<sub>z</sub> [MNm] und N [MN] eintragen.
4. Die Ergebnisse aktualisieren sich sofort. Über **PDF-Bericht** lässt sich alles exportieren.

| Tastenkürzel | Aktion |
|---|---|
| `Ctrl+N` / `Ctrl+O` / `Ctrl+S` | Neu / Öffnen / Speichern |
| `Ctrl+Shift+S` | Speichern unter |
| `Ctrl+P` | PDF-Bericht |
| `Ctrl+Shift+C` | Ergebnisse kopieren |
| `Ctrl+Enter` | Neu berechnen |

Rechtsklick auf ein Diagramm speichert es als PNG, SVG oder PDF.

## Konventionen

Koordinaten: y nach rechts, z nach oben; alle Momente beziehen sich auf den Schwerpunkt S.

- I<sub>yz</sub> = +∫ y·z dA
- **M<sub>y</sub> > 0** → Druck auf der Seite z > z<sub>S</sub> (M<sub>y</sub> = −∫ z·σ dA)
- **M<sub>z</sub> > 0** → Zug auf der Seite y > y<sub>S</sub> (M<sub>z</sub> = +∫ y·σ dA)
- tan 2θ = 2·I<sub>yz</sub> / (I<sub>y</sub> − I<sub>z</sub>)

Spannungsformel mit D = I<sub>y</sub>·I<sub>z</sub> − I<sub>yz</sub>², ỹ = y − y<sub>S</sub>, z̃ = z − z<sub>S</sub>:

```
σ = N/A + (Mz·Iy + My·Iyz)/D · ỹ − (My·Iz + Mz·Iyz)/D · z̃
```

Da σ im Querschnitt linear verläuft, liegen σ<sub>max</sub> und σ<sub>min</sub> immer in Eckpunkten.

## Projektstruktur

```
querschnitt/
├── core.py          Rechenkern (SymPy, ohne GUI) – auch für Skripte/Notebooks nutzbar
├── plotting.py      Diagramme (matplotlib)
├── report.py        PDF- und Textbericht
├── project.py       Datenmodell, JSON
└── ui/              Qt-Oberfläche (Hauptfenster, Widgets, Theme)
tests/               Tests gegen bekannte Lösungen + GUI-Smoke-Test
examples/            Beispiel-Querschnitte
```

Rechenkern direkt verwenden:

```python
from querschnitt.core import compute_section, compute_stress, parse_expr

pts = [(parse_expr(y), parse_expr(z)) for y, z in
       [("0", "0"), ("b", "0"), ("b", "h"), ("0", "h")]]
res = compute_section(pts)            # symbolisch: res.I_y == b*h**3/12
num = res.numeric(b=0.3, h=0.5)       # Zahlenwerte
print(compute_stress(num, M_y=0.1, M_z=0, N=0).sigma_max)
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```
