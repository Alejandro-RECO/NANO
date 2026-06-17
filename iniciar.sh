#!/usr/bin/env bash
# ============================================================
#  NANO - Iniciador del visor de logs en tiempo real (Linux/Mac)
#  Crea un entorno virtual local (.venv), instala dependencias
#  y arranca el visor. Uso: ./iniciar.sh [carpeta] [opciones]
# ============================================================
set -e
cd "$(dirname "$0")"

echo ""
echo "=== NANO - Iniciando visor de logs ==="
echo ""

# 1) Localizar Python
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
    echo "[ERROR] Python no encontrado. Instalalo y reintenta."
    exit 1
fi
echo "[OK] $($PY --version)"

# 2) Crear venv si no existe
if [ ! -x ".venv/bin/python" ]; then
    echo "[..] Creando entorno virtual .venv ..."
    "$PY" -m venv .venv
fi
VPY=".venv/bin/python"

# 3) Instalar dependencias
if ! "$VPY" -c "import colorama" >/dev/null 2>&1; then
    echo "[..] Instalando dependencias en .venv ..."
    "$VPY" -m pip install --upgrade pip >/dev/null 2>&1 || true
    "$VPY" -m pip install -r requirements.txt
fi
echo "[OK] Dependencias listas."

# 4) Lanzar visor
echo "[..] Arrancando visor... (Ctrl+C para salir)"
echo ""
exec "$VPY" log_viewer.py "$@"
