from sympy import symbols, Rational, sum as sym_sum

# Symbolische Variablen
x1, y1, x2, y2, b, h = symbols('x1 y1 x2 y2 b h')

# Eckpunkte des Polygons definieren (hier als Beispiel)
points = [(0, 0), (3*b/2, 5*h/6), ...]  # weitere Punkte ergänzen

# Hilfsfunktion: summiert Ausdruck über alle Kanten des Polygons
def poly_sum(expr):
    return sum(
        expr.subs({x1: points[i][0], y1: points[i][1],
                   x2: points[i+1][0], y2: points[i+1][1]})
        for i in range(len(points) - 1)
    )

# Querschnittswerte (Shoelace-basiert)
A   = Rational(1, 2) * poly_sum(x1*y2 - x2*y1)                          # Fläche
xs  = poly_sum((x1 + x2) * (x1*y2 - x2*y1)) / (6*A)                    # Schwerpunkt x
ys  = poly_sum((y1 + y2) * (x1*y2 - x2*y1)) / (6*A)                    # Schwerpunkt y
Ix  = poly_sum((y1**2 + y1*y2 + y2**2) * (x1*y2 - x2*y1)) / 12        # Flächenträgheitsmoment Ix
Iy  = poly_sum((x1**2 + x1*x2 + x2**2) * (x1*y2 - x2*y1)) / 12        # Flächenträgheitsmoment Iy
IzS = Ix + Iy - A * (xs**2 + ys**2)                                   # Polares Moment (Steiner-Anteil abgezogen)