@echo off
REM ==========================================================================
REM  Instalador del proyecto "Mas alla de la tabla" para Windows.
REM  Doble clic en este archivo: crea el entorno virtual, instala las
REM  librerias, ejecuta las pruebas, abre VS Code y la aplicacion.
REM  Todo lo que pasa queda anotado en instalacion_log.txt
REM ==========================================================================
setlocal
cd /d "%~dp0"
set "LOG=%~dp0instalacion_log.txt"
echo Instalacion iniciada: %DATE% %TIME% > "%LOG%"

echo.
echo  =============================================
echo   Mas alla de la tabla - instalacion
echo  =============================================
echo.

REM --- 1. Buscar Python -----------------------------------------------------
REM El proyecto usa Python 3.12: es la version con la que se publicara la app
REM y la que tiene listas todas las librerias. Versiones muy nuevas (como 3.15)
REM todavia pueden no tener disponibles algunas de ellas.
echo [1/5] Buscando Python 3.12...
set "PY="
set "PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
py -3.12 --version >nul 2>&1 && set "PY=py -3.12"
if not defined PY (
    if exist "%PY312%" set "PY=%PY312%"
)
if not defined PY (
    echo       No se encontro Python 3.12. Instalandolo con winget, solo para este usuario...
    echo No se encontro Python 3.12. Se instala con winget. >> "%LOG%"
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements >> "%LOG%" 2>&1
    if exist "%PY312%" set "PY=%PY312%"
)
if not defined PY (
    echo.
    echo  ERROR: no se pudo conseguir Python 3.12. Instalalo desde
    echo  https://www.python.org/downloads/release/python-31210/
    echo  y vuelve a abrir este archivo.
    echo ERROR: Python 3.12 no disponible. >> "%LOG%"
    goto :fin_error
)
for /f "delims=" %%v in ('%PY% --version 2^>^&1') do set "VERSION_PY=%%v"
echo       Encontrado: %VERSION_PY%
echo Python: %VERSION_PY% (%PY%) >> "%LOG%"

REM --- 2. Crear el entorno virtual ------------------------------------------
echo [2/5] Creando el entorno virtual .venv...
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv >> "%LOG%" 2>&1
)
if not exist ".venv\Scripts\python.exe" (
    echo  ERROR: no se pudo crear el entorno virtual. Revisa instalacion_log.txt
    goto :fin_error
)
set "VPY=%~dp0.venv\Scripts\python.exe"

REM --- 3. Instalar las librerias --------------------------------------------
echo [3/5] Instalando librerias (puede tardar unos minutos)...
"%VPY%" -m pip install --upgrade pip >> "%LOG%" 2>&1
"%VPY%" -m pip install -r requirements.txt pytest >> "%LOG%" 2>&1
if errorlevel 1 (
    echo  ERROR: fallo la instalacion de librerias. Revisa instalacion_log.txt
    goto :fin_error
)
echo       Librerias instaladas.

REM --- 4. Ejecutar las pruebas ----------------------------------------------
echo [4/5] Ejecutando las pruebas...
echo. >> "%LOG%"
echo ===== PRUEBAS ===== >> "%LOG%"
"%VPY%" -m pytest tests -v >> "%LOG%" 2>&1
if errorlevel 1 (
    echo       ATENCION: alguna prueba fallo. Revisa instalacion_log.txt
    echo RESULTADO PRUEBAS: con fallos >> "%LOG%"
) else (
    echo       Todas las pruebas pasaron.
    echo RESULTADO PRUEBAS: todas pasaron >> "%LOG%"
)

REM --- 5. Abrir VS Code y la aplicacion -------------------------------------
echo [5/5] Abriendo VS Code y la aplicacion...
where code >nul 2>&1 && start "" code "%~dp0"
echo INSTALACION COMPLETA >> "%LOG%"
echo.
echo  La aplicacion se abrira en el navegador en http://localhost:8501
echo  Para detenerla, cierra esta ventana o pulsa Ctrl + C.
echo.
start "" cmd /c "timeout /t 8 /nobreak >nul & start http://localhost:8501"
"%VPY%" -m streamlit run app.py --server.headless true
goto :eof

:fin_error
echo.
echo INSTALACION CON ERRORES >> "%LOG%"
pause
exit /b 1
