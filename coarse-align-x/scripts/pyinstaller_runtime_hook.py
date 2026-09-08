# Runtime hook for PyInstaller to set Qt environment variables
import os

# Ensure high-DPI scaling is enabled on Windows
os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
os.environ.setdefault('QT_SCALE_FACTOR', '1')
os.environ.setdefault('QT_FONT_DPI', '96')

