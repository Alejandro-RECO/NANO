@echo off
REM ============================================================
REM  NANO - Iniciador del visor de logs en tiempo real
REM  Verifica Python, instala dependencias y arranca el visor.
REM  Uso:  iniciar.bat [carpeta] [opciones de log_viewer.py]
REM  Ej.:  iniciar.bat logs -f ERROR -t
REM ============================================================
setlocal
cd /d "%~dp0"

echo(
echo === NANO - Iniciando visor de logs ===
echo(

REM 1) Verificar que Python existe
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en PATH.
    echo Instalalo desde https://www.python.org/downloads/ y reintenta.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('python --version 2^>^&1') do echo [OK] %%v

REM 2) Instalar / verificar dependencias
echo [..] Verificando dependencias (colorama)...
python -c "import colorama" >nul 2>&1
if errorlevel 1 (
    echo [..] Instalando dependencias...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion de dependencias.
        pause
        exit /b 1
    )
)
echo [OK] Dependencias listas.

REM 3) Lanzar el visor (pasa todos los argumentos recibidos)
echo [..] Arrancando visor... (Ctrl+C para salir)
echo(
python log_viewer.py %*

endlocal
