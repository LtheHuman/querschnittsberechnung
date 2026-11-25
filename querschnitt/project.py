"""Projektdaten (Eingaben) und Speichern/Laden als JSON.

Das Dateiformat ist abwärtskompatibel zur alten Tkinter-Version:
``{"b": "2", "h": "3", "loads": ["50", "270", "400"], "points": [[name, y, z], ...]}``
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

FORMAT_VERSION = 2


@dataclass
class Vertex:
    name: str
    y: str
    z: str


@dataclass
class Project:
    title: str = ""
    b: str = "2"
    h: str = "3"
    M_y: str = "50"
    M_z: str = "270"
    N: str = "400"
    vertices: list[Vertex] = field(default_factory=list)

    @classmethod
    def example(cls) -> "Project":
        """Querschnitt aus der BM2-Aufgabe 2026 (TU Graz)."""
        return cls(
            title="BM2 Aufgabe 2026",
            vertices=[Vertex("A", "0", "0"),
                      Vertex("B", "2*b", "0"),
                      Vertex("C", "3*b", "h"),
                      Vertex("D", "5*b/2", "2*h"),
                      Vertex("E", "b/2", "3*h")],
        )

    # ── JSON ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "version": FORMAT_VERSION,
            "title": self.title,
            "b": self.b,
            "h": self.h,
            "loads": [self.M_y, self.M_z, self.N],
            "points": [[v.name, v.y, v.z] for v in self.vertices],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        if not isinstance(data, dict) or "points" not in data:
            raise ValueError("Keine gültige Querschnittsdatei (Feld 'points' fehlt).")
        loads = list(data.get("loads", ["0", "0", "0"])) + ["0", "0", "0"]
        vertices = []
        for item in data["points"]:
            if not isinstance(item, (list, tuple)) or len(item) != 3:
                raise ValueError(f"Ungültiger Punkt-Eintrag: {item!r}")
            vertices.append(Vertex(*(str(x) for x in item)))
        return cls(title=str(data.get("title", "")),
                   b=str(data.get("b", "1")), h=str(data.get("h", "1")),
                   M_y=str(loads[0]), M_z=str(loads[1]), N=str(loads[2]),
                   vertices=vertices)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                              encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Datei ist kein gültiges JSON: {exc}") from exc
        return cls.from_dict(data)
