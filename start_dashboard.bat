@echo off
cd /d "%~dp0"
echo Starting Embedded Job Search Companion...
echo Your browser will open automatically. Close this window to stop it.
streamlit run app.py
pause