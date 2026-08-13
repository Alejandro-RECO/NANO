#!/usr/bin/env bash
# ============================================================
#  NANO - Iniciador del visor / panel de control (Linux/Mac)
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

# 3) Instalar dependencias solo si requirements.txt cambio
"$VPY" scripts/preparar_entorno.py

# 4) Lanzar visor
echo "[..] Arrancando visor... ('q' o Ctrl+C para salir)"
echo ""
exec "$VPY" -m nano "$@"
