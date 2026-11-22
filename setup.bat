@echo off
REM One-time setup: Python environment, dependencies, model training, frontend packages.
cd /d "%~dp0backend"
python -m venv venv || (echo Python not found. Install Python 3.10+ from python.org & pause & exit /b 1)
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo Dependency install failed & pause & exit /b 1)
python train_model.py || (echo Training failed & pause & exit /b 1)
cd /d "%~dp0frontend"
call npm install || (echo npm not found. Install Node.js 18+ from nodejs.org & pause & exit /b 1)
echo.
echo Setup complete. Now double-click run.bat
pause
