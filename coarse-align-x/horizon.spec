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
]

# Data files to bundle – include models, configs, fonts, icons, plugins, assets
datas = []
# Models (ONNX files)
if os.path.isdir('models'):
    datas += collect_data_files('models', includes=['*.onnx'])
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

# Excludes – remove training‑only packages and unused Qt plugins
excludes = [
    'torch', 'torchvision', 'torchaudio', 'ultralytics',
    'tensorflow', 'mxnet', 'caffe2',
    'PyQt5', 'QtWebEngine', 'QtMultimedia', 'QtNetwork',
    'QtPrintSupport', 'QtSql', 'QtSvg', 'QtTest', 'QtXml',
]

# Build options – analysis
exe = Analysis(
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

pyz = PYZ(exe.pure, exe.zipped_data, cipher=None)

# Build one‑dir bundle
exe = EXE(
    pyz,
    exe.scripts,
    exe.binaries,
    exe.zipfiles,
    exe.datas,
    name='HORIZON',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # hide console; use --debug flag to re‑enable
    icon='icons/horizon.ico'
)

coll = COLLECT(
    exe,
    exe.binaries,
    exe.zipfiles,
    exe.datas,
    strip=False,
    upx=True,
    name='HORIZON'
)

