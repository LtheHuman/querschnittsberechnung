"""Rechenkern: Querschnittswerte und Normalspannungen beliebiger Polygone.

Das Modul ist bewusst frei von GUI-Code, damit es unabhängig getestet und
auch aus Skripten oder Notebooks verwendet werden kann.

Koordinaten: y nach rechts, z nach oben (wie bei der Eingabe der Eckpunkte).
Alle Flächenmomente beziehen sich auf den Schwerpunkt S.

Vorzeichenkonvention (TU Graz, BM2):
    M_y = −∫ z·σ dA      (M_y > 0 → Druck auf der Seite z > z_S)
    M_z = +∫ y·σ dA      (M_z > 0 → Zug auf der Seite y > y_S)
    I_yz = +∫ y·z dA

    σ = N/A + (M_z·I_y + M_y·I_yz)/D · ỹ − (M_y·I_z + M_z·I_yz)/D · z̃
    mit D = I_y·I_z − I_yz²  und  ỹ = y − y_S,  z̃ = z − z_S
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import sympy as sp

b_sym, h_sym = sp.symbols("b h", positive=True)

_ALLOWED = {
    "b": b_sym,
    "h": h_sym,
    "pi": sp.pi,
    "sqrt": sp.sqrt,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
}


class InputError(ValueError):
    """Ungültige Benutzereingabe (wird in der GUI am Feld angezeigt)."""


# ─── Eingabe ────────────────────────────────────────────────────────────────

def parse_expr(text: str) -> sp.Expr:
    """Wandelt eine Eingabe wie ``3*b/2``, ``h/3`` oder ``1,5`` in einen
    SymPy-Ausdruck um. Erlaubt sind die Symbole ``b`` und ``h``."""
    s = (text or "").strip().replace("^", "**").replace(",", ".")
    s = s.replace("−", "-").replace("·", "*").replace("×", "*")
    if not s:
        raise InputError("Leerer Ausdruck")
    try:
        expr = sp.sympify(s, locals=_ALLOWED)
    except (sp.SympifyError, SyntaxError, TypeError) as exc:
        raise InputError(f"Ungültiger Ausdruck: {text!r}") from exc
    if not isinstance(expr, sp.Expr):
        raise InputError(f"Kein Zahlenausdruck: {text!r}")
    unknown = expr.free_symbols - {b_sym, h_sym}
    if unknown:
        names = ", ".join(sorted(str(u) for u in unknown))
        raise InputError(f"Unbekannte Variable: {names} (erlaubt: b, h)")
    return expr


def parse_number(text: str) -> float:
    """Wandelt eine Zahl (auch mit Komma oder als Ausdruck wie ``3/2``) um."""
    expr = parse_expr(text)
    if expr.free_symbols:
        raise InputError("Hier ist nur eine Zahl erlaubt")
    value = float(expr)
    if not math.isfinite(value):
        raise InputError("Wert ist nicht endlich")
    return value


# ─── Polygon-Prüfungen ──────────────────────────────────────────────────────

def signed_area(coords: list[tuple[float, float]]) -> float:
    n = len(coords)
    return 0.5 * sum(coords[i][0] * coords[(i + 1) % n][1]
                     - coords[(i + 1) % n][0] * coords[i][1] for i in range(n))


def _segments_intersect(p1, p2, q1, q2) -> bool:
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)

    o1, o2 = orient(p1, p2, q1), orient(p1, p2, q2)
    o3, o4 = orient(q1, q2, p1), orient(q1, q2, p2)
    return o1 * o2 < 0 and o3 * o4 < 0


def is_self_intersecting(coords: list[tuple[float, float]]) -> bool:
    """True, wenn sich zwei nicht benachbarte Kanten kreuzen."""
    n = len(coords)
    edges = [(coords[i], coords[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if _segments_intersect(*edges[i], *edges[j]):
                return True
    return False


# ─── Querschnittswerte ──────────────────────────────────────────────────────

SYMBOLIC_KEYS = ("A", "y_S", "z_S", "I_y", "I_z", "I_yz", "I_1", "I_2", "tan_2theta")


@dataclass
class SectionResult:
    """Symbolische Querschnittswerte (Ausdrücke in b und h)."""

    A: sp.Expr
    y_S: sp.Expr
    z_S: sp.Expr
    I_y: sp.Expr
    I_z: sp.Expr
    I_yz: sp.Expr
    I_1: sp.Expr
    I_2: sp.Expr
    tan_2theta: sp.Expr
    points: list[tuple[sp.Expr, sp.Expr]]
    reversed_input: bool = False  # Eingabe war im Uhrzeigersinn → umgedreht

    def numeric(self, b: float, h: float) -> "NumericSection":
        subs = {b_sym: b, h_sym: h}

        def ev(expr):
            expr = sp.sympify(expr).subs(subs)
            if expr.has(sp.zoo, sp.oo, -sp.oo):
                return math.inf
            try:
                v = complex(sp.N(expr))
            except (TypeError, ValueError):
                return math.nan
            return v.real if abs(v.imag) < 1e-9 * (1 + abs(v.real)) else math.nan

        pts = [(ev(y), ev(z)) for y, z in self.points]
        vals = {k: ev(getattr(self, k)) for k in SYMBOLIC_KEYS}
        return NumericSection(b=b, h=h, points=pts, **vals)


def compute_section(points: list[tuple[sp.Expr, sp.Expr]],
                    check_values: tuple[float, float] | None = None) -> SectionResult:
    """Berechnet die Querschnittswerte eines Polygons symbolisch.

    ``points`` sind (y, z)-Ausdrücke, idealerweise gegen den Uhrzeigersinn.
    Wird ``check_values=(b, h)`` übergeben, wird die Umlaufrichtung mit diesen
    Werten geprüft und eine Eingabe im Uhrzeigersinn automatisch umgedreht.
    """
    n = len(points)
    if n < 3:
        raise InputError("Mindestens 3 Punkte benötigt.")

    reversed_input = False
    if check_values is not None:
        bv, hv = check_values
        coords = [(float(y.subs({b_sym: bv, h_sym: hv})),
                   float(z.subs({b_sym: bv, h_sym: hv}))) for y, z in points]
        if is_self_intersecting(coords):
            raise InputError("Das Polygon überschneidet sich selbst. "
                             "Bitte die Reihenfolge der Punkte prüfen.")
        area = signed_area(coords)
        if abs(area) < 1e-12:
            raise InputError("Die Fläche ist null – liegen alle Punkte auf einer Linie?")
        if area < 0:
            points = list(reversed(points))
            reversed_input = True

    pts = list(points) + [points[0]]
    y = [p[0] for p in pts]
    z = [p[1] for p in pts]
    d = [y[i] * z[i + 1] - y[i + 1] * z[i] for i in range(n)]

    A = sp.simplify(sp.Rational(1, 2) * sum(d))
    if A == 0:
        raise InputError("Die Fläche ist null.")
    y_S = sp.simplify(sum((y[i] + y[i + 1]) * d[i] for i in range(n)) / (6 * A))
    z_S = sp.simplify(sum((z[i] + z[i + 1]) * d[i] for i in range(n)) / (6 * A))

    I_y0 = sum((z[i] ** 2 + z[i] * z[i + 1] + z[i + 1] ** 2) * d[i] for i in range(n)) / 12
    I_z0 = sum((y[i] ** 2 + y[i] * y[i + 1] + y[i + 1] ** 2) * d[i] for i in range(n)) / 12
    I_yz0 = sum(d[i] * (2 * y[i] * z[i] + y[i] * z[i + 1]
                        + y[i + 1] * z[i] + 2 * y[i + 1] * z[i + 1])
                for i in range(n)) / 24

    I_y = sp.simplify(I_y0 - A * z_S ** 2)
    I_z = sp.simplify(I_z0 - A * y_S ** 2)
    I_yz = sp.simplify(I_yz0 - A * y_S * z_S)

    delta = sp.sqrt(((I_y - I_z) / 2) ** 2 + I_yz ** 2)
    I_1 = sp.simplify((I_y + I_z) / 2 + delta)
    I_2 = sp.simplify((I_y + I_z) / 2 - delta)
    diff = sp.simplify(I_y - I_z)
    tan_2theta = sp.zoo if diff == 0 else sp.simplify(2 * I_yz / diff)

    return SectionResult(A=A, y_S=y_S, z_S=z_S, I_y=I_y, I_z=I_z, I_yz=I_yz,
                         I_1=I_1, I_2=I_2, tan_2theta=tan_2theta,
                         points=list(points), reversed_input=reversed_input)


# ─── Numerische Auswertung & Spannungen ─────────────────────────────────────

@dataclass
class NumericSection:
    b: float
    h: float
    points: list[tuple[float, float]]
    A: float
    y_S: float
    z_S: float
    I_y: float
    I_z: float
    I_yz: float
    I_1: float
    I_2: float
    tan_2theta: float

    @property
    def theta_deg(self) -> float:
        """θ = ½·arctan(tan 2θ) in Grad – so wie in der Übung definiert."""
        if math.isnan(self.tan_2theta):
            return math.nan
        if math.isinf(self.tan_2theta):
            return 45.0
        return math.degrees(math.atan(self.tan_2theta) / 2)

    @property
    def principal_angle_1(self) -> float:
        """Richtung der Hauptachse ξ₁ (zu I₁) in Radiant, gemessen von der
        y-Achse gegen den Uhrzeigersinn in der Zeichenebene (y →, z ↑).

        Für I_yz = +∫yz dA gilt I(α) = Ī + ΔI·cos2α − I_yz·sin2α, das Maximum
        liegt daher bei 2α = atan2(−2·I_yz, I_y − I_z)."""
        return 0.5 * math.atan2(-2 * self.I_yz, self.I_y - self.I_z)

    @property
    def is_principal_isotropic(self) -> bool:
        """True bei I₁ = I₂ (z. B. Quadrat): jede Achse ist Hauptachse."""
        return abs(self.I_1 - self.I_2) <= 1e-9 * max(abs(self.I_1), 1e-30)


@dataclass
class StressResult:
    N: float
    M_y: float
    M_z: float
    sigma_N: float          # N/A
    k_y: float              # Faktor vor ỹ
    k_z: float              # Faktor vor z̃
    vertex_sigma: list[float] = field(default_factory=list)

    @property
    def sigma_max(self) -> float:
        return max(self.vertex_sigma)

    @property
    def sigma_min(self) -> float:
        return min(self.vertex_sigma)

    def sigma(self, y_rel, z_rel):
        """σ an Koordinaten relativ zum Schwerpunkt (auch NumPy-Arrays)."""
        return self.sigma_N + self.k_y * y_rel + self.k_z * z_rel

    @property
    def has_neutral_axis(self) -> bool:
        return abs(self.k_y) > 1e-15 or abs(self.k_z) > 1e-15


def compute_stress(sec: NumericSection, M_y: float, M_z: float, N: float) -> StressResult:
    """Normalspannungen bei schiefer Biegung mit Normalkraft (siehe Modulkopf).

    Bei einem ebenen Spannungsverlauf liegen σ_max und σ_min immer in
    Eckpunkten des Polygons."""
    D = sec.I_y * sec.I_z - sec.I_yz ** 2
    if abs(D) < 1e-14 * max(sec.I_y * sec.I_z, 1e-300):
        raise InputError("Determinante I_y·I_z − I_yz² ≈ 0 – Querschnitt degeneriert.")
    k_y = (M_z * sec.I_y + M_y * sec.I_yz) / D
    k_z = -(M_y * sec.I_z + M_z * sec.I_yz) / D
    res = StressResult(N=N, M_y=M_y, M_z=M_z, sigma_N=N / sec.A, k_y=k_y, k_z=k_z)
    res.vertex_sigma = [res.sigma(y - sec.y_S, z - sec.z_S) for y, z in sec.points]
    return res
