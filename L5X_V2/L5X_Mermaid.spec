# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('template.html', '.'),
    ('script.js', '.'),
]
binaries = []
hiddenimports = ['l5x_core']

# Op 2: collect_all('PySide6') is kept for datas/binaries so that all Qt
# native libraries and plugins are properly collected via PyInstaller's
# top-level PySide6 hook (there are no per-submodule hooks, so calling
# collect_all on individual submodules leaves binaries like QtWebEngineCore
# uncollected).  We intentionally discard the hiddenimports list it returns
# and instead rely on PyInstaller's import analysis + the excludes list below
# to keep the Python layer lean.
_tmp = collect_all('PySide6')
datas    += _tmp[0]
binaries += _tmp[1]
# hiddenimports intentionally not extended here — let Analysis + excludes decide


a = Analysis(
    ['l5x_mermaid_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Op 3: Explicitly exclude unused PySide6 submodules and heavy stdlib/
    # third-party packages that are not needed by this application.
    excludes=[
        # Unused PySide6 submodules
        'PySide6.Qt3DAnimation', 'PySide6.Qt3DCore', 'PySide6.Qt3DExtras',
        'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DRender',
        'PySide6.QtBluetooth', 'PySide6.QtCharts', 'PySide6.QtConcurrent',
        'PySide6.QtDataVisualization', 'PySide6.QtDesigner', 'PySide6.QtHelp',
        'PySide6.QtLocation', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtNfc', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
        'PySide6.QtPositioning', 'PySide6.QtPrintSupport', 'PySide6.QtQml',
        'PySide6.QtQuick', 'PySide6.QtQuick3D', 'PySide6.QtQuickControls2',
        'PySide6.QtQuickWidgets', 'PySide6.QtRemoteObjects', 'PySide6.QtScxml',
        'PySide6.QtSensors', 'PySide6.QtSerialBus', 'PySide6.QtSerialPort',
        'PySide6.QtSql', 'PySide6.QtStateMachine', 'PySide6.QtSvg',
        'PySide6.QtSvgWidgets', 'PySide6.QtTest', 'PySide6.QtUiTools',
        'PySide6.QtWebChannel', 'PySide6.QtWebSockets', 'PySide6.QtXml',
        # WebEngine removed entirely — viewer now opens in system browser
        'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineCore',
        # Unused stdlib modules
        'tkinter', '_tkinter', 'lib2to3', 'pydoc', 'doctest',
        'unittest', 'test', 'distutils',
        # Unused heavy packages that could be pulled in transitively
        'matplotlib', 'numpy', 'scipy', 'pandas', 'PIL', 'cv2',
        'PyQt5', 'PyQt6', 'wx',
    ],
    noarchive=False,
    optimize=2,  # Op 4: Strip docstrings and assert statements from bundled .pyc files
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='L5X Mermaid',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['../dolphin.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='L5X Mermaid',
)
