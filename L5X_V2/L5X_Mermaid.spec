# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = [
    ('template.html', '.'),
    ('script.js', '.'),
]
binaries = []
hiddenimports = ['l5x_core']

# collect_all('PySide6') lets PyInstaller's top-level hook discover every
# Qt native library, plugin, and data file automatically.  We then
# post-filter its binaries and datas outputs so that only the libraries
# the application actually needs end up in the bundle.
#
# Background: the Analysis() excludes list only filters Python-level
# imports; it has no effect on native binaries already added to the
# binaries list here.  The filters below are therefore the only mechanism
# that keeps unused Qt natives (WebEngine alone is ~150-200 MB) out of
# the final artifact.
_tmp = collect_all('PySide6')

# ── Binary filter ────────────────────────────────────────────────────────────
# Block-list of Qt module stem names whose native libraries must not be
# bundled.  The check normalises across platforms by stripping the leading
# 'lib' (Linux) and everything from the first '.' onward (drops .dll /
# .so.6 / .abi3.so etc.), leaving a bare module name like 'Qt6WebEngineCore'.
_QT_BINARY_BLOCKLIST = frozenset([
    # WebEngine — Chromium engine, by far the largest single contributor
    'Qt6WebEngineCore', 'Qt6WebEngineWidgets', 'Qt6WebEngineQuick',
    'QtWebEngineProcess',  # helper exe, no Qt6 prefix
    # Multimedia / FFmpeg
    'Qt6Multimedia', 'Qt6MultimediaWidgets', 'Qt6MultimediaQuick',
    'avcodec', 'avformat', 'avutil', 'avdevice', 'swresample', 'swscale',
    # QML / Quick engine
    'Qt6Qml', 'Qt6QmlCompiler', 'Qt6QmlCore', 'Qt6QmlModels',
    'Qt6QmlWorkerScript', 'Qt6QmlNetwork', 'Qt6QmlLocalStorage',
    'Qt6QmlXmlListModel',
    'Qt6Quick', 'Qt6QuickControls2', 'Qt6QuickControls2Basic',
    'Qt6QuickControls2BasicStyleImpl', 'Qt6QuickControls2Fusion',
    'Qt6QuickControls2FusionStyleImpl', 'Qt6QuickControls2Imagine',
    'Qt6QuickControls2ImagineStyleImpl', 'Qt6QuickControls2Material',
    'Qt6QuickControls2MaterialStyleImpl', 'Qt6QuickControls2Universal',
    'Qt6QuickControls2UniversalStyleImpl', 'Qt6QuickControls2Impl',
    'Qt6QuickDialogs2', 'Qt6QuickDialogs2QuickImpl', 'Qt6QuickDialogs2Utils',
    'Qt6QuickEffects', 'Qt6QuickLayouts', 'Qt6QuickParticles',
    'Qt6QuickShapes', 'Qt6QuickTemplates2', 'Qt6QuickTest', 'Qt6QuickWidgets',
    # Quick 3D
    'Qt6Quick3D', 'Qt6Quick3DAssetImport', 'Qt6Quick3DAssetUtils',
    'Qt6Quick3DEffects', 'Qt6Quick3DGlslParser', 'Qt6Quick3DHelpers',
    'Qt6Quick3DHelpersImpl', 'Qt6Quick3DParticles', 'Qt6Quick3DRuntimeRender',
    'Qt6Quick3DUtils',
    # 3D
    'Qt63DAnimation', 'Qt63DCore', 'Qt63DExtras',
    'Qt63DInput', 'Qt63DLogic', 'Qt63DRender',
    # Charts / data visualisation
    'Qt6Charts', 'Qt6DataVisualization', 'Qt6Graphs', 'Qt6GraphsWidgets',
    # Developer tooling
    'Qt6Designer', 'Qt6DesignerComponents', 'Qt6Help', 'Qt6UiTools',
    # Geospatial
    'Qt6Location', 'Qt6Positioning', 'Qt6PositioningQuick',
    # Connectivity
    'Qt6Bluetooth', 'Qt6Nfc',
    # Print / PDF
    'Qt6PrintSupport', 'Qt6Pdf', 'Qt6PdfQuick',
    # 3D Quick (separate family from Qt63D*)
    'Qt63DQuick',
    # Audio / XR / virtual keyboard
    'Qt6SpatialAudio', 'Qt6VirtualKeyboard',
    # Misc unused
    'Qt6Concurrent', 'Qt6HttpServer', 'Qt6RemoteObjects',
    'Qt6Scxml', 'Qt6ScxmlQml',
    'Qt6Sensors', 'Qt6SensorsQuick',
    'Qt6SerialBus', 'Qt6SerialPort',
    'Qt6Sql',
    'Qt6StateMachine', 'Qt6StateMachineQml',
    'Qt6Svg', 'Qt6SvgWidgets',
    'Qt6Test',
    'Qt6TextToSpeech',
    'Qt6WebChannel', 'Qt6WebChannelQuick',
    'Qt6WebSockets',
    'Qt6WebView', 'Qt6WebViewQuick',
    'Qt6Xml',
    'Qt6ShaderTools',
    'Qt6OpenGL', 'Qt6OpenGLWidgets',
    'Qt6NetworkAuth',
    'Qt6WaylandCompositor', 'Qt6WaylandClient',
    'Qt6WaylandEglClientHwIntegration', 'Qt6WaylandEglCompositorHwIntegration',
])

def _keep_binary(dest_name):
    base = os.path.basename(dest_name)
    stem = base.split('.')[0]          # strip extension(s): .dll / .so.6 / .abi3.so
    stem = stem.removeprefix('lib')    # normalise Linux 'lib' prefix
    # Prefix match catches variants like Qt6Quick3DXr from Qt6Quick3D,
    # Qt63DQuickRender from Qt63DRender, Qt6QmlMeta from Qt6Qml, etc.
    return not any(stem == b or stem.startswith(b) for b in _QT_BINARY_BLOCKLIST)

# ── Data filter ──────────────────────────────────────────────────────────────
# Entire Qt data subdirectories that are safe to drop for a pure Widgets app:
#   Qt/resources/   — 100% WebEngine data (icudtl.dat, .pak files, v8 snapshot)
#   Qt/qml/         — QML component tree, not used by QtWidgets
#   Qt/metatypes/   — design-time type metadata for Qt Creator, not runtime
#   Qt/translations/— locale strings for all Qt modules; omit to save ~56 MB
#
# Qt/plugins/ is intentionally kept in full: it contains the platform plugin,
# image format decoders, TLS backends, and other required runtime components.
_DATA_EXCLUDE_DIRS = (
    os.path.join('PySide6', 'Qt', 'resources'),
    os.path.join('PySide6', 'Qt', 'qml'),
    os.path.join('PySide6', 'Qt', 'metatypes'),
    os.path.join('PySide6', 'Qt', 'translations'),
)

_QT_LIB_DEST = os.path.normpath(os.path.join('PySide6', 'Qt', 'lib'))

def _keep_data(src, dest_name):
    # dest_name is the destination path inside the bundle (relative)
    norm = os.path.normpath(dest_name)
    # Drop entire excluded subdirectories (qml, metatypes, resources, translations)
    for excl in _DATA_EXCLUDE_DIRS:
        if norm == os.path.normpath(excl) or norm.startswith(os.path.normpath(excl) + os.sep):
            return False
    # On Linux, Qt shared libraries land in datas under Qt/lib/ rather than in
    # binaries.  Apply the same block-list so unwanted natives (WebEngine etc.)
    # are filtered regardless of platform packaging convention.
    if norm == _QT_LIB_DEST or norm.startswith(_QT_LIB_DEST + os.sep):
        stem = os.path.basename(src).split('.')[0].removeprefix('lib')
        if any(stem == b or stem.startswith(b) for b in _QT_BINARY_BLOCKLIST):
            return False
    return True

datas    += [d for d in _tmp[0] if _keep_data(d[0], d[1])]
binaries += [b for b in _tmp[1] if _keep_binary(b[0])]
# hiddenimports intentionally not extended — let Analysis + excludes decide


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
