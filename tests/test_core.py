"""Tests des Rechenkerns gegen bekannte Lösungen."""

import math

import numpy as np
import pytest
import sympy as sp
from matplotlib.path import Path as MplPath

from querschnitt.core import (InputError, b_sym as b, compute_section, compute_stress,
                              h_sym as h, parse_expr, parse_number)
from querschnitt.formatting import fmt
from querschnitt.project import Project, Vertex


def section(*pts, check=(2.0, 3.0)):
    return compute_section([(parse_expr(y), parse_expr(z)) for y, z in pts], check_values=check)


# ─── Eingabe ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text, expected", [
    ("3*b/2", 3 * b / 2), ("h^2", h ** 2), ("1,5*b", sp.Rational(3, 2) * b),
    (" −b ", -b), ("sqrt(2)*h", sp.sqrt(2) * h),
])
def test_parse_expr(text, expected):
    assert sp.simplify(parse_expr(text) - expected) == 0


@pytest.mark.parametrize("text", ["", "x", "b+", "import os", "b == h"])
def test_parse_expr_rejects(text):
    with pytest.raises(InputError):
        parse_expr(text)


def test_parse_number():
    assert parse_number("2,5") == 2.5
    assert parse_number("3/2") == 1.5
    with pytest.raises(InputError):
        parse_number("b")


# ─── Querschnittswerte ──────────────────────────────────────────────────────

def test_rectangle():
    r = section(("0", "0"), ("b", "0"), ("b", "h"), ("0", "h"))
    assert sp.simplify(r.A - b * h) == 0
    assert sp.simplify(r.y_S - b / 2) == 0 and sp.simplify(r.z_S - h / 2) == 0
    assert sp.simplify(r.I_y - b * h ** 3 / 12) == 0
    assert sp.simplify(r.I_z - b ** 3 * h / 12) == 0
    assert r.I_yz == 0


def test_right_triangle_product_moment():
    # rechtwinkeliges Dreieck: I_yz = −b²h²/72 bezogen auf S (mit I_yz = +∫yz dA)
    r = section(("0", "0"), ("b", "0"), ("0", "h"))
    assert sp.simplify(r.A - b * h / 2) == 0
    assert sp.simplify(r.I_y - b * h ** 3 / 36) == 0
    assert sp.simplify(r.I_yz + b ** 2 * h ** 2 / 72) == 0


def test_clockwise_input_is_reversed():
    r = section(("0", "0"), ("0", "h"), ("b", "h"), ("b", "0"))
    assert r.reversed_input
    assert sp.simplify(r.A - b * h) == 0
    assert sp.simplify(r.I_y - b * h ** 3 / 12) == 0


def test_self_intersection_rejected():
    with pytest.raises(InputError, match="überschneidet"):
        section(("0", "0"), ("b", "h"), ("b", "0"), ("0", "h"))


def test_too_few_points():
    with pytest.raises(InputError):
        section(("0", "0"), ("b", "0"))


def test_bm2_assignment_2026():
    """Querschnitt der BM2-Aufgabe 2026 (Beispieldatei)."""
    p = Project.example()
    r = section(*[(v.y, v.z) for v in p.vertices])
    assert sp.simplify(r.A - 6 * b * h) == 0
    assert sp.simplify(r.y_S - sp.Rational(65, 48) * b) == 0
    assert sp.simplify(r.z_S - sp.Rational(5, 4) * h) == 0
    assert sp.simplify(r.I_y - sp.Rational(25, 8) * b * h ** 3) == 0
    assert sp.simplify(r.I_z - sp.Rational(1151, 384) * b ** 3 * h) == 0
    assert sp.simplify(r.I_yz + sp.Rational(3, 32) * b ** 2 * h ** 2) == 0


def _grid_moments(coords, n=1500):
    """Unabhängige Kontrolle per Rasterintegration."""
    ys, zs = zip(*coords)
    yg = np.linspace(min(ys), max(ys), n)
    zg = np.linspace(min(zs), max(zs), n)
    Y, Z = np.meshgrid(yg, zg)
    dA = (yg[1] - yg[0]) * (zg[1] - zg[0])
    m = MplPath(coords).contains_points(np.c_[Y.ravel(), Z.ravel()]).reshape(Y.shape)
    A = m.sum() * dA
    yS, zS = (Y * m).sum() * dA / A, (Z * m).sum() * dA / A
    Iy = ((Z - zS) ** 2 * m).sum() * dA
    Iz = ((Y - yS) ** 2 * m).sum() * dA
    Iyz = ((Y - yS) * (Z - zS) * m).sum() * dA
    return A, yS, zS, Iy, Iz, Iyz


def test_against_numerical_integration():
    pts = [("0", "0"), ("2*b", "0"), ("3*b", "h"), ("5*b/2", "2*h"), ("b/2", "3*h")]
    num = section(*pts).numeric(2.0, 3.0)
    A, yS, zS, Iy, Iz, Iyz = _grid_moments(num.points)
    assert num.A == pytest.approx(A, rel=2e-3)
    assert num.y_S == pytest.approx(yS, rel=2e-3)
    assert num.I_y == pytest.approx(Iy, rel=5e-3)
    assert num.I_z == pytest.approx(Iz, rel=5e-3)
    assert num.I_yz == pytest.approx(Iyz, rel=2e-2)


# ─── Hauptachsen ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("deg", [0, 20, 30, 60, 110, 150])
def test_principal_axis_direction(deg):
    """Ein schlankes, um ``deg`` gedrehtes Rechteck: ξ₂ (kleinstes I) liegt in
    Längsrichtung, ξ₁ steht senkrecht darauf."""
    a = math.radians(deg)
    L, t = 4.0, 0.5
    c, s = math.cos(a), math.sin(a)
    pts = [(0, 0), (L * c, L * s), (L * c - t * s, L * s + t * c), (-t * s, t * c)]
    r = compute_section([(sp.nsimplify(y), sp.nsimplify(z)) for y, z in pts],
                        check_values=(1, 1))
    num = r.numeric(1, 1)
    axis1 = math.degrees(num.principal_angle_1) % 180
    assert axis1 == pytest.approx((deg + 90) % 180, abs=1e-6)
    # I(α) entlang der berechneten Richtung muss I₁ ergeben
    a1 = num.principal_angle_1
    I_a = ((num.I_y + num.I_z) / 2 + (num.I_y - num.I_z) / 2 * math.cos(2 * a1)
           - num.I_yz * math.sin(2 * a1))
    assert I_a == pytest.approx(num.I_1)


def test_square_is_isotropic():
    num = section(("0", "0"), ("b", "0"), ("b", "b"), ("0", "b")).numeric(2, 3)
    assert num.is_principal_isotropic


# ─── Spannungen ─────────────────────────────────────────────────────────────

def test_pure_normal_force():
    num = section(("0", "0"), ("b", "0"), ("b", "h"), ("0", "h")).numeric(2, 3)
    st = compute_stress(num, 0, 0, 12)
    assert all(s == pytest.approx(2.0) for s in st.vertex_sigma)
    assert not st.has_neutral_axis


def test_bending_sign_convention():
    """M_y > 0 → Druck oben (z > z_S);  M_z > 0 → Zug rechts (y > y_S)."""
    num = section(("0", "0"), ("b", "0"), ("b", "h"), ("0", "h")).numeric(2, 3)
    W_y = num.I_y / 1.5   # Widerstandsmoment, h/2 = 1,5
    W_z = num.I_z / 1.0
    st = compute_stress(num, 10, 0, 0)
    assert st.vertex_sigma[2] == pytest.approx(-10 / W_y)   # Punkt oben rechts
    assert st.vertex_sigma[0] == pytest.approx(+10 / W_y)   # unten links
    st = compute_stress(num, 0, 10, 0)
    assert st.vertex_sigma[1] == pytest.approx(+10 / W_z)   # rechts
    assert st.vertex_sigma[0] == pytest.approx(-10 / W_z)   # links


def test_bm2_assignment_stresses():
    p = Project.example()
    num = section(*[(v.y, v.z) for v in p.vertices]).numeric(2.0, 3.0)
    st = compute_stress(num, 50, 270, 400)
    assert st.sigma_max == pytest.approx(23.5974676, rel=1e-7)   # Punkt C
    assert st.sigma_min == pytest.approx(1.8045700, rel=1e-6)    # Punkt A


# ─── Projektdatei & Formatierung ────────────────────────────────────────────

def test_project_roundtrip(tmp_path):
    p = Project.example()
    f = tmp_path / "q.json"
    p.save(f)
    assert Project.load(f) == p


def test_legacy_file_format():
    old = {"b": "2", "h": "3", "loads": ["50", "270", "400"],
           "points": [["A", "0", "0"], ["B", "3*b/2", "0"], ["C", "b", "h"]]}
    p = Project.from_dict(old)
    assert p.M_z == "270" and p.vertices[1] == Vertex("B", "3*b/2", "0")


def test_fmt():
    assert fmt(168.75) == "168,75"
    assert fmt(-3.375) == "−3,375"
    assert fmt(2.708333333) == "2,70833"
    assert fmt(1.8, signed=True) == "+1,8"
    assert fmt(0) == "0"
    assert fmt(1.5e-6) == "1,5·10⁻⁶"
