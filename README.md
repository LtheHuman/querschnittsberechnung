# Querschnittsberechnung – Polygon

GUI-Anwendung zur symbolischen und numerischen Berechnung von Querschnittswerten beliebiger Polygone (Baumechanik 2, TU Graz).

## Funktionen

- Symbolische Eingabe der Eckpunkte (Ausdrücke mit `b` und `h`)
- Berechnung von: **A, y_S, z_S, I_y, I_z, I_yz, I_1, I_2, tan(2θ)**
- Spannungsberechnung (schiefe Biegung): **σ_max, σ_min** an allen Eckpunkten
- Polygon-Vorschau mit Schwerpunkt
- Farbkarte der Spannungsverteilung mit Nulllinie und Hauptachsen
- Speichern/Laden als JSON

## Voraussetzungen

Python 3.10+ sowie folgende Pakete:

```
pip install -r requirements.txt
```

## Starten

```
python querschnitt_gui.py
```

## Bedienung

1. **Polygon-Punkte** eintragen (Gegenuhrzeigersinn, Ausdrücke wie `3*b/2`, `h/3`)
2. **Parameter** b und h (numerische Werte in Metern) eingeben
3. **Schnittgrößen** M_y, M_z, N eintragen
4. **„Berechnen"** klicken → Ergebnisse + Spannungsdiagramm erscheinen automatisch

## Vorzeichenkonvention (TU Graz BM2)

- **M_y > 0** → Druck auf der z > z_S Seite (M_y = −∫z·σ dA)
- **M_z > 0** → Zug auf der y > y_S Seite (M_z = +∫y·σ dA)

Spannungsformel:

```
σ = N/A + (Mz·Iy + My·Iyz) / (Iy·Iz − Iyz²) · ỹ
        − (My·Iz + Mz·Iyz) / (Iy·Iz − Iyz²) · z̃
```
