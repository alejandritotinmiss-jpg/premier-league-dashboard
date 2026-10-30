@echo off
REM Abre la aplicacion (requiere haber ejecutado instalar.bat una vez).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta instalar.bat
    pause
    exit /b 1
)
echo La aplicacion se abrira en http://localhost:8501  (Ctrl + C para detenerla)
start "" cmd /c "timeout /t 6 /nobreak >nul & start http://localhost:8501"
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true
