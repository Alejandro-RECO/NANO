# ============================================================
#  NANO - Iniciador del visor de logs en tiempo real (PowerShell)
#  Verifica Python, instala dependencias y arranca el visor.
#  Uso:  .\iniciar.ps1 [carpeta] [opciones de log_viewer.py]
#  Ej.:  .\iniciar.ps1 logs -f ERROR -t
# ============================================================
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host ""
Write-Host "=== NANO - Iniciando visor de logs ===" -ForegroundColor Magenta
Write-Host ""

# 1) Verificar Python
$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) {
    Write-Host "[ERROR] Python no encontrado en PATH." -ForegroundColor Red
    Write-Host "Instalalo desde https://www.python.org/downloads/ y reintenta."
    exit 1
}
Write-Host "[OK] $(python --version)" -ForegroundColor Green

# 2) Dependencias
Write-Host "[..] Verificando dependencias (colorama)..."
python -c "import colorama" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[..] Instalando dependencias..."
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallo la instalacion de dependencias." -ForegroundColor Red
        exit 1
    }
}
Write-Host "[OK] Dependencias listas." -ForegroundColor Green

# 3) Lanzar visor (pasa todos los argumentos)
Write-Host "[..] Arrancando visor... (Ctrl+C para salir)"
Write-Host ""
python log_viewer.py @args
