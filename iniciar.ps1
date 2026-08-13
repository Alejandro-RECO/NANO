# ============================================================
#  NANO - Iniciador del visor / panel de control (PowerShell)
#  Crea un entorno virtual local (.venv), instala dependencias
#  y arranca el visor. Funciona en cualquier maquina con Python.
#  Uso:  .\iniciar.ps1 [carpeta] [opciones]
#  Ej.:  .\iniciar.ps1 logs -f ERROR
#        .\iniciar.ps1 logs --simple
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

# 3) Instalar dependencias solo si requirements.txt cambio
& $vpy (Join-Path $PSScriptRoot "scripts\preparar_entorno.py")
if ($LASTEXITCODE -ne 0) { exit 1 }

# 4) Lanzar visor (pasa todos los argumentos)
Write-Host "[..] Arrancando visor... ('q' o Ctrl+C para salir)"
Write-Host ""
& $vpy -m nano @args
