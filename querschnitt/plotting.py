"""Diagramme mit matplotlib: Querschnitt (mit Hauptachsen) und Spannungsfeld.

Die Funktionen zeichnen in eine übergebene ``Figure`` und werden sowohl von
der GUI als auch vom PDF-Bericht verwendet.
"""

from __future__ import annotations

import math

import matplotlib as mpl
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.figure import Figure
from matplotlib.path import Path as MplPath
from matplotlib.ticker import FuncFormatter

from .core import NumericSection, StressResult
from .formatting import fmt

_tick_fmt = FuncFormatter(lambda v, _pos: fmt(v, 4))


def _prepare(fig: Figure, colors) -> "mpl.axes.Axes":
    fig.clear()
    fig.set_facecolor(colors.surface)
    ax = fig.add_subplot(111)
    ax.set_facecolor(colors.surface)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(colors.border)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=colors.muted, labelsize=8)
    ax.xaxis.set_major_formatter(_tick_fmt)
    ax.yaxis.set_major_formatter(_tick_fmt)
    ax.set_xlabel("y  [m]", color=colors.muted, fontsize=9)
    ax.set_ylabel("z  [m]", color=colors.muted, fontsize=9)
    ax.grid(True, color=colors.grid, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_aspect("equal", adjustable="datalim")
    return ax


def draw_placeholder(fig: Figure, colors, message: str) -> None:
    fig.clear()
    fig.set_facecolor(colors.surface)
    fig.text(0.5, 0.5, message, ha="center", va="center", color=colors.muted, fontsize=11)


def _extent(coords):
    ys = [c[0] for c in coords]
    zs = [c[1] for c in coords]
    return min(ys), max(ys), min(zs), max(zs)


def _set_limits(ax, coords, margin=0.18):
    """Datenbereich + Rand festlegen; das gleiche Seitenverhältnis (aspect=equal,
    adjustable=datalim) erweitert dann eine Richtung passend zur Zeichenfläche."""
    y0, y1, z0, z1 = _extent(coords)
    span = max(y1 - y0, z1 - z0) or 1.0
    ax.update_datalim([(y0 - margin * span, z0 - margin * span),
                       (y1 + margin * span, z1 + margin * span)])
    ax.autoscale_view()
    return span


def _label_offsets(coords):
    """Richtung (in Punkten) für Eckpunkt-Beschriftungen: vom Mittelpunkt weg."""
    cy = sum(c[0] for c in coords) / len(coords)
    cz = sum(c[1] for c in coords) / len(coords)
    out = []
    for y, z in coords:
        dy, dz = y - cy, z - cz
        r = math.hypot(dy, dz) or 1.0
        out.append((dy / r, dz / r))
    return out


def draw_section(fig: Figure, colors, names: list[str], coords: list[tuple[float, float]],
                 sec: NumericSection | None = None) -> None:
    """Polygon mit Eckpunkten; mit ``sec`` zusätzlich Schwerpunkt und Hauptachsen."""
    ax = _prepare(fig, colors)
    span = _set_limits(ax, coords)

    closed = coords + [coords[0]]
    ax.fill([c[0] for c in coords], [c[1] for c in coords],
            color=colors.accent, alpha=0.13, zorder=2, linewidth=0)
    ax.plot([c[0] for c in closed], [c[1] for c in closed],
            color=colors.accent, linewidth=2, zorder=3, solid_joinstyle="round")
    ax.scatter([c[0] for c in coords], [c[1] for c in coords], s=26, zorder=4,
               color=colors.surface, edgecolors=colors.accent, linewidths=1.8)

    for (y, z), name, (ox, oz) in zip(coords, names, _label_offsets(coords)):
        ax.annotate(name, (y, z), xytext=(ox * 11, oz * 11), textcoords="offset points",
                    ha="center", va="center", fontsize=9.5, fontweight="bold",
                    color=colors.text, zorder=6)

    if sec is not None:
        S = (sec.y_S, sec.z_S)
        # lokale Achsen y, z im Schwerpunkt
        r = 0.16 * span
        for (dy, dz), lbl in (((r, 0), "y"), ((0, r), "z")):
            ax.annotate("", xy=(S[0] + dy, S[1] + dz), xytext=S, zorder=7,
                        arrowprops=dict(arrowstyle="-|>", color=colors.muted, lw=1.3,
                                        mutation_scale=11, shrinkA=0, shrinkB=0))
            ax.annotate(lbl, (S[0] + dy, S[1] + dz), xytext=(5 if dy else 0, 5 if dz else -1),
                        textcoords="offset points", fontsize=9, color=colors.muted,
                        ha="left" if dy else "center", va="center" if dy else "bottom",
                        fontstyle="italic", zorder=7)

        # Hauptachsen ξ₁ / ξ₂
        if not sec.is_principal_isotropic:
            a1 = sec.principal_angle_1
            L = 0.62 * span
            for ang, lbl, col in ((a1, "ξ₁", colors.axis1),
                                  (a1 + math.pi / 2, "ξ₂", colors.axis2)):
                dy, dz = L * math.cos(ang), L * math.sin(ang)
                ax.plot([S[0] - dy, S[0] + dy], [S[1] - dz, S[1] + dz], color=col,
                        linewidth=1.4, linestyle=(0, (6, 3)), zorder=5)
                ax.annotate(lbl, (S[0] + dy, S[1] + dz), xytext=(math.cos(ang) * 9,
                            math.sin(ang) * 9), textcoords="offset points", color=col,
                            fontsize=10, fontweight="bold", ha="center", va="center",
                            zorder=7)

        ax.scatter([S[0]], [S[1]], s=70, marker="o", color=colors.surface,
                   edgecolors=colors.text, linewidths=1.6, zorder=8)
        ax.scatter([S[0]], [S[1]], s=10, marker="o", color=colors.text, zorder=9)
        ax.annotate("S", S, xytext=(-8, -9), textcoords="offset points", fontsize=10,
                    fontweight="bold", color=colors.text, ha="center", va="center", zorder=9)

    fig.tight_layout(pad=1.2)


def draw_stress(fig: Figure, colors, names: list[str], sec: NumericSection,
                stress: StressResult, cmap: str = "RdBu_r", grid: int = 320) -> None:
    """Farbkarte der Normalspannung mit Nulllinie und Eckpunktwerten."""
    ax = _prepare(fig, colors)
    coords = sec.points
    y0, y1, z0, z1 = _extent(coords)

    ys = np.linspace(y0, y1, grid)
    zs = np.linspace(z0, z1, grid)
    Y, Z = np.meshgrid(ys, zs)
    inside = MplPath(coords + [coords[0]]).contains_points(
        np.column_stack([Y.ravel(), Z.ravel()]), radius=1e-9).reshape(Y.shape)
    sigma = stress.sigma(Y - sec.y_S, Z - sec.z_S)
    field = np.ma.masked_where(~inside, sigma)

    vmax = max(abs(stress.sigma_max), abs(stress.sigma_min), 1e-12)
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    img = ax.imshow(field, extent=(y0, y1, z0, z1), origin="lower", cmap=cmap, norm=norm,
                    interpolation="bilinear", zorder=2)
    ax.set_aspect("equal", adjustable="datalim")
    _set_limits(ax, coords, margin=0.2)

    closed = coords + [coords[0]]
    ax.plot([c[0] for c in closed], [c[1] for c in closed], color=colors.text,
            linewidth=1.6, zorder=4)

    # Nulllinie  σ_N + k_y·ỹ + k_z·z̃ = 0
    if stress.has_neutral_axis:
        k2 = stress.k_y ** 2 + stress.k_z ** 2
        p0 = (sec.y_S - stress.sigma_N * stress.k_y / k2,
              sec.z_S - stress.sigma_N * stress.k_z / k2)
        p1 = (p0[0] - stress.k_z, p0[1] + stress.k_y)
        ax.axline(p0, p1, color=colors.text, linewidth=1.4, linestyle=(0, (5, 3)),
                  zorder=5, label="Nulllinie  σ = 0")
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=8,
                  labelcolor=colors.muted, handlelength=2.6, frameon=False, borderaxespad=0.2)

    ax.scatter([sec.y_S], [sec.z_S], s=46, marker="o", color=colors.surface,
               edgecolors=colors.text, linewidths=1.4, zorder=8)
    ax.annotate("S", (sec.y_S, sec.z_S), xytext=(-8, -9), textcoords="offset points",
                fontsize=9.5, fontweight="bold", color=colors.text, ha="center", va="center",
                zorder=9)

    i_max = int(np.argmax(stress.vertex_sigma))
    i_min = int(np.argmin(stress.vertex_sigma))
    for i, ((y, z), name, (ox, oz), s) in enumerate(
            zip(coords, names, _label_offsets(coords), stress.vertex_sigma)):
        col = colors.tension if s > 0 else colors.compression if s < 0 else colors.muted
        strong = i in (i_max, i_min)
        ax.scatter([y], [z], s=30 if strong else 18, color=col, edgecolors=colors.surface,
                   linewidths=1, zorder=7)
        ax.annotate(f"{name}  {fmt(s, 4, signed=True)}", (y, z),
                    xytext=(ox * 16, oz * 14), textcoords="offset points",
                    ha="left" if ox > 0.3 else "right" if ox < -0.3 else "center",
                    va="center", fontsize=8.5, color=col,
                    fontweight="bold" if strong else "normal", zorder=9,
                    bbox=dict(boxstyle="round,pad=0.25", fc=colors.surface, ec=col,
                              lw=0.8 if strong else 0, alpha=0.92))

    cbar = fig.colorbar(img, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("σ  [MN/m²]", color=colors.muted, fontsize=9)
    cbar.ax.yaxis.set_major_formatter(_tick_fmt)
    cbar.ax.tick_params(colors=colors.muted, labelsize=8)
    cbar.outline.set_edgecolor(colors.border)

    fig.tight_layout(pad=1.2)
