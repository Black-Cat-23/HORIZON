# Verify that all runtime dependencies can be imported
import importlib
import sys

runtime_packages = [
    'numpy',
    'opencv_python_headless',
    'PySide6',
    'onnxruntime',
    'scipy',
    'pandas',
    'pyqtgraph',
    'yaml',
    'reportlab',
    'matplotlib',
    'osqp',
    'filterpy',
]

missing = []
for pkg in runtime_packages:
    try:
        importlib.import_module(pkg)
    except ImportError:
        missing.append(pkg)

if missing:
    print('Missing runtime dependencies:', ', '.join(missing))
    sys.exit(1)
else:
    print('All runtime dependencies are present.')

