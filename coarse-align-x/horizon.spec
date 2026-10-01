# -*- mode: python ; coding: utf-8 -*-

# PyInstaller spec file for HORIZON standalone executable
# Generated as part of Phase 19 implementation.

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Entry point script
entry_script = 'main.py'

# Hidden imports – include modules that are imported dynamically at runtime
hiddenimports = collect_submodules('PySide6')
hiddenimports += [
    'onnxruntime',
    'onnxruntime.capi._pybind_state',
    'scipy.special._basic',
    'scipy.optimize._minimize',
    'osqp',
    'pyqtgraph',
    'matplotlib.backends.backend_agg',
    'cv2',
    'numpy',
    'pandas',
    'reportlab',
    'reportlab.lib',
    'reportlab.lib.pagesizes',
    'reportlab.lib.styles',
    'reportlab.platypus',
    'reportlab.pdfgen',
    'sources',
    'sources.video_source',
    'sources.frame_source',
]

# Data files to bundle – include models, configs, fonts, icons, plugins, assets
datas = []
# Models (ONNX files & metadata)
if os.path.isdir('models'):
    datas += collect_data_files('models', includes=['*.onnx'])
if os.path.isdir('research/training/models'):
    for root, _, files in os.walk('research/training/models'):
        for f in files:
            p = os.path.join(root, f)
            rel_dir = os.path.relpath(root, '.')
            datas.append((p, rel_dir))

icon_file = 'icons/horizon.ico' if os.path.isfile('icons/horizon.ico') else None
# Config files (YAML/JSON)
if os.path.isdir('configs'):
    datas += collect_data_files('configs')
# Fonts used by UI
if os.path.isdir('fonts'):
    datas += collect_data_files('fonts', includes=['*.ttf', '*.otf'])
# Icons
if os.path.isdir('icons'):
    datas += collect_data_files('icons')
# Plugins (user‑installed and example plugins)
if os.path.isdir('plugins'):
    datas += collect_data_files('plugins')
# Additional assets (splash screen, etc.)
if os.path.isdir('assets'):
    datas += collect_data_files('assets')
# Data samples (ISRO sample test video)
if os.path.isdir('data'):
    for root, _, files in os.walk('data'):
        for f in files:
            p = os.path.join(root, f)
            rel_dir = os.path.relpath(root, '.')
            datas.append((p, rel_dir))
if os.path.isfile('HORIZON_ISRO_Performance_Report.pdf'):
    datas.append(('HORIZON_ISRO_Performance_Report.pdf', '.'))

# Excludes – remove training‑only packages and unused Qt plugins
excludes = [
    'torch', 'torchvision', 'torchaudio', 'ultralytics',
    'tensorflow', 'mxnet', 'caffe2',
    'PyQt5', 'QtWebEngine', 'QtMultimedia', 'QtNetwork',
    'QtPrintSupport', 'QtSql', 'QtSvg', 'QtTest', 'QtXml',
]

# Build options – analysis
a = Analysis(
    [entry_script],
    pathex=[os.getcwd()],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=['scripts/pyinstaller_runtime_hook.py'],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Build one‑dir bundle
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HORIZON',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # hide console; set to True for CLI debug
    icon=icon_file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='HORIZON'
)

