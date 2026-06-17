@echo off
REM ============================================================
REM  NANO - Iniciador del visor de logs en tiempo real
REM  Crea un entorno virtual local (.venv), instala dependencias
REM  y arranca el visor. Funciona en cualquier maquina con Python.
REM  Uso:  iniciar.bat [carpeta] [opciones de log_viewer.py]
REM  Ej.:  iniciar.bat logs -f ERROR -t
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

REM 3) Instalar dependencias dentro del venv
"%VPY%" -c "import colorama" >nul 2>&1
if errorlevel 1 (
    echo [..] Instalando dependencias en .venv ...
    "%VPY%" -m pip install --upgrade pip >nul 2>&1
    "%VPY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion de dependencias.
        pause
        exit /b 1
    )
)
echo [OK] Dependencias listas.

REM 4) Lanzar el visor (pasa todos los argumentos recibidos)
echo [..] Arrancando visor... (Ctrl+C para salir)
echo(
"%VPY%" log_viewer.py %*

endlocal
