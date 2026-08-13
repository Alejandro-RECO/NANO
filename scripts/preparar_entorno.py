#!/usr/bin/env python3
"""Instala las dependencias del .venv solo cuando hace falta.

Lo llaman los tres lanzadores (iniciar.bat / .ps1 / .sh) con el Python del
entorno virtual. Guarda en `.venv/.deps-ok` la huella de requirements.txt:
mientras coincida no se reinstala nada, y si el archivo cambia (por ejemplo
al anadirse `rich`) se reinstala solo, sin tener que borrar el .venv.

Usa unicamente la biblioteca estandar: se ejecuta ANTES de instalar nada.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REQUISITOS = RAIZ / "requirements.txt"
SELLO = RAIZ / ".venv" / ".deps-ok"


def huella() -> str:
    """SHA-256 de requirements.txt, con el nombre del interprete."""
    datos = REQUISITOS.read_bytes() if REQUISITOS.exists() else b""
    version = f"{sys.version_info.major}.{sys.version_info.minor}".encode()
    return hashlib.sha256(datos + b"|" + version).hexdigest()


def al_dia(actual: str) -> bool:
    try:
        return SELLO.read_text(encoding="utf-8").strip() == actual
    except OSError:
        return False


def instalar() -> int:
    print("[..] Instalando dependencias en .venv ...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    resultado = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUISITOS)],
        check=False,
    )
    return resultado.returncode


def main() -> int:
    if not REQUISITOS.exists():
        print(f"[ERROR] No se encuentra {REQUISITOS}")
        return 1

    actual = huella()
    if al_dia(actual):
        print("[OK] Dependencias listas.")
        return 0

    codigo = instalar()
    if codigo != 0:
        print("[ERROR] Fallo la instalacion de dependencias.")
        return codigo

    try:
        SELLO.parent.mkdir(parents=True, exist_ok=True)
        SELLO.write_text(actual, encoding="utf-8")
    except OSError:
        pass  # sin sello solo se pierde el atajo, no la funcionalidad
    print("[OK] Dependencias listas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
