#!/usr/bin/env python3
"""Querschnittsberechnung fuer allgemeine Polygone -- GUI"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sympy as sp
import numpy as np
import json
import math

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.path import Path as MplPath

b_sym, h_sym = sp.symbols('b h', positive=True)


# ─── Berechnung ───────────────────────────────────────────────────────────────

def parse_expr(s):
    s = s.strip().replace('^', '**')
    if not s:
        raise ValueError("Leerer Ausdruck")
    return sp.sympify(s, locals={'b': b_sym, 'h': h_sym, 'pi': sp.pi})


def compute_section(points):
    """
    Berechnet alle Querschnittswerte fuer ein Polygon.
    points: Liste von (y_sym, z_sym) -- Punkte im Gegenuhrzeigersinn eingeben.
    Gibt dict mit symbolischen Ausdruecken zurueck.
    """
    n = len(points)
    if n < 3:
        raise ValueError("Mindestens 3 Punkte benoetigt.")

    pts = points + [points[0]]

    d = [pts[i][0]*pts[i+1][1] - pts[i+1][0]*pts[i][1] for i in range(n)]

    A   = sp.simplify(sp.Rational(1, 2) * sum(d))
    y_S = sp.simplify(sum((pts[i][0] + pts[i+1][0]) * d[i] for i in range(n)) / (6*A))
    z_S = sp.simplify(sum((pts[i][1] + pts[i+1][1]) * d[i] for i in range(n)) / (6*A))

    I_y0  = sum((pts[i][1]**2 + pts[i][1]*pts[i+1][1] + pts[i+1][1]**2) * d[i]
                for i in range(n)) / 12
    I_z0  = sum((pts[i][0]**2 + pts[i][0]*pts[i+1][0] + pts[i+1][0]**2) * d[i]
                for i in range(n)) / 12
    I_yz0 = sum(d[i] * (2*pts[i][0]*pts[i][1]
                        + pts[i][0]*pts[i+1][1]
                        + pts[i+1][0]*pts[i][1]
                        + 2*pts[i+1][0]*pts[i+1][1])
                for i in range(n)) / 24

    I_y  = sp.simplify(I_y0  - A * z_S**2)
    I_z  = sp.simplify(I_z0  - A * y_S**2)
    I_yz = sp.simplify(I_yz0 - A * y_S * z_S)

    delta    = sp.sqrt(((I_y - I_z)/2)**2 + I_yz**2)
    I_1      = sp.simplify((I_y + I_z)/2 + delta)
    I_2      = sp.simplify((I_y + I_z)/2 - delta)
    try:
        tan_2th = sp.simplify(2 * I_yz / (I_y - I_z))
    except Exception:
        tan_2th = sp.oo

    return dict(A=A, y_S=y_S, z_S=z_S,
                I_y=I_y, I_z=I_z, I_yz=I_yz,
                I_1=I_1, I_2=I_2, tan_2theta=tan_2th)


def to_num(expr, b_val, h_val):
    return float(expr.subs([(b_sym, b_val), (h_sym, h_val)]))


def compute_stress(res, points, b_val, h_val, M_y_v, M_z_v, N_v):
    """Normalspannung an allen Eckpunkten."""
    A_n    = to_num(res['A'],   b_val, h_val)
    I_y_n  = to_num(res['I_y'],  b_val, h_val)
    I_z_n  = to_num(res['I_z'],  b_val, h_val)
    I_yz_n = to_num(res['I_yz'], b_val, h_val)
    y_S_n  = to_num(res['y_S'],  b_val, h_val)
    z_S_n  = to_num(res['z_S'],  b_val, h_val)
    det    = I_y_n * I_z_n - I_yz_n**2

    stresses = []
    for y_e, z_e in points:
        y_r = float(y_e.subs([(b_sym, b_val), (h_sym, h_val)])) - y_S_n
        z_r = float(z_e.subs([(b_sym, b_val), (h_sym, h_val)])) - z_S_n
        sigma = (N_v / A_n
                 + (M_z_v * I_y_n + M_y_v * I_yz_n) / det * y_r
                 - (M_y_v * I_z_n + M_z_v * I_yz_n) / det * z_r)
        stresses.append(sigma)
    return stresses


# ─── GUI ──────────────────────────────────────────────────────────────────────

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Querschnittsberechnung \u2013 Polygon")
        self.root.geometry("1400x800")
        self.root.minsize(1050, 650)

        self.rows      = []
        self._centroid = None
        self._cbar     = None

        self._build_ui()

        for name, y, z in [('A', '0',     '0'),
                            ('B', '3*b/2', '0'),
                            ('C', '3*b/2', 'h/3'),
                            ('D', 'b/2',   'h/3'),
                            ('E', 'b/2',   'h')]:
            self._add_row(name, y, z)

        self.root.mainloop()

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        ttk.Style().theme_use('clam')

        mb = tk.Menu(self.root)
        fm = tk.Menu(mb, tearoff=0)
        fm.add_command(label="Oeffnen...",   command=self._load, accelerator="Ctrl+O")
        fm.add_command(label="Speichern...", command=self._save, accelerator="Ctrl+S")
        fm.add_separator()
        fm.add_command(label="Beenden", command=self.root.quit)
        mb.add_cascade(label="Datei", menu=fm)
        self.root.config(menu=mb)
        self.root.bind('<Control-o>', lambda e: self._load())
        self.root.bind('<Control-s>', lambda e: self._save())

        pw = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        left   = ttk.Frame(pw, width=330)
        center = ttk.Frame(pw, width=330)
        right  = ttk.Frame(pw, width=700)
        for f in (left, center, right):
            f.pack_propagate(False)
        pw.add(left,   weight=1)
        pw.add(center, weight=1)
        pw.add(right,  weight=3)

        self._build_left(left)
        self._build_center(center)
        self._build_right(right)

    # ── Linke Spalte: Eingabe ────────────────────────────────────────────────

    def _build_left(self, p):
        lf = ttk.LabelFrame(p, text="Polygon-Punkte  (Gegenuhrzeigersinn)")
        lf.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        hdr = ttk.Frame(lf)
        hdr.pack(fill=tk.X, padx=6, pady=(4, 0))
        ttk.Label(hdr, text="Name",           width=6,  anchor='center').grid(row=0, column=0)
        ttk.Label(hdr, text="y  (Ausdruck)",  width=17, anchor='center').grid(row=0, column=1, padx=2)
        ttk.Label(hdr, text="z  (Ausdruck)",  width=17, anchor='center').grid(row=0, column=2, padx=2)
        ttk.Separator(lf).pack(fill=tk.X, padx=4, pady=2)

        cf = ttk.Frame(lf)
        cf.pack(fill=tk.BOTH, expand=True, padx=2)
        self._pts_canvas = tk.Canvas(cf, highlightthickness=0, height=200)
        sb = ttk.Scrollbar(cf, orient='vertical', command=self._pts_canvas.yview)
        self._rows_frame = ttk.Frame(self._pts_canvas)
        self._rows_frame.bind('<Configure>',
            lambda e: self._pts_canvas.configure(
                scrollregion=self._pts_canvas.bbox('all')))
        self._pts_canvas.create_window((0, 0), window=self._rows_frame, anchor='nw')
        self._pts_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._pts_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._pts_canvas.bind('<Enter>', lambda e: self._pts_canvas.bind_all(
            '<MouseWheel>',
            lambda ev: self._pts_canvas.yview_scroll(-1*(ev.delta//120), 'units')))
        self._pts_canvas.bind('<Leave>',
            lambda e: self._pts_canvas.unbind_all('<MouseWheel>'))

        bf = ttk.Frame(lf)
        bf.pack(pady=4)
        ttk.Button(bf, text="+ Punkt",       command=self._add_row,    width=13).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text="- Entfernen",   command=self._remove_row, width=13).pack(side=tk.LEFT)

        # Parameter
        pf = ttk.LabelFrame(p, text="Parameter  [m]")
        pf.pack(fill=tk.X, padx=4, pady=(0, 4))
        g = ttk.Frame(pf)
        g.pack(padx=8, pady=6)
        ttk.Label(g, text="b =").grid(row=0, column=0, sticky='e')
        self.b_var = tk.StringVar(value="2")
        ttk.Entry(g, textvariable=self.b_var, width=8).grid(row=0, column=1, padx=(2, 16))
        ttk.Label(g, text="h =").grid(row=0, column=2, sticky='e')
        self.h_var = tk.StringVar(value="3")
        ttk.Entry(g, textvariable=self.h_var, width=8).grid(row=0, column=3, padx=(2, 0))

        # Schnittgroessen
        sf = ttk.LabelFrame(p, text="Schnittgroessen  (fuer Spannungsberechnung)")
        sf.pack(fill=tk.X, padx=4, pady=(0, 4))
        g2 = ttk.Frame(sf)
        g2.pack(padx=8, pady=6)
        self.load_vars = []
        for row, (lbl, val) in enumerate([("M_y  [MNm] =", "50"),
                                           ("M_z  [MNm] =", "270"),
                                           ("N    [MN]  =", "400")]):
            ttk.Label(g2, text=lbl, anchor='e', width=14).grid(row=row, column=0, sticky='e', pady=2)
            v = tk.StringVar(value=val)
            ttk.Entry(g2, textvariable=v, width=10).grid(row=row, column=1, padx=(6, 0), pady=2)
            self.load_vars.append(v)

        ttk.Button(p, text="\u25b6  Berechnen", command=self._calculate,
                   width=24).pack(pady=8)

    # ── Mittlere Spalte: Polygon-Vorschau ────────────────────────────────────

    def _build_center(self, p):
        lf = ttk.LabelFrame(p, text="Polygon-Vorschau")
        lf.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.preview = tk.Canvas(lf, background='white',
                                  highlightthickness=1, highlightbackground='#bbb')
        self.preview.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        ttk.Button(p, text="Vorschau aktualisieren",
                   command=self._draw_preview).pack(pady=2)

    # ── Rechte Spalte: Tabs ──────────────────────────────────────────────────

    def _build_right(self, p):
        self._notebook = ttk.Notebook(p)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tab 1: Textergebnisse
        tab1 = ttk.Frame(self._notebook)
        self._notebook.add(tab1, text="  Ergebnisse  ")
        self._build_results_tab(tab1)

        # Tab 2: Spannungsverteilung
        tab2 = ttk.Frame(self._notebook)
        self._notebook.add(tab2, text="  Schiefe Biegung  ")
        self._build_stress_tab(tab2)

    def _build_results_tab(self, p):
        lf = ttk.LabelFrame(p, text="Berechnungsergebnisse")
        lf.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.result_text = tk.Text(
            lf, font=('Consolas', 10), wrap=tk.NONE,
            state=tk.DISABLED, background='#fafafa', relief=tk.FLAT)
        xsb = ttk.Scrollbar(lf, orient='horizontal', command=self.result_text.xview)
        ysb = ttk.Scrollbar(lf, orient='vertical',   command=self.result_text.yview)
        self.result_text.configure(xscrollcommand=xsb.set, yscrollcommand=ysb.set)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        xsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        ttk.Button(p, text="Ergebnisse kopieren", command=self._copy).pack(pady=2)

    def _build_stress_tab(self, p):
        self._stress_fig = Figure(figsize=(7, 6), dpi=96)
        self._stress_ax  = self._stress_fig.add_subplot(111)
        self._stress_ax.set_aspect('equal')
        self._stress_ax.text(0.5, 0.5,
                              'Noch keine Berechnung.\n\nBitte zuerst "Berechnen" druecken.',
                              ha='center', va='center',
                              transform=self._stress_ax.transAxes,
                              color='gray', fontsize=12)
        self._stress_ax.axis('off')

        canvas = FigureCanvasTkAgg(self._stress_fig, master=p)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, p)
        toolbar.update()
        self._stress_canvas = canvas

    # ── Punkte-Verwaltung ────────────────────────────────────────────────────

    def _add_row(self, name=None, y='', z=''):
        idx = len(self.rows)
        if name is None:
            name = chr(ord('A') + idx) if idx < 26 else f'P{idx+1}'
        frame = ttk.Frame(self._rows_frame)
        frame.pack(fill=tk.X, pady=1, padx=2)
        nv = tk.StringVar(value=name)
        yv = tk.StringVar(value=y)
        zv = tk.StringVar(value=z)
        ttk.Entry(frame, textvariable=nv, width=6,  justify='center').grid(row=0, column=0, padx=2)
        ttk.Entry(frame, textvariable=yv, width=17).grid(row=0, column=1, padx=2)
        ttk.Entry(frame, textvariable=zv, width=17).grid(row=0, column=2, padx=2)
        self.rows.append((nv, yv, zv, frame))

    def _remove_row(self):
        if len(self.rows) > 1:
            *_, frame = self.rows.pop()
            frame.destroy()

    # ── Polygon-Vorschau (tkinter Canvas) ────────────────────────────────────

    def _draw_preview(self):
        try:
            b_val = float(sp.sympify(self.b_var.get()))
            h_val = float(sp.sympify(self.h_var.get()))
        except Exception:
            return

        coords, labels = [], []
        for nv, yv, zv, _ in self.rows:
            try:
                y_n = float(parse_expr(yv.get()).subs([(b_sym, b_val), (h_sym, h_val)]))
                z_n = float(parse_expr(zv.get()).subs([(b_sym, b_val), (h_sym, h_val)]))
                coords.append((y_n, z_n))
                labels.append(nv.get())
            except Exception:
                return
        if len(coords) < 3:
            return

        self.preview.update_idletasks()
        W = self.preview.winfo_width()  or 300
        H = self.preview.winfo_height() or 300
        self.preview.delete('all')

        PAD = 45
        ys = [c[0] for c in coords]
        zs = [c[1] for c in coords]
        dy = (max(ys) - min(ys)) or 1
        dz = (max(zs) - min(zs)) or 1
        scale = min((W - 2*PAD) / dy, (H - 2*PAD) / dz)
        y_min, z_min = min(ys), min(zs)

        def to_cv(y, z):
            return (PAD + (y - y_min) * scale,
                    H - PAD - (z - z_min) * scale)

        flat = [v for y, z in coords for v in to_cv(y, z)]
        self.preview.create_polygon(flat, fill='#d6eaf8', outline='#2471a3', width=2)

        for (y, z), lbl in zip(coords, labels):
            cx, cy = to_cv(y, z)
            self.preview.create_oval(cx-4, cy-4, cx+4, cy+4, fill='#2471a3', outline='')
            self.preview.create_text(cx+8, cy-8, text=lbl,
                                      font=('Arial', 9, 'bold'), fill='#1a5276')

        if self._centroid:
            cx, cy = to_cv(*self._centroid)
            self.preview.create_oval(cx-5, cy-5, cx+5, cy+5,
                                      fill='red', outline='darkred', width=1)
            self.preview.create_text(cx+9, cy-9, text='S',
                                      font=('Arial', 9, 'bold'), fill='red')

        self.preview.create_text(W//2, H - 10, text='y \u2192', font=('Arial', 8), fill='#777')
        self.preview.create_text(12,   H//2,    text='z\n\u2191', font=('Arial', 8), fill='#777')

    # ── Spannungsvisualisierung (matplotlib) ──────────────────────────────────

    def _plot_stress(self, pts_num, names, res, b_val, h_val, M_y_v, M_z_v, N_v):
        # Numerische Werte
        A_n    = to_num(res['A'],   b_val, h_val)
        I_y_n  = to_num(res['I_y'],  b_val, h_val)
        I_z_n  = to_num(res['I_z'],  b_val, h_val)
        I_yz_n = to_num(res['I_yz'], b_val, h_val)
        y_S_n  = to_num(res['y_S'],  b_val, h_val)
        z_S_n  = to_num(res['z_S'],  b_val, h_val)
        I_1_n  = to_num(res['I_1'],  b_val, h_val)
        I_2_n  = to_num(res['I_2'],  b_val, h_val)

        # Koordinaten relativ zum Schwerpunkt S
        ys = [y - y_S_n for y, z in pts_num]
        zs = [z - z_S_n for y, z in pts_num]

        det = I_y_n * I_z_n - I_yz_n**2
        if abs(det) < 1e-14:
            messagebox.showwarning("Spannungsplot",
                "Determinante ~ 0: Querschnitt ist degeneriert (alle Punkte kollinear?).")
            return

        # Spannungskoeffizienten (TU-Graz-Konvention: My = -∫z·σ dA)
        # σ = N/A + (Mz·Iy + My·Iyz)/det · ỹ − (My·Iz + Mz·Iyz)/det · z̃
        Ay  =  (M_z_v * I_y_n + M_y_v * I_yz_n) / det
        Az  = -(M_y_v * I_z_n + M_z_v * I_yz_n) / det
        N_t = N_v / A_n

        # Feingitter ueber Bounding Box
        margin = 0.20
        y_min, y_max = min(ys), max(ys)
        z_min, z_max = min(zs), max(zs)
        dy = (y_max - y_min) or 1.0
        dz = (z_max - z_min) or 1.0
        N_GRID = 220
        y_g = np.linspace(y_min - margin*dy, y_max + margin*dy, N_GRID)
        z_g = np.linspace(z_min - margin*dz, z_max + margin*dz, N_GRID)
        YY, ZZ = np.meshgrid(y_g, z_g)

        # Punkte-im-Polygon-Test
        poly_verts = list(zip(ys, zs))
        poly_path  = MplPath(poly_verts + [poly_verts[0]])
        pts_flat   = np.column_stack([YY.ravel(), ZZ.ravel()])
        inside     = poly_path.contains_points(pts_flat).reshape(N_GRID, N_GRID)

        # Spannungsfeld
        SIGMA        = N_t + Az * ZZ + Ay * YY
        SIGMA_masked = np.where(inside, SIGMA, np.nan)

        vmax = np.nanmax(np.abs(SIGMA_masked))
        if vmax < 1e-10:
            vmax = 1.0

        # Eckpunkt-Spannungen
        sigma_pts = [N_t + Az*(z - z_S_n) + Ay*(y - y_S_n)
                     for y, z in pts_num]
        sigma_max = max(sigma_pts)
        sigma_min = min(sigma_pts)

        # ── Figure neu aufbauen ──────────────────────────────────────────────
        self._stress_fig.clear()
        ax = self._stress_fig.add_subplot(111)

        # Farbflaeche
        cf = ax.contourf(YY, ZZ, SIGMA_masked, levels=120,
                         cmap='RdBu_r', vmin=-vmax, vmax=vmax)

        # Nulllinie (Nullspannungslinie)
        try:
            cs0 = ax.contour(YY, ZZ, SIGMA_masked, levels=[0.0],
                             colors='black', linewidths=2.5, linestyles='--')
            ax.clabel(cs0, fmt='Nulllinie (\u03c3=0)', fontsize=8, inline=True,
                      manual=False)
        except Exception:
            pass

        # Polygonumriss
        ys_c = ys + [ys[0]]
        zs_c = zs + [zs[0]]
        ax.plot(ys_c, zs_c, 'k-', linewidth=2.5, zorder=5)

        # Eckpunkte mit Spannungswerten
        for y_r, z_r, lbl, sig in zip(ys, zs, names, sigma_pts):
            ax.plot(y_r, z_r, 'o', color='black', markersize=5, zorder=6)
            ax.annotate(
                f' {lbl}: {sig:+.2f}',
                xy=(y_r, z_r), fontsize=8, zorder=7,
                color='black',
                bbox=dict(boxstyle='round,pad=0.15', fc='white', alpha=0.75, lw=0))

        # Schwerpunkt S
        ax.plot(0, 0, marker='^', color='white', markersize=10, zorder=8,
                markeredgecolor='black', markeredgewidth=1.5,
                label=f'S  (y_S={y_S_n:.3f}, z_S={z_S_n:.3f}) m')

        # Koordinatenachsen y, z
        r_ax = max(dy, dz) * 0.28
        ax.annotate('', xy=(r_ax, 0), xytext=(0, 0),
                    arrowprops=dict(arrowstyle='->', color='white', lw=1.5, mutation_scale=12))
        ax.annotate('', xy=(0, r_ax), xytext=(0, 0),
                    arrowprops=dict(arrowstyle='->', color='white', lw=1.5, mutation_scale=12))
        ax.text(r_ax * 1.08, 0,      'y', color='white', fontsize=9,
                fontweight='bold', ha='left',   va='center')
        ax.text(0,      r_ax * 1.08, 'z', color='white', fontsize=9,
                fontweight='bold', ha='center', va='bottom')

        # Hauptachsen xi_1, xi_2
        try:
            tan2t = to_num(res['tan_2theta'], b_val, h_val)
            theta = math.atan(tan2t) / 2

            # Bestimme welcher Winkel zu I_1 gehoert
            I_y1 = (I_y_n + I_z_n)/2 + (I_y_n - I_z_n)/2 * math.cos(2*theta) - I_yz_n * math.sin(2*theta)
            # I_y1 nahe I_1 -> theta gehoert zu Hauptachse 1
            if abs(I_y1 - I_1_n) < abs(I_y1 - I_2_n):
                th1, th2 = theta, theta + math.pi/2
                axes_info = [(th1, '\u03be\u2081', I_1_n, '#FFD700'),
                             (th2, '\u03be\u2082', I_2_n, '#FFA500')]
            else:
                th1, th2 = theta, theta + math.pi/2
                axes_info = [(th1, '\u03be\u2082', I_2_n, '#FFA500'),
                             (th2, '\u03be\u2081', I_1_n, '#FFD700')]

            r_pa = max(dy, dz) * 0.60
            for th_pa, lbl_pa, I_pa, col in axes_info:
                dy_pa = r_pa * math.cos(th_pa)
                dz_pa = r_pa * math.sin(th_pa)
                ax.annotate('', xy=(dy_pa, dz_pa), xytext=(0, 0),
                            arrowprops=dict(arrowstyle='->', color=col,
                                            lw=2.5, mutation_scale=14))
                ax.annotate('', xy=(-dy_pa, -dz_pa), xytext=(0, 0),
                            arrowprops=dict(arrowstyle='->', color=col,
                                            lw=2.5, mutation_scale=14))
                offset = 1.14
                ax.text(dy_pa*offset, dz_pa*offset,
                        f'{lbl_pa}\nI={I_pa:.3f} m\u2074',
                        color=col, fontsize=8, fontweight='bold',
                        ha='center', va='center')
        except Exception:
            pass

        # Colorbar
        cbar = self._stress_fig.colorbar(cf, ax=ax,
                                          label='\u03c3  [MN/m\u00b2]',
                                          fraction=0.035, pad=0.03)
        cbar.ax.tick_params(labelsize=8)

        # Achsen + Titel
        ax.set_xlabel('y  [m]', fontsize=10)
        ax.set_ylabel('z  [m]', fontsize=10)
        ax.set_aspect('equal', 'box')

        theta_deg = math.degrees(math.atan(to_num(res['tan_2theta'], b_val, h_val)) / 2) \
            if True else 0.0
        ax.set_title(
            f'Schiefe Biegung  |  '
            f'\u03c3_max = {sigma_max:+.3f}  |  \u03c3_min = {sigma_min:+.3f}  [MN/m\u00b2]  |  '
            f'\u03b8 = {theta_deg:.2f}\u00b0',
            fontsize=10, pad=8)
        ax.legend(loc='upper left', fontsize=8, framealpha=0.8)
        ax.grid(True, alpha=0.25, linewidth=0.5)

        self._stress_fig.tight_layout()
        self._stress_canvas.draw()

    # ── Berechnung ───────────────────────────────────────────────────────────

    def _calculate(self):
        points_sym, names, errors = [], [], []
        for nv, yv, zv, _ in self.rows:
            name = nv.get().strip() or '?'
            try:
                points_sym.append((parse_expr(yv.get()), parse_expr(zv.get())))
                names.append(name)
            except Exception as e:
                errors.append(f"Punkt {name}: {e}")

        if errors:
            messagebox.showerror("Eingabefehler", "\n".join(errors))
            return
        if len(points_sym) < 3:
            messagebox.showerror("Fehler", "Mindestens 3 Punkte erforderlich.")
            return

        try:
            b_val = float(sp.sympify(self.b_var.get()))
            h_val = float(sp.sympify(self.h_var.get()))
        except Exception:
            messagebox.showerror("Fehler", "Ungueltige Werte fuer b oder h.")
            return

        try:
            res = compute_section(points_sym)
        except Exception as e:
            messagebox.showerror("Berechnungsfehler", str(e))
            return

        # Schwerpunkt fuer Vorschau
        try:
            self._centroid = (to_num(res['y_S'], b_val, h_val),
                              to_num(res['z_S'], b_val, h_val))
        except Exception:
            self._centroid = None

        # ── Textergebnisse ────────────────────────────────────────────────────
        subs = [(b_sym, b_val), (h_sym, h_val)]

        def sym(expr):
            return str(sp.simplify(expr))

        def nf(expr, unit=''):
            try:
                v = to_num(expr, b_val, h_val)
                return f"{v:.5f}" + (f"  [{unit}]" if unit else '')
            except Exception:
                return "–"

        lines = [
            "=" * 64,
            "  QUERSCHNITTSWERTE",
            "=" * 64,
            f"\n  Parameter:  b = {b_val} m,  h = {h_val} m",
            "\n  Eingabepunkte (y, z):"]
        for name, (y_e, z_e) in zip(names, points_sym):
            yn = float(y_e.subs(subs))
            zn = float(z_e.subs(subs))
            lines.append(
                f"    {name:>4}:  y = {str(y_e):>14}  =  {yn:8.4f} m"
                f"    z = {str(z_e):>14}  =  {zn:8.4f} m")

        lines += [
            "\n" + "-"*64,
            "  a)  Flaeche",
            f"      A  =  {sym(res['A'])}",
            f"         =  {nf(res['A'], 'm^2')}",
            "\n  b)  Schwerpunkt",
            f"      y_S  =  {sym(res['y_S'])}",
            f"           =  {nf(res['y_S'], 'm')}",
            f"      z_S  =  {sym(res['z_S'])}",
            f"           =  {nf(res['z_S'], 'm')}",
            "\n  c)  Flaechentraegheitsmomente (bezogen auf S)",
            f"      I_y   =  {sym(res['I_y'])}",
            f"            =  {nf(res['I_y'], 'm^4')}",
            f"      I_z   =  {sym(res['I_z'])}",
            f"            =  {nf(res['I_z'], 'm^4')}",
            f"      I_yz  =  {sym(res['I_yz'])}",
            f"            =  {nf(res['I_yz'], 'm^4')}",
            "\n  d)  Haupttraegheitsmomente",
            f"      I_1  =  {nf(res['I_1'], 'm^4')}",
            f"      I_2  =  {nf(res['I_2'], 'm^4')}",
            "\n  e)  Verdrehung Koordinatensystem",
            f"      tan(2*theta)  =  {nf(res['tan_2theta'])}"]

        try:
            tan2t = to_num(res['tan_2theta'], b_val, h_val)
            theta_deg = math.degrees(math.atan(tan2t) / 2)
            lines.append(f"      theta         =  {theta_deg:.4f} Grad")
        except Exception:
            pass

        # Normalspannungen
        try:
            M_y_v = float(self.load_vars[0].get())
            M_z_v = float(self.load_vars[1].get())
            N_v   = float(self.load_vars[2].get())
            stresses = compute_stress(res, points_sym, b_val, h_val, M_y_v, M_z_v, N_v)

            lines += [
                "\n  f+g)  Normalspannungen an den Eckpunkten",
                f"        M_y={M_y_v} MNm,  M_z={M_z_v} MNm,  N={N_v} MN",
                "        sigma = N/A + (Mz*Iy + My*Iyz)/det * y~",
                "                    - (My*Iz + Mz*Iyz)/det * z~"]
            for name, sig in zip(names, stresses):
                lines.append(f"        sigma({name:>3})  =  {sig:+.5f} MN/m^2")
            lines += [
                f"\n        sigma_max  =  {max(stresses):+.5f} MN/m^2",
                f"        sigma_min  =  {min(stresses):+.5f} MN/m^2"]

        except Exception as e:
            lines.append(f"\n  Spannungsberechnung: Fehler - {e}")
            M_y_v = M_z_v = N_v = 0.0

        lines.append("\n" + "=" * 64)

        # Ausgabe
        self._show_results("\n".join(lines))
        self._draw_preview()

        # Spannungsplot
        pts_num = [(float(y_e.subs(subs)), float(z_e.subs(subs)))
                   for y_e, z_e in points_sym]
        try:
            self._plot_stress(pts_num, names, res, b_val, h_val,
                              M_y_v, M_z_v, N_v)
            self._notebook.select(1)   # direkt zur Spannungsdarstellung
        except Exception as e:
            messagebox.showwarning("Spannungsplot",
                                    f"Diagramm konnte nicht erstellt werden:\n{e}")

    def _show_results(self, text):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', text)
        self.result_text.config(state=tk.DISABLED)

    def _copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.result_text.get('1.0', tk.END))

    # ── Speichern / Laden ────────────────────────────────────────────────────

    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON-Datei', '*.json'), ('Alle', '*.*')],
            title="Speichern unter...")
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                'b': self.b_var.get(), 'h': self.h_var.get(),
                'loads': [v.get() for v in self.load_vars],
                'points': [(r[0].get(), r[1].get(), r[2].get()) for r in self.rows]
            }, f, indent=2, ensure_ascii=False)

    def _load(self):
        path = filedialog.askopenfilename(
            filetypes=[('JSON-Datei', '*.json'), ('Alle', '*.*')],
            title="Oeffnen...")
        if not path:
            return
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        for _, _, _, frame in self.rows:
            frame.destroy()
        self.rows.clear()
        self.b_var.set(data.get('b', '1'))
        self.h_var.set(data.get('h', '1'))
        for v, val in zip(self.load_vars, data.get('loads', ['0', '0', '0'])):
            v.set(val)
        for name, y, z in data.get('points', []):
            self._add_row(name, y, z)


if __name__ == '__main__':
    App()
