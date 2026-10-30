@echo off
REM Ejecuta las pruebas automaticas (requiere haber ejecutado instalar.bat una vez).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta instalar.bat
    pause
    exit /b 1
)
echo Ejecutando las pruebas... (el resultado queda en pruebas_log.txt)
echo Pruebas: %DATE% %TIME% > pruebas_log.txt
".venv\Scripts\python.exe" -m pytest tests -v >> pruebas_log.txt 2>&1
if errorlevel 1 (
    echo RESULTADO: con fallos >> pruebas_log.txt
    echo ATENCION: alguna prueba fallo. Revisa pruebas_log.txt
) else (
    echo RESULTADO: todas pasaron >> pruebas_log.txt
    echo Todas las pruebas pasaron.
)
type pruebas_log.txt | findstr /c:"passed" /c:"failed" /c:"RESULTADO"
pause
