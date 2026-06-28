@echo off
cd /d "%~dp0"

REM Kill any existing instance on port 8501
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| find "8501" ^| find "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

.venv\Scripts\python.exe -m streamlit run app.py --browser.gatherUsageStats false
