# ============================================================
#  NANO - Iniciador del visor de logs en tiempo real (PowerShell)
#  Crea un entorno virtual local (.venv), instala dependencias
#  y arranca el visor. Funciona en cualquier maquina con Python.
#  Uso:  .\iniciar.ps1 [carpeta] [opciones de log_viewer.py]
#  Ej.:  .\iniciar.ps1 logs -f ERROR -t
# ============================================================
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host ""
Write-Host "=== NANO - Iniciando visor de logs ===" -ForegroundColor Magenta
Write-Host ""

# 1) Localizar Python (python o py launcher)
$py = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $py = "py" }
if (-not $py) {
    Write-Host "[ERROR] Python no encontrado en PATH." -ForegroundColor Red
    Write-Host "Instalalo desde https://www.python.org/downloads/ y reintenta."
    exit 1
}
Write-Host "[OK] $(& $py --version)" -ForegroundColor Green

# 2) Crear entorno virtual local si no existe
$vpy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $vpy)) {
    Write-Host "[..] Creando entorno virtual .venv ..."
    & $py -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] No se pudo crear el entorno virtual." -ForegroundColor Red
        exit 1
    }
}

# 3) Instalar dependencias dentro del venv
& $vpy -c "import colorama" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[..] Instalando dependencias en .venv ..."
    & $vpy -m pip install --upgrade pip | Out-Null
    & $vpy -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallo la instalacion de dependencias." -ForegroundColor Red
        exit 1
    }
}
Write-Host "[OK] Dependencias listas." -ForegroundColor Green

# 4) Lanzar visor (pasa todos los argumentos)
Write-Host "[..] Arrancando visor... (Ctrl+C para salir)"
Write-Host ""
& $vpy log_viewer.py @args
