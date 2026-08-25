@echo off
cd /d "C:\Scriptorium"
python scriptorium.py
if errorlevel 1 (
    echo.
    echo *** Error launching Scriptorium ***
    echo Python may not be installed or on your PATH.
    echo.
    pause
)
