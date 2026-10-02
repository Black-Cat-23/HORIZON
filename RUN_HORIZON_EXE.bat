@echo off
title HORIZON ISRO Coarse-Align-X Desktop Suite
echo ============================================================
echo   HORIZON: Coarse-to-Fine Optical Beam Tracking Suite (ISRO)
echo ============================================================
echo.

IF EXIST "%~dp0coarse-align-x\dist\HORIZON\HORIZON.exe" (
    echo [OK] Found Standalone Executable: coarse-align-x\dist\HORIZON\HORIZON.exe
    echo Launching Desktop GUI in High-Performance Mode...
    start "" "%~dp0coarse-align-x\dist\HORIZON\HORIZON.exe" --gui
) ELSE (
    echo [NOTICE] Standalone executable not found in dist\.
    echo Launching from Python environment...
    cd "%~dp0coarse-align-x"
    python main.py --gui
)
