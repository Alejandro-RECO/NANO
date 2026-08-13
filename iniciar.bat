@echo off
REM ============================================================
REM  NANO - Iniciador del visor / panel de control de logs
REM  Crea un entorno virtual local (.venv), instala dependencias
REM  y arranca el visor. Funciona en cualquier maquina con Python.
REM  Uso:  iniciar.bat [carpeta] [opciones]
REM  Ej.:  iniciar.bat logs -f ERROR
REM        iniciar.bat logs --simple
REM ============================================================
setlocal
cd /d "%~dp0"

echo(
echo === NANO - Iniciando visor de logs ===
echo(

REM 1) Localizar Python (python o py launcher)
set "PY=python"
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python no encontrado en PATH.
        echo Instalalo desde https://www.python.org/downloads/ y reintenta.
        pause
        exit /b 1
    )
    set "PY=py"
)
for /f "delims=" %%v in ('%PY% --version 2^>^&1') do echo [OK] %%v

REM 2) Crear entorno virtual local si no existe
if not exist ".venv\Scripts\python.exe" (
    echo [..] Creando entorno virtual .venv ...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
)
set "VPY=.venv\Scripts\python.exe"

REM 3) Instalar dependencias solo si requirements.txt cambio
"%VPY%" scripts\preparar_entorno.py
if errorlevel 1 (
    pause
    exit /b 1
)

REM 4) Lanzar el visor (pasa todos los argumentos recibidos)
echo [..] Arrancando visor... ('q' o Ctrl+C para salir)
echo(
"%VPY%" -m nano %*

endlocal
