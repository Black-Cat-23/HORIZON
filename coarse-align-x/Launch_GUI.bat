@echo off
title Launch HORIZON Desktop Suite
echo ============================================================
echo   Launching HORIZON Coarse-Align-X Desktop Application
echo ============================================================
echo.
IF EXIST "%~dp0dist\HORIZON\HORIZON.exe" (
    echo Starting Standalone Executable...
    start "" "%~dp0dist\HORIZON\HORIZON.exe" --gui
) ELSE (
    echo Starting Python GUI...
    python "%~dp0main.py" --gui
)
