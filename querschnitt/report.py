"""Berichte: Klartext (Zwischenablage) und PDF (über Qt)."""

from __future__ import annotations

import base64
import datetime as _dt
import html
import io

from matplotlib.figure import Figure

from .core import NumericSection, SectionResult, StressResult
from .formatting import fmt, to_latex, to_plain
from .plotting import draw_section, draw_stress

LABELS = [
    ("A", "A", "m²"), ("y_S", "y_S", "m"), ("z_S", "z_S", "m"),
    ("I_y", "I_y", "m⁴"), ("I_z", "I_z", "m⁴"), ("I_yz", "I_yz", "m⁴"),
    ("I_1", "I_1", "m⁴"), ("I_2", "I_2", "m⁴"), ("tan_2theta", "tan 2θ", ""),
]


def text_report(title: str, names, res: SectionResult, num: NumericSection,
                stress: StressResult | None) -> str:
    lines = [f"Querschnittsberechnung{' – ' + title if title else ''}",
             f"b = {fmt(num.b)} m, h = {fmt(num.h)} m", "",
             "Eckpunkte (y, z):"]
    for n, (ye, ze), (y, z) in zip(names, res.points, num.points):
        lines.append(f"  {n:>3}:  y = {to_plain(ye)} = {fmt(y)} m,   "
                     f"z = {to_plain(ze)} = {fmt(z)} m")
    lines += ["", "Querschnittswerte (bezogen auf S):"]
    for key, sym, unit in LABELS:
        expr = getattr(res, key)
        lines.append(f"  {sym:<7}= {to_plain(expr)}  =  {fmt(getattr(num, key))} {unit}".rstrip())
    lines.append(f"  {'θ':<7}= {fmt(num.theta_deg, 5)}°")
    if stress:
        lines += ["", f"Normalspannungen (M_y = {fmt(stress.M_y)} MNm, "
                      f"M_z = {fmt(stress.M_z)} MNm, N = {fmt(stress.N)} MN):"]
        for n, s in zip(names, stress.vertex_sigma):
            lines.append(f"  σ({n}) = {fmt(s, 6, signed=True)} MN/m²")
        lines += [f"  σ_max = {fmt(stress.sigma_max, 6, signed=True)} MN/m²",
                  f"  σ_min = {fmt(stress.sigma_min, 6, signed=True)} MN/m²"]
    return "\n".join(lines)


# ─── PDF ────────────────────────────────────────────────────────────────────

class _PrintColors:
    surface = "#ffffff"
    border = "#d5d9df"
    text = "#1b2330"
    muted = "#5d6673"
    accent = "#2b5fd9"
    grid = "#eceef1"
    tension = "#b03024"
    compression = "#1f5c9e"
    axis1 = "#c26a00"
    axis2 = "#6d33d6"


def _fig_png(draw, *args, size=(6.4, 4.4)) -> str:
    fig = Figure(figsize=size, dpi=200)
    draw(fig, _PrintColors, *args)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    return base64.b64encode(buf.getvalue()).decode()


def _math_png(tex: str) -> str:
    from matplotlib import mathtext
    from matplotlib.font_manager import FontProperties
    buf = io.BytesIO()
    mathtext.math_to_image(f"${tex}$", buf, prop=FontProperties(size=10, math_fontfamily="dejavusans"),
                           dpi=300, format="png", color=_PrintColors.text)
    return base64.b64encode(buf.getvalue()).decode()


def html_report(title: str, names, res: SectionResult, num: NumericSection,
                stress: StressResult | None) -> tuple[str, dict[str, str]]:
    """HTML für QTextDocument; Bilder werden als Ressourcen (base64-PNG) geliefert."""
    images = {"section.png": _fig_png(draw_section, list(names), num.points, num)}
    if stress:
        images["stress.png"] = _fig_png(draw_stress, list(names), num, stress)

    e = html.escape
    rows_pts = "".join(
        f"<tr><td><b>{e(n)}</b></td><td>{e(to_plain(ye))}</td><td align=right>{fmt(y)}</td>"
        f"<td>&nbsp;&nbsp;{e(to_plain(ze))}</td><td align=right>{fmt(z)}</td></tr>"
        for n, (ye, ze), (y, z) in zip(names, res.points, num.points))

    rows_res = ""
    for key, sym, unit in LABELS:
        expr = getattr(res, key)
        name = f"f_{key}.png"
        formula = ""
        if key not in ("I_1", "I_2"):
            try:
                images[name] = _math_png(to_latex(expr))
                formula = f'<img src="{name}" height="{_img_height(images[name])}">'
            except Exception:
                formula = e(to_plain(expr))
        rows_res += (f"<tr><td width=60><b>{_HTML_SYM.get(key, e(sym))}</b></td>"
                     f"<td width=200>{formula}</td>"
                     f"<td width=110 align=right><b>{fmt(getattr(num, key))}</b></td>"
                     f"<td width=40>&nbsp;{unit}</td></tr>")
    rows_res += ("<tr><td><b>θ</b></td><td></td>"
                 f"<td align=right><b>{fmt(num.theta_deg, 5)}</b></td><td>&nbsp;°</td></tr>")

    stress_html = ""
    if stress:
        rows_s = "".join(
            f"<tr><td width=60><b>{e(n)}</b></td><td width=90 align=right>{fmt(y)}</td>"
            f"<td width=90 align=right>{fmt(z)}</td>"
            f"<td width=120 align=right>{fmt(s, 6, signed=True)}</td></tr>"
            for n, (y, z), s in zip(names, num.points, stress.vertex_sigma))
        stress_html = f"""
        <h2 style="page-break-before: always">Normalspannungen</h2>
        <p>M<sub>y</sub> = {fmt(stress.M_y)} MNm, &nbsp; M<sub>z</sub> = {fmt(stress.M_z)} MNm,
           &nbsp; N = {fmt(stress.N)} MN</p>
        <table cellpadding=3 cellspacing=0>
          <tr><th align=left>Punkt</th><th align=right>y [m]</th><th align=right>z [m]</th>
              <th align=right>σ [MN/m²]</th></tr>{rows_s}
        </table>
        <p><b>σ<sub>max</sub> = {fmt(stress.sigma_max, 6, signed=True)} MN/m²</b> &nbsp;&nbsp;
           <b>σ<sub>min</sub> = {fmt(stress.sigma_min, 6, signed=True)} MN/m²</b><br>
           <span class=muted>Positive Werte = Zug, negative Werte = Druck.</span></p>
        <p align=center><img src="stress.png" width="480"></p>"""

    today = _dt.date.today().strftime("%d.%m.%Y")
    doc = f"""
    <html><head><style>
      body {{ font-family: 'DejaVu Sans', sans-serif; font-size: 9pt; color: #1b2330; }}
      h1 {{ font-size: 17pt; margin-bottom: 0; }}
      h2 {{ font-size: 11pt; margin-top: 18px; margin-bottom: 6px; color: #2b5fd9; }}
      .muted {{ color: #5d6673; }}
      th {{ color: #5d6673; font-weight: 600; }}
    </style></head><body>
      <h1>Querschnittsberechnung</h1>
      <p class=muted>{e(title) + ' · ' if title else ''}erstellt am {today}</p>
      <h2>Eingabe</h2>
      <p>b = {fmt(num.b)} m, &nbsp; h = {fmt(num.h)} m</p>
      <table cellpadding=3 cellspacing=0>
        <tr><th align=left width=60>Punkt</th><th align=left width=90>y</th>
            <th align=right width=60>[m]</th><th align=left width=90>&nbsp;&nbsp;z</th>
            <th align=right width=60>[m]</th></tr>{rows_pts}
      </table>
      <p align=center><img src="section.png" width="400"></p>
      <h2>Querschnittswerte (bezogen auf den Schwerpunkt S)</h2>
      <table cellpadding=3 cellspacing=0>{rows_res}</table>
      <p class=muted>tan 2θ = 2·I<sub>yz</sub> / (I<sub>y</sub> − I<sub>z</sub>), θ = ½·arctan(tan 2θ);
         Vorzeichen: I<sub>yz</sub> = +∫yz dA.</p>
      {stress_html}
    </body></html>"""
    return doc, images


_HTML_SYM = {"y_S": "y<sub>S</sub>", "z_S": "z<sub>S</sub>", "I_y": "I<sub>y</sub>",
             "I_z": "I<sub>z</sub>", "I_yz": "I<sub>yz</sub>", "I_1": "I<sub>1</sub>",
             "I_2": "I<sub>2</sub>"}


def _img_height(b64: str) -> int:
    """Logische Höhe einer 300-dpi-Formelgrafik bei ~96 dpi Bildschirm."""
    import struct
    raw = base64.b64decode(b64)
    h = struct.unpack(">I", raw[20:24])[0]
    return max(10, round(h * 96 / 300))


def export_pdf(path: str, title: str, names, res, num, stress) -> None:
    """Schreibt den Bericht als A4-PDF (benötigt eine laufende QApplication)."""
    from PySide6.QtCore import QByteArray, QMarginsF, QUrl
    from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPdfWriter, QTextDocument

    doc_html, images = html_report(title, names, res, num, stress)
    doc = QTextDocument()
    for name, b64 in images.items():
        img = QImage.fromData(QByteArray(base64.b64decode(b64)), "PNG")
        doc.addResource(QTextDocument.ImageResource, QUrl(name), img)
    doc.setHtml(doc_html)

    writer = QPdfWriter(path)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait,
                                     QMarginsF(18, 16, 18, 16), QPageLayout.Millimeter))
    writer.setResolution(96)
    writer.setTitle(f"Querschnittsberechnung {title}".strip())
    writer.setCreator("Querschnittsberechnung")
    doc.setPageSize(writer.pageLayout().paintRectPixels(96).size().toSizeF())
    doc.print_(writer)
