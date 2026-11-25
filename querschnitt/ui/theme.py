"""Farbschemata (hell/dunkel) für Qt-Oberfläche und matplotlib-Diagramme."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str          # Fensterhintergrund
    surface: str     # Karten / Panels
    surface_alt: str # Tabellenzeilen, Eingabefelder
    border: str
    text: str
    muted: str
    accent: str
    accent_text: str
    danger: str
    tension: str     # Zug (σ > 0)
    compression: str # Druck (σ < 0)
    axis1: str       # Hauptachse ξ₁
    axis2: str       # Hauptachse ξ₂
    grid: str

    @property
    def is_dark(self) -> bool:
        return self.name == "dark"


LIGHT = Theme(
    name="light",
    bg="#f3f4f6", surface="#ffffff", surface_alt="#f8f9fb", border="#e2e5ea",
    text="#1b2330", muted="#6b7482", accent="#2b5fd9", accent_text="#ffffff",
    danger="#c62f3c", tension="#c0392b", compression="#2563a8",
    axis1="#d97706", axis2="#7c3aed", grid="#e6e8ec",
)

DARK = Theme(
    name="dark",
    bg="#15171b", surface="#1e2127", surface_alt="#252931", border="#30353e",
    text="#e5e8ec", muted="#99a2ae", accent="#6b96f5", accent_text="#0d1220",
    danger="#f06b75", tension="#f07167", compression="#6aa8f0",
    axis1="#f5b041", axis2="#b392f0", grid="#2b3038",
)


def apply_theme(app: QApplication, t: Theme) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    c = QColor
    pal.setColor(QPalette.Window, c(t.bg))
    pal.setColor(QPalette.WindowText, c(t.text))
    pal.setColor(QPalette.Base, c(t.surface))
    pal.setColor(QPalette.AlternateBase, c(t.surface_alt))
    pal.setColor(QPalette.Text, c(t.text))
    pal.setColor(QPalette.Button, c(t.surface))
    pal.setColor(QPalette.ButtonText, c(t.text))
    pal.setColor(QPalette.Highlight, c(t.accent))
    pal.setColor(QPalette.HighlightedText, c(t.accent_text))
    pal.setColor(QPalette.ToolTipBase, c(t.surface))
    pal.setColor(QPalette.ToolTipText, c(t.text))
    pal.setColor(QPalette.PlaceholderText, c(t.muted))
    pal.setColor(QPalette.Link, c(t.accent))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, c(t.muted))
    app.setPalette(pal)
    app.setStyleSheet(stylesheet(t))


def stylesheet(t: Theme) -> str:
    return f"""
    QMainWindow, QWidget#Root {{ background: {t.bg}; }}
    QToolTip {{ background: {t.surface}; color: {t.text}; border: 1px solid {t.border};
                padding: 6px 8px; border-radius: 6px; }}

    QToolBar {{ background: {t.surface}; border: none; border-bottom: 1px solid {t.border};
               padding: 6px 10px; spacing: 4px; }}
    QToolBar QToolButton {{ background: transparent; border: 1px solid transparent;
               border-radius: 7px; padding: 5px 9px; color: {t.text}; }}
    QToolBar QToolButton:hover {{ background: {t.surface_alt}; border-color: {t.border}; }}
    QToolBar QToolButton:pressed {{ background: {t.border}; }}
    QToolBar::separator {{ background: {t.border}; width: 1px; margin: 6px 6px; }}
    QLabel#AppTitle {{ font-size: 15px; font-weight: 600; color: {t.text}; padding: 0 10px 0 2px; }}
    QLabel#AppSubtitle {{ color: {t.muted}; padding-right: 12px; }}

    QFrame#Card {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 10px; }}
    QLabel#CardTitle {{ font-size: 11px; font-weight: 700; letter-spacing: 0.6px;
                       color: {t.muted}; }}
    QLabel#Hint, QLabel#Unit {{ color: {t.muted}; }}
    QLabel#Hint {{ font-size: 11px; }}
    QLabel#Symbol {{ font-weight: 600; }}
    QLabel#Value {{ font-size: 14px; font-weight: 600; }}
    QLabel#BigValue {{ font-size: 20px; font-weight: 650; }}
    QLabel#Tension {{ color: {t.tension}; font-size: 20px; font-weight: 650; }}
    QLabel#Compression {{ color: {t.compression}; font-size: 20px; font-weight: 650; }}
    QFrame#Divider {{ background: {t.border}; max-height: 1px; min-height: 1px; border: none; }}

    QLineEdit {{ background: {t.surface_alt}; border: 1px solid {t.border}; border-radius: 7px;
                padding: 5px 8px; selection-background-color: {t.accent}; }}
    QLineEdit:focus {{ border: 1px solid {t.accent}; }}
    QLineEdit[invalid="true"] {{ border: 1px solid {t.danger}; }}

    QPushButton {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 7px;
                  padding: 5px 12px; }}
    QPushButton:hover {{ background: {t.surface_alt}; }}
    QPushButton:pressed {{ background: {t.border}; }}
    QPushButton:disabled {{ color: {t.muted}; }}
    QPushButton#Primary {{ background: {t.accent}; color: {t.accent_text}; border: none;
                          font-weight: 600; padding: 8px 14px; }}
    QPushButton#Primary:hover {{ background: {t.accent}; }}
    QPushButton#IconButton {{ padding: 4px 8px; min-width: 22px; }}

    QTableWidget {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 8px;
                   gridline-color: {t.border}; alternate-background-color: {t.surface_alt};
                   selection-background-color: {t.accent}; selection-color: {t.accent_text}; }}
    QTableWidget QLineEdit {{ border-radius: 0; padding: 2px 4px; }}
    QHeaderView::section {{ background: {t.surface_alt}; color: {t.muted}; border: none;
                           border-bottom: 1px solid {t.border}; padding: 6px 8px;
                           font-weight: 600; font-size: 11px; }}
    QTableCornerButton::section {{ background: {t.surface_alt}; border: none; }}

    QTabWidget::pane {{ border: 1px solid {t.border}; border-radius: 10px; background: {t.surface};
                       top: -1px; }}
    QTabBar::tab {{ background: transparent; color: {t.muted}; padding: 7px 16px; margin-right: 2px;
                   border: 1px solid transparent; border-bottom: none;
                   border-top-left-radius: 8px; border-top-right-radius: 8px; }}
    QTabBar::tab:selected {{ background: {t.surface}; color: {t.text}; border-color: {t.border};
                            font-weight: 600; }}
    QTabBar::tab:hover:!selected {{ color: {t.text}; }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {t.border}; border-radius: 4px; min-height: 30px; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {t.border}; border-radius: 4px; min-width: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

    QSplitter::handle {{ background: transparent; }}
    QStatusBar {{ background: {t.surface}; border-top: 1px solid {t.border}; color: {t.muted}; }}
    QStatusBar QLabel {{ color: {t.muted}; padding: 0 6px; }}
    QLabel#Pill {{ border-radius: 9px; padding: 2px 10px; font-size: 11px; font-weight: 600; }}
    QLabel#Pill[state="ok"] {{ background: rgba(34,160,90,0.15); color: #22a05a; }}
    QLabel#Pill[state="busy"] {{ background: rgba(120,130,150,0.18); color: {t.muted}; }}
    QLabel#Pill[state="error"] {{ background: rgba(220,60,70,0.15); color: {t.danger}; }}
    QLabel#Notice {{ background: rgba(217,119,6,0.12); color: {t.axis1}; border-radius: 7px;
                    padding: 6px 9px; }}
    QMenu {{ background: {t.surface}; border: 1px solid {t.border}; padding: 4px; }}
    QMenu::item {{ padding: 5px 18px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {t.accent}; color: {t.accent_text}; }}
    """


def mpl_rc(t: Theme) -> dict:
    """matplotlib-rcParams passend zum Theme."""
    return {
        "figure.facecolor": t.surface,
        "axes.facecolor": t.surface,
        "savefig.facecolor": t.surface,
        "axes.edgecolor": t.border,
        "axes.labelcolor": t.muted,
        "axes.titlecolor": t.text,
        "xtick.color": t.muted,
        "ytick.color": t.muted,
        "grid.color": t.grid,
        "text.color": t.text,
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "mathtext.fontset": "dejavusans",
    }
