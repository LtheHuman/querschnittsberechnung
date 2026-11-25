# PyInstaller-Konfiguration – baut ein eigenständiges Programm (ohne Python-Installation).
# Unterstützt werden nur Windows und Linux.
# Aufruf aus dem Projektordner:  pyinstaller packaging/querschnitt.spec --noconfirm
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
NAME = "Querschnittsberechnung"
if sys.platform == "darwin":
    raise SystemExit("macOS wird nicht unterstützt – nur Windows und Linux.")
RES = ROOT / "querschnitt" / "resources"
ICON = str(RES / ("icon.ico" if sys.platform == "win32" else "icon.png"))

# Große Qt-/Python-Module, die das Programm nicht braucht
EXCLUDES = [
    "tkinter", "PyQt5", "PyQt6", "IPython", "jupyter", "pytest",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQml", "PySide6.QtQuickWidgets",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtMultimedia", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtBluetooth",
    "PySide6.QtLocation", "PySide6.QtPositioning", "PySide6.QtSensors",
    "PySide6.QtSerialPort", "PySide6.QtNetworkAuth", "PySide6.QtRemoteObjects",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtSpatialAudio", "PySide6.QtTextToSpeech", "PySide6.QtWebSockets",
    "PySide6.QtWebChannel", "PySide6.QtHttpServer", "PySide6.QtScxml",
    "PySide6.QtStateMachine", "PySide6.QtVirtualKeyboard", "PySide6.QtCanvasPainter",
]

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    datas=[(str(RES), "querschnitt/resources")],
    hiddenimports=["matplotlib.backends.backend_qtagg", "PySide6.QtSvg"],
    excludes=EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=NAME,
    console=False,
    icon=ICON,
)
coll = COLLECT(exe, a.binaries, a.datas, name=NAME)
