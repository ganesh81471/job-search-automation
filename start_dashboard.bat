@echo off
cd /d "%~dp0"

echo ================================================
echo   Embedded Job Search Companion - Starting up
echo ================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERROR: Could not find venv\Scripts\python.exe in this folder.
    echo Make sure this .bat file is sitting directly inside your
    echo job-search-automation folder, next to the "venv" folder.
    echo.
    echo Current folder: %cd%
    echo.
    pause
    exit /b 1
)

echo Using Python from: venv\Scripts\python.exe
echo Launching dashboard - your browser should open automatically.
echo Keep this window open while you use the dashboard.
echo Close this window (or press Ctrl+C) to stop it.
echo.

venv\Scripts\python.exe -m streamlit run app.py

echo.
echo ================================================
echo Streamlit stopped or failed to start. See any error
echo message above. This window will stay open so you can
echo read it.
echo ================================================
pause