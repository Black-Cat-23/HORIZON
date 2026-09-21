@echo off
echo ===============================================================================
echo HORIZON Standalone Windows Executable Builder (PyInstaller)
echo Smart India Hackathon 2026 - Problem Statement: SIH26169
echo Department of Space / Indian Space Research Organisation (ISRO)
echo ===============================================================================

echo [1/3] Verifying runtime dependencies...
python scripts/verify_runtime_deps.py
if errorlevel 1 (
    echo [ERROR] Dependency verification failed. Please check python environment.
    pause
    exit /b 1
)

echo [2/3] Generating sample test video for offline evaluator testing...
python scripts/generate_sample_video.py

echo [3/3] Compiling standalone executable via PyInstaller...
pyinstaller --clean --noconfirm horizon.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed. Check logs above.
    pause
    exit /b 1
)

echo ===============================================================================
echo [SUCCESS] Standalone HORIZON executable compiled successfully!
echo Output Directory: dist\HORIZON\HORIZON.exe
echo ===============================================================================
pause
