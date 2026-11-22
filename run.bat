@echo off
REM Starts the FastAPI backend and the React frontend in two windows.
start "SolarPower API" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate && uvicorn app.main:app --port 8000"
start "SolarPower UI" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 6 >nul
start http://localhost:5173
