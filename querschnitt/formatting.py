"""Zahlen- und Formelformatierung (deutsche Schreibweise, LaTeX)."""

from __future__ import annotations

import math

import sympy as sp

MINUS = "−"


def fmt(value: float, digits: int = 6, signed: bool = False) -> str:
    """Zahl mit ``digits`` signifikanten Stellen, Dezimalkomma und echtem Minus.

    >>> fmt(168.75), fmt(-3.375), fmt(2.708333333)
    ('168,75', '−3,375', '2,70833')
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "–"
    if math.isinf(value):
        return "∞" if value > 0 else MINUS + "∞"
    if value == 0:
        return "0"
    mag = abs(value)
    if mag >= 1e6 or mag < 1e-4:
        mant, exp = f"{value:.{digits - 1}e}".split("e")
        mant = mant.rstrip("0").rstrip(".") if "." in mant else mant
        s = f"{mant}·10{_superscript(int(exp))}"
    else:
        decimals = max(0, digits - 1 - int(math.floor(math.log10(mag))))
        s = f"{value:.{decimals}f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
    s = s.replace(".", ",").replace("-", MINUS)
    if signed and value > 0:
        s = "+" + s
    return s


_SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def _superscript(n: int) -> str:
    return str(n).translate(_SUP)


def to_latex(expr) -> str:
    """SymPy-Ausdruck → LaTeX für matplotlib-mathtext (ohne ``\\cdot``-Ballast)."""
    if expr is sp.zoo or expr == sp.zoo:
        return r"\infty"
    tex = sp.latex(expr, mul_symbol=None)
    tex = tex.replace(r"\left(", "(").replace(r"\right)", ")")
    return tex.replace(r"\frac", r"\dfrac")


def to_plain(expr) -> str:
    """Kompakte Textform eines Ausdrucks, z. B. ``25·b·h³/8``."""
    s = str(expr)
    s = s.replace("**2", "²").replace("**3", "³").replace("**4", "⁴")
    return s.replace("*", "·")
